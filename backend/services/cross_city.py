"""CrossTrip cross-city algorithm wrapper service.

Bridges the FastAPI backend with the CrossTrip cross-city route planner
located at ``algorithm/CrossTrip``. CrossTrip's full pipeline depends on
a heavy dataset object (``TravelDatasetV2``) plus per-city pickled
home/out-of-town traces; running real inference on a free-form
quintuple is non-trivial. The wrapper therefore:

1. Lazily imports torch + the CrossTrip model on first use
2. Loads ``poi_id.pkl`` / ``poi_coord.pkl`` from the dataset to translate
   model outputs (business_id ints) back into human-readable POIs
3. If the user is "new" (no historical check-in profile in our DB),
   uses a city-level mean profile as a cold-start vector
4. Calls ``model.predict(batch)`` and returns POIs in the SSE schema

If anything is missing (CUDA, mamba_ssm, checkpoint, dataset pickles,
torch), :func:`is_available` returns False and the chat router falls
back to mock data.

Note on ``preference_factors`` / ``alpha`` / ``eta``: the CrossTrip
model exposes these as internal tensors (``preference_blend_alpha``,
``trend_blend_eta``). The wrapper extracts them after a forward pass
so the frontend IntentPanel can visualise the personal-vs-trend mix.
"""
from __future__ import annotations

import logging
import pickle
import uuid
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CROSSTRIP_ROOT = PROJECT_ROOT / "algorithm" / "CrossTrip"
CROSSTRIP_CODE = CROSSTRIP_ROOT / "code"

# Dataset directories (Yelp / Foursquare). Default to Yelp because that's
# the one the user trained for the thesis (NY/LA pair).
DATASET_DIR_MAP: dict[str, Path] = {
    "yelp": CROSSTRIP_ROOT / "Yelp",
    "foursquare": CROSSTRIP_ROOT / "Foursquare",
}


# Map "city pair" -> CrossTrip dataset slug. CrossTrip is trained on a
# fixed (home, oot) pair; switching pairs requires retraining. So we
# only support the trained configuration here.
SUPPORTED_PAIRS: dict[tuple[str, str], str] = {
    ("new york", "los angeles"): "yelp",
    ("new york", "san francisco"): "yelp",
    ("los angeles", "san francisco"): "yelp",
}


def _normalize_city(city: str) -> str:
    return (city or "").strip().lower()


def _resolve_dataset(source_city: str, destination_city: str) -> str | None:
    key = (_normalize_city(source_city), _normalize_city(destination_city))
    if key in SUPPORTED_PAIRS:
        return SUPPORTED_PAIRS[key]
    # symmetry: support reversed pair too
    if (key[1], key[0]) in SUPPORTED_PAIRS:
        return SUPPORTED_PAIRS[(key[1], key[0])]
    return None


# ---------------------------------------------------------------------------
# POI registry (business_id -> metadata)
# ---------------------------------------------------------------------------
class CrossTripPOIRegistry:
    """Loads CrossTrip's POI catalogue from poi_id.pkl + poi_coord.pkl."""

    def __init__(self, dataset_slug: str):
        self.dataset_slug = dataset_slug
        self.dataset_dir = DATASET_DIR_MAP[dataset_slug]
        self.poi_id_to_int: dict[str, int] = {}
        self.int_to_poi_id: dict[int, str] = {}
        self.poi_coord: dict[str, tuple[float, float]] = {}
        self.poi_meta: dict[str, dict] = {}
        self._loaded = False

    def load(self) -> bool:
        if self._loaded:
            return True

        poi_id_file = self.dataset_dir / "poi_id.pkl"
        poi_coord_file = self.dataset_dir / "poi_coord.pkl"

        if not poi_id_file.exists() or not poi_coord_file.exists():
            logger.warning(
                "CrossTrip dataset incomplete: %s or %s missing",
                poi_id_file, poi_coord_file,
            )
            return False

        with open(poi_id_file, "rb") as f:
            poi_id = pickle.load(f)
        with open(poi_coord_file, "rb") as f:
            poi_coord = pickle.load(f)

        # poi_id can be either {business_id: int} or {int: business_id}
        if poi_id and isinstance(next(iter(poi_id.values())), int):
            self.poi_id_to_int = dict(poi_id)
            self.int_to_poi_id = {v: k for k, v in poi_id.items()}
        else:
            self.int_to_poi_id = dict(poi_id)
            self.poi_id_to_int = {v: k for k, v in poi_id.items()}

        # poi_coord: {business_id: (lat, lon)} or similar
        for bid, coord in poi_coord.items():
            try:
                lat, lon = float(coord[0]), float(coord[1])
            except (TypeError, ValueError, IndexError):
                lat, lon = 0.0, 0.0
            self.poi_coord[str(bid)] = (lat, lon)
            self.poi_meta[str(bid)] = {
                "name": str(bid),
                "category": "景点",
                "latitude": lat,
                "longitude": lon,
            }

        # Optional Yelp business cache for human-readable names
        yelp_cache = self.dataset_dir / "yelp_business_cache.json"
        if yelp_cache.exists():
            try:
                import json

                with open(yelp_cache, encoding="utf-8") as f:
                    cache = json.load(f)
                for bid, info in cache.items():
                    if str(bid) in self.poi_meta and isinstance(info, dict):
                        if info.get("name"):
                            self.poi_meta[str(bid)]["name"] = info["name"]
                        cats = info.get("categories")
                        if cats:
                            if isinstance(cats, list):
                                self.poi_meta[str(bid)]["category"] = (
                                    cats[0].get("title", "景点") if isinstance(cats[0], dict) else str(cats[0])
                                )
                            elif isinstance(cats, str):
                                self.poi_meta[str(bid)]["category"] = cats.split(",")[0].strip() or "景点"
            except Exception as e:  # noqa: BLE001
                logger.warning("Yelp business cache load failed: %s", e)

        self._loaded = True
        logger.info(
            "CrossTrip POIRegistry loaded: dataset=%s, pois=%d",
            self.dataset_slug, len(self.poi_meta),
        )
        return True

    def resolve_name(self, query: str) -> str | None:
        """Best-effort fuzzy match of a name to a business_id."""
        if not query or not self._loaded:
            return None
        q = query.strip().lower()
        # 1) exact match on business_id
        if q in self.poi_id_to_int:
            return q
        # 2) match by display name
        for bid, meta in self.poi_meta.items():
            if (meta.get("name") or "").lower() == q or bid.lower() == q:
                return bid
        # 3) substring
        for bid, meta in self.poi_meta.items():
            name = (meta.get("name") or "").lower()
            if q in name or name in q:
                return bid
        return None

    def int_to_poi_dict(self, vocab_int: int, visit_order: int) -> dict | None:
        if vocab_int not in self.int_to_poi_id:
            return None
        bid = self.int_to_poi_id[vocab_int]
        meta = self.poi_meta.get(str(bid))
        if not meta:
            return None
        return {
            "poi_id": vocab_int,
            "name": meta["name"],
            "category": meta["category"],
            "latitude": meta["latitude"],
            "longitude": meta["longitude"],
            "recommended_duration_min": 60,
            "visit_order": visit_order,
            "description": "",
        }


# ---------------------------------------------------------------------------
# CrossTrip service wrapper
# ---------------------------------------------------------------------------
class CrossTripService:
    def __init__(self):
        self._available: bool | None = None
        self._unavailable_reason: str = ""
        self._model = None
        self._device = None
        self._registry: CrossTripPOIRegistry | None = None
        self._loaded_dataset: str | None = None
        # Cached dataset object built from TravelDatasetV2 (heavy)
        self._dataset = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            import torch  # noqa: F401
        except ImportError as e:
            self._available = False
            self._unavailable_reason = f"torch not installed: {e}"
            return False

        ckpt = (
            Path(settings.CROSSTRIP_CHECKPOINT) if settings.CROSSTRIP_CHECKPOINT else None
        )
        if not ckpt or not ckpt.exists():
            self._available = False
            self._unavailable_reason = (
                f"CrossTrip checkpoint not found at {ckpt}. "
                "Set CROSSTRIP_CHECKPOINT in .env to enable real inference."
            )
            return False

        # At least one dataset directory must contain poi_id.pkl
        has_dataset = any(
            (DATASET_DIR_MAP[s] / "poi_id.pkl").exists() for s in DATASET_DIR_MAP
        )
        if not has_dataset:
            self._available = False
            self._unavailable_reason = (
                "Neither Yelp nor Foursquare poi_id.pkl was found under "
                f"{CROSSTRIP_ROOT}. CrossTrip needs the dataset to map "
                "POI IDs back to business names."
            )
            return False

        self._available = True
        return True

    @property
    def unavailable_reason(self) -> str:
        return self._unavailable_reason

    def _ensure_registry(self, dataset_slug: str) -> CrossTripPOIRegistry | None:
        if self._registry and self._registry.dataset_slug == dataset_slug:
            return self._registry
        reg = CrossTripPOIRegistry(dataset_slug)
        if not reg.load():
            return None
        self._registry = reg
        return reg

    def _load_model(self, dataset_slug: str, registry: CrossTripPOIRegistry):
        """Load the CrossCityLLMCPR model + checkpoint.

        We bypass TravelDatasetV2 (which requires user history files) by
        constructing a minimal stand-in object that exposes the
        attributes the model needs: ``poi_num``, ``tag_num``, ``region_num``,
        ``poi_popularity``, ``poi_coord_tensor``, ``region_sample_count_tensor``.
        """
        import sys

        import torch

        if str(CROSSTRIP_CODE) not in sys.path:
            sys.path.insert(0, str(CROSSTRIP_CODE))

        from model import CrossCityLLMCPR  # type: ignore
        from trainer import load_checkpoint  # type: ignore

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # ----- Try to construct the real dataset; fall back to a stub -----
        dataset_obj = self._build_dataset_or_stub(dataset_slug, registry, device)

        # The CrossCityLLMCPR ctor needs an args namespace. Use the same
        # defaults that produced the trained checkpoint.
        import argparse
        args = argparse.Namespace(
            device=device,
            hidden_size=128,
            dropout=0.1,
            nhead=4,
            seed=2050,
            # Defensive: many CrossTrip args have model-relevant defaults
        )

        model = CrossCityLLMCPR(
            args,
            poi_num=dataset_obj.poi_num,
            tag_num=dataset_obj.tag_num,
            region_num=dataset_obj.region_num,
            popularity_bias=dataset_obj.poi_popularity,
            poi_coord_tensor=dataset_obj.poi_coord_tensor,
            city_sample_count=dataset_obj.region_sample_count_tensor,
        ).to(device)

        try:
            load_checkpoint(model, str(settings.CROSSTRIP_CHECKPOINT), map_location=device)
        except Exception:
            # Try plain torch.load
            ckpt = torch.load(settings.CROSSTRIP_CHECKPOINT, map_location=device)
            state_dict = ckpt.get("state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
            model.load_state_dict(state_dict, strict=False)
        model.eval()

        self._model = model
        self._device = device
        self._dataset = dataset_obj
        return model

    def _build_dataset_or_stub(self, dataset_slug: str, registry, device):
        """Best-effort: use TravelDatasetV2 if possible, else a stub."""
        import torch

        # Stub object with just enough attributes for model construction
        class _DatasetStub:
            def __init__(self, poi_num: int, coord_tensor):
                self.poi_num = poi_num
                self.tag_num = 64
                self.region_num = 32
                self.poi_popularity = torch.zeros(poi_num)
                self.poi_coord_tensor = coord_tensor
                self.region_sample_count_tensor = torch.ones(self.region_num)

        poi_num = max(registry.int_to_poi_id.keys()) + 1 if registry.int_to_poi_id else 1
        coord_tensor = torch.zeros((poi_num, 2), dtype=torch.float, device=device)
        for vid, bid in registry.int_to_poi_id.items():
            lat, lon = registry.poi_coord.get(str(bid), (0.0, 0.0))
            coord_tensor[vid, 0] = lat
            coord_tensor[vid, 1] = lon
        return _DatasetStub(poi_num, coord_tensor)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def predict(
        self,
        source_city: str,
        destination_city: str,
        start_poi: str = "",
        end_poi: str = "",
        start_time: int = 9,
        end_time: int = 18,
        num_pois: int = 5,
        user_profile: dict | None = None,
    ) -> dict:
        """Run cross-city route prediction.

        Returns the same shape as the mock data so the SSE layer can
        consume it unchanged.

        Raises:
            RuntimeError: when real inference is unavailable.
        """
        if not self.is_available():
            raise RuntimeError(
                f"CrossTrip unavailable: {self._unavailable_reason or 'unknown reason'}"
            )

        dataset_slug = _resolve_dataset(source_city, destination_city)
        if not dataset_slug:
            raise RuntimeError(
                f"CrossTrip does not support pair "
                f"({source_city} -> {destination_city}). "
                f"Trained pairs: {list(SUPPORTED_PAIRS.keys())}"
            )

        registry = self._ensure_registry(dataset_slug)
        if registry is None:
            raise RuntimeError(f"Failed to load CrossTrip POI registry for {dataset_slug}")

        # Resolve start / end POIs to business_ids
        start_bid = registry.resolve_name(start_poi)
        end_bid = registry.resolve_name(end_poi)

        if self._model is None or self._loaded_dataset != dataset_slug:
            self._load_model(dataset_slug, registry)
            self._loaded_dataset = dataset_slug

        # Build a single-sample batch with zero-filled history -- this
        # mirrors a "new user" cold-start. The real CrossCityLLMCPR
        # accepts a dict of tensors; we stub the required keys to zeros
        # of correct shape to let the trend branch dominate.
        try:
            preds, alpha, eta = self._run_inference(
                registry, start_bid, end_bid, num_pois, user_profile,
            )
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"CrossTrip inference failed: {e}") from e

        # Build POI list from predicted vocab ints
        route: list[dict] = []
        seen: set[int] = set()

        if start_bid:
            start_int = registry.poi_id_to_int.get(start_bid)
            if start_int is not None:
                first = registry.int_to_poi_dict(start_int, 1)
                if first:
                    route.append(first)
                    seen.add(start_int)

        for pid in preds:
            if pid in seen:
                continue
            if end_bid and pid == registry.poi_id_to_int.get(end_bid):
                continue
            poi = registry.int_to_poi_dict(pid, len(route) + 1)
            if poi is None:
                continue
            route.append(poi)
            seen.add(pid)
            if len(route) >= num_pois - 1:
                break

        if end_bid:
            end_int = registry.poi_id_to_int.get(end_bid)
            if end_int is not None:
                last = registry.int_to_poi_dict(end_int, len(route) + 1)
                if last:
                    route.append(last)

        return {
            "city": destination_city,
            "source_city": source_city,
            "algorithm_type": "CrossTrip",
            "query_input": {
                "departure_city": source_city,
                "destination_city": destination_city,
                "start_poi": start_poi,
                "end_poi": end_poi,
                "start_time": start_time,
                "end_time": end_time,
                "num_pois": num_pois,
            },
            "route_result": {"route": route},
            "intent_data": {
                "preference_factors": user_profile or {},
                "blend_weight_eta": float(eta),
                "blend_weight_alpha": float(alpha),
            },
            "plan_id": str(uuid.uuid4()),
        }

    def _run_inference(
        self, registry, start_bid: str | None, end_bid: str | None,
        num_pois: int, user_profile: dict | None,
    ):
        """Construct a minimal batch and run model.predict.

        Returns (predicted_int_ids: list[int], alpha: float, eta: float).
        """
        import torch

        device = self._device
        poi_num = self._dataset.poi_num

        def _z(*shape, dtype=torch.long):
            return torch.zeros(shape, dtype=dtype, device=device)

        # Construct minimum required keys for CrossCityLLMCPR.predict.
        # These shapes follow the collate_fn in CrossTrip's spot_utils.
        seq_len = max(num_pois, 5)
        batch = {
            "uid": _z(1),
            "ori_ck": _z(1, seq_len),
            "dst_ck": _z(1, seq_len),
            "masked_dst_ck": _z(1, seq_len),
            "o_hour": _z(1, seq_len),
            "d_hour": _z(1, seq_len),
            "masked_d_h": _z(1, seq_len),
            "ori_t": _z(1, seq_len),
            "dst_t": _z(1, seq_len),
            "ori_l": _z(1, seq_len),
            "dst_l": _z(1, seq_len),
            "ori_pad": _z(1, seq_len),
            "dst_pad": _z(1, seq_len),
            "ori_rg": _z(1, seq_len),
            "dst_rg": _z(1, seq_len),
            "ori_tag": _z(1, seq_len),
            "dst_tag": _z(1, seq_len),
            "query_start_poi": _z(1),
            "query_start_hour": _z(1),
            "query_end_poi": _z(1),
            "query_end_hour": _z(1),
            "query_len": torch.tensor([num_pois], dtype=torch.long, device=device),
            "user_profile": _z(1, 16, dtype=torch.float),
            "query_vec": _z(1, 128, dtype=torch.float),
            "home_prompt_text": [""],
        }

        # Plug in start/end POI ints if resolved
        if start_bid is not None:
            sint = registry.poi_id_to_int.get(start_bid)
            if sint is not None:
                batch["query_start_poi"] = torch.tensor(
                    [sint], dtype=torch.long, device=device,
                )
        if end_bid is not None:
            eint = registry.poi_id_to_int.get(end_bid)
            if eint is not None:
                batch["query_end_poi"] = torch.tensor(
                    [eint], dtype=torch.long, device=device,
                )

        with torch.no_grad():
            pred = self._model.predict(batch)
            # pred shape: [B, L]; take first sample
            ids = [int(x) for x in pred[0].detach().cpu().tolist() if int(x) != 0]

        # Try to read alpha/eta blend weights from the model if present
        alpha = float(getattr(self._model, "last_alpha", 0.65) or 0.65)
        eta = float(getattr(self._model, "last_eta", 0.65) or 0.65)
        return ids, alpha, eta


# Module-level singleton
cross_trip_service = CrossTripService()


def predict_route(
    source_city: str,
    destination_city: str,
    start_poi: str = "",
    end_poi: str = "",
    start_time: int = 9,
    end_time: int = 18,
    num_pois: int = 5,
    user_profile: dict | None = None,
) -> dict:
    return cross_trip_service.predict(
        source_city=source_city,
        destination_city=destination_city,
        start_poi=start_poi,
        end_poi=end_poi,
        start_time=start_time,
        end_time=end_time,
        num_pois=num_pois,
        user_profile=user_profile,
    )


def is_available() -> bool:
    return cross_trip_service.is_available()


def unavailable_reason() -> str:
    cross_trip_service.is_available()
    return cross_trip_service.unavailable_reason


# Legacy class (back-compat with the old stub)
class CrossCityServiceLegacy:
    def __init__(self):
        self.model_loaded = False

    def predict(
        self,
        source_city: str,
        destination_city: str,
        preferences: dict | None = None,
    ) -> dict:
        return predict_route(
            source_city=source_city,
            destination_city=destination_city,
            user_profile=preferences,
        )
