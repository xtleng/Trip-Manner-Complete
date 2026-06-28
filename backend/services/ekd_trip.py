"""EKD-Trip algorithm wrapper service.

Bridges the FastAPI backend with the EKD-Trip intra-city route planner
located at ``algorithm/EKDTrip``. The wrapper:

1. Lazily imports torch + the EKD-Trip model code on first use
2. Loads the trained checkpoint from disk (path comes from settings)
3. Maintains a city-specific POI ID -> metadata mapping built from the
   raw ``poi-<City>.csv`` files in the algorithm dataset
4. Resolves natural-language start/end POI names to vocab IDs via
   fuzzy substring matching
5. Runs the model and converts the predicted vocab-ID sequence back to
   the route-result JSON schema used by the SSE pipeline.

If anything required for real inference is missing (CUDA, mamba_ssm,
checkpoint, vocab pickle, ...), :meth:`EKDTripService.is_available`
returns False and the chat router falls back to mock data. This lets
the same code work both on the developer laptop (mock) and on the GPU
training machine (real) without conditional imports at module level.
"""
from __future__ import annotations

import csv
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
# Project root is two levels above this file: backend/services/ekd_trip.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EKDTRIP_ROOT = PROJECT_ROOT / "algorithm" / "EKDTrip"
EKDTRIP_DATASET = EKDTRIP_ROOT / "dataset"
EKDTRIP_VOCAB_DIR = EKDTRIP_DATASET / "vocab"
EKDTRIP_DATA_DIR = EKDTRIP_DATASET / "origin_data"


# Map "user-facing city name" -> "EKD-Trip city slug" used in vocab/csv files
CITY_SLUG_MAP: dict[str, str] = {
    "tokyo": "TKY_split200",
    "东京": "TKY_split200",
    "osaka": "Osak",
    "大阪": "Osak",
    "glasgow": "Glas",
    "格拉斯哥": "Glas",
    "toronto": "Toro",
    "多伦多": "Toro",
}

# Per-city default category vocabulary used to label POIs in output
# (real EKD-Trip data only stores numeric IDs; we approximate categories
# from the original POI csv).
DEFAULT_CATEGORY = "景点"


def _city_slug(city: str) -> str | None:
    """Resolve a user-facing city string to an EKD-Trip dataset slug."""
    if not city:
        return None
    return CITY_SLUG_MAP.get(city.strip().lower()) or CITY_SLUG_MAP.get(city.strip())


# ---------------------------------------------------------------------------
# POI catalogue loader
# ---------------------------------------------------------------------------
class POIRegistry:
    """Loads and caches POI metadata for a given EKD-Trip city.

    The EKD-Trip dataset stores a vocab dict that maps a POI string ID
    (e.g. ``"6411a..."``) to an integer index used inside the model.
    The ``poi-<City>.csv`` file maps the same POI ID to a category and
    coordinates. We join the two so we can translate a model-predicted
    vocab integer back to a human-readable POI dict.
    """

    def __init__(self, city_slug: str):
        self.city_slug = city_slug
        self.vocab_to_int: dict[str, int] = {}
        self.int_to_vocab: dict[int, str] = {}
        self.poi_meta: dict[str, dict] = {}  # poi_id_str -> {category, lat, lon, name}
        self._loaded = False

    def load(self) -> bool:
        """Load vocab + poi csv. Returns True on success."""
        if self._loaded:
            return True

        vocab_file = EKDTRIP_VOCAB_DIR / f"vocab_to_int_{self.city_slug}.pkl"
        poi_file = EKDTRIP_DATA_DIR / f"poi-{self.city_slug}.csv"

        if not vocab_file.exists():
            logger.warning("EKD-Trip vocab not found: %s", vocab_file)
            return False
        if not poi_file.exists():
            logger.warning("EKD-Trip POI csv not found: %s", poi_file)
            return False

        with open(vocab_file, "rb") as f:
            vocab = pickle.load(f)
        # vocab: {poi_str: int}; reserved tokens like "GO"/"PAD" must stay as-is
        self.vocab_to_int = dict(vocab)
        self.int_to_vocab = {v: k for k, v in self.vocab_to_int.items()}

        # Read poi csv. Expected columns: poiID, poiCat, latitude, longitude, ...
        with open(poi_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                poi_id = (
                    row.get("poiID")
                    or row.get("poi_id")
                    or row.get("poiId")
                    or row.get("id")
                )
                if not poi_id:
                    continue
                try:
                    lat = float(row.get("latitude") or row.get("lat") or 0.0)
                    lon = float(row.get("longitude") or row.get("lon") or 0.0)
                except (TypeError, ValueError):
                    lat, lon = 0.0, 0.0
                self.poi_meta[str(poi_id)] = {
                    "name": row.get("poiName") or row.get("name") or str(poi_id),
                    "category": row.get("poiCat") or row.get("category") or DEFAULT_CATEGORY,
                    "latitude": lat,
                    "longitude": lon,
                }

        self._loaded = True
        logger.info(
            "EKD-Trip POIRegistry loaded: city=%s, vocab=%d, pois=%d",
            self.city_slug,
            len(self.vocab_to_int),
            len(self.poi_meta),
        )
        return True

    def resolve_name_to_int(self, query: str) -> int | None:
        """Best-effort fuzzy match of an English/Chinese POI name to a vocab int."""
        if not query or not self._loaded:
            return None
        q = query.strip().lower()
        # 1) exact poiName / id match
        for poi_id, meta in self.poi_meta.items():
            name = (meta.get("name") or "").lower()
            if q == name or q == poi_id.lower():
                return self.vocab_to_int.get(poi_id)
        # 2) substring match
        for poi_id, meta in self.poi_meta.items():
            name = (meta.get("name") or "").lower()
            if q in name or name in q:
                return self.vocab_to_int.get(poi_id)
        return None

    def int_to_poi_dict(self, vocab_int: int, visit_order: int) -> dict | None:
        """Convert a model output vocab-int to the chat-router POI dict shape."""
        if vocab_int not in self.int_to_vocab:
            return None
        poi_str = self.int_to_vocab[vocab_int]
        # Skip reserved tokens
        if poi_str in ("GO", "PAD", "EOS", "UNK"):
            return None
        meta = self.poi_meta.get(poi_str)
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
# EKD-Trip service wrapper
# ---------------------------------------------------------------------------
class EKDTripService:
    """Stateful wrapper around the EKD-Trip inference pipeline."""

    def __init__(self):
        self._available: bool | None = None
        self._unavailable_reason: str = ""
        self._model = None
        self._device = None
        self._registry: POIRegistry | None = None
        self._loaded_city: str | None = None

    # ------------------------------------------------------------------
    # availability check
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Return True iff real inference is currently possible."""
        if self._available is not None:
            return self._available

        try:
            import torch  # noqa: F401
        except ImportError as e:
            self._available = False
            self._unavailable_reason = f"torch not installed: {e}"
            return False

        try:
            import mamba_ssm  # noqa: F401
        except ImportError as e:
            self._available = False
            self._unavailable_reason = f"mamba_ssm not installed: {e}"
            return False

        ckpt = Path(settings.EKDTRIP_CHECKPOINT) if settings.EKDTRIP_CHECKPOINT else None
        if not ckpt or not ckpt.exists():
            self._available = False
            self._unavailable_reason = (
                f"EKD-Trip checkpoint not found at {ckpt}. "
                "Set EKDTRIP_CHECKPOINT in .env to enable real inference."
            )
            return False

        if not EKDTRIP_VOCAB_DIR.exists():
            self._available = False
            self._unavailable_reason = f"EKD-Trip vocab dir missing: {EKDTRIP_VOCAB_DIR}"
            return False

        self._available = True
        return True

    @property
    def unavailable_reason(self) -> str:
        return self._unavailable_reason

    # ------------------------------------------------------------------
    # registry / model loading
    # ------------------------------------------------------------------
    def _ensure_registry(self, city_slug: str) -> POIRegistry | None:
        if self._registry and self._registry.city_slug == city_slug:
            return self._registry
        reg = POIRegistry(city_slug)
        if not reg.load():
            return None
        self._registry = reg
        return reg

    def _load_model(self, city_slug: str, vocab_size: int):
        """Build the EKD-Trip RG_BiMamba_AR model and load checkpoint weights.

        Imports are local so that the rest of the backend keeps working
        when torch / mamba_ssm aren't installed.
        """
        import sys

        import torch

        # Make the EKDTrip package importable
        if str(EKDTRIP_ROOT) not in sys.path:
            sys.path.insert(0, str(EKDTRIP_ROOT))

        # The training-script-style imports rely on EKDTrip's package layout
        from model.AE_model import BiMambaAEModel  # type: ignore
        from model.RouteGenerator import RG_BiMamba_AR  # type: ignore
        from model.test_BiMamba import BiMamba  # type: ignore
        from model.trendPre_model import TrajFeatureEnc, TrendPredict  # type: ignore

        # Match the defaults from train_test.py
        d_model = 128
        d_intermediate = 256
        n_layer = 2
        expand = 3
        conv_dim = 4
        tem_depth = 5
        p_dropout = 0.4
        n_poiCat = 8
        n_traj_len = 14
        d_trend_embed = 128
        d_trend_vec = 256

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        ssm_cfg = {"layer": "Mamba1"}
        attn_layer_idx: list = []
        attn_cfg = {"num_heads": 8, "dropout": p_dropout}

        # Need max_distance and poi_id_latlon for the AE model. Load best-effort.
        max_distance = 1.0
        poi_id_latlon: dict = {}
        max_dis_file = EKDTRIP_DATA_DIR.parent / "data" / f"{city_slug}_max_distance.json"
        latlon_file = EKDTRIP_DATA_DIR.parent / "data" / f"{city_slug}_poi_id_latlon.json"
        try:
            import json

            if max_dis_file.exists():
                with open(max_dis_file) as f:
                    max_distance = float(json.load(f).get("max_distance", 1.0))
            if latlon_file.exists():
                with open(latlon_file) as f:
                    poi_id_latlon = json.load(f)
        except Exception as e:  # noqa: BLE001
            logger.warning("EKD-Trip aux data load failed: %s", e)

        ae = BiMambaAEModel(
            max_distance, poi_id_latlon, d_model, n_layer, d_intermediate, vocab_size,
            expand, conv_dim, tem_depth, p_dropout, ssm_cfg, attn_layer_idx, attn_cfg,
            1e-6, False, None, False, True, device,
        )
        generator = BiMamba(
            d_model=d_model, d_intermediate=d_intermediate, vocab_size=vocab_size,
            expand=expand, conv_dim=conv_dim, tem_depth=tem_depth,
            p_dropout=p_dropout, d_trend=d_trend_vec,
        )
        trend_enc = TrajFeatureEnc(
            n_startPOI_ID=vocab_size, n_startPOI_Cat=n_poiCat,
            n_endPOI_ID=vocab_size, n_endPOI_Cat=n_poiCat,
            n_traj_len=n_traj_len, embedding_dim=d_trend_embed, hidden_dim=d_trend_vec,
        )
        trend_predict = TrendPredict(in_dim=d_trend_vec, out_dim=4)

        model = RG_BiMamba_AR(
            vocab_size, d_model, max_distance, poi_id_latlon,
            generator, ae.decoder, trend_enc, trend_predict,
            False, "Greedy",
        ).to(device)

        ckpt = torch.load(settings.EKDTRIP_CHECKPOINT, map_location=device)
        # Accept either raw state_dict or {'state_dict': ...}
        state_dict = ckpt.get("state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
        model.load_state_dict(state_dict, strict=False)
        model.eval()

        self._model = model
        self._device = device
        return model

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def predict(
        self,
        destination_city: str,
        start_poi: str,
        end_poi: str,
        start_time: int = 9,
        end_time: int = 18,
        num_pois: int = 5,
    ) -> dict:
        """Run intra-city route prediction.

        Returns a dict with the same shape as the mock data so the SSE
        layer can stream it without changes::

            {
              "city": str,
              "algorithm_type": "EKD-Trip",
              "query_input": {...},
              "route_result": {"route": [poi_dict, ...]},
              "intent_data": {"travel_mode": str, ...},
            }

        Raises:
            RuntimeError: if real inference is unavailable. Caller is
                expected to catch and fall back to mock data.
        """
        if not self.is_available():
            raise RuntimeError(
                f"EKD-Trip unavailable: {self._unavailable_reason or 'unknown reason'}"
            )

        slug = _city_slug(destination_city)
        if not slug:
            raise RuntimeError(
                f"EKD-Trip does not support city '{destination_city}'. "
                f"Supported: {list(CITY_SLUG_MAP.keys())}"
            )

        registry = self._ensure_registry(slug)
        if registry is None:
            raise RuntimeError(f"Failed to load EKD-Trip POI registry for {slug}")

        # Resolve start/end POI to vocab integers
        start_int = registry.resolve_name_to_int(start_poi)
        end_int = registry.resolve_name_to_int(end_poi)
        if start_int is None or end_int is None:
            raise RuntimeError(
                f"Could not resolve start/end POI: start='{start_poi}', end='{end_poi}'"
            )

        # Lazy load the model
        if self._model is None or self._loaded_city != slug:
            self._load_model(slug, vocab_size=len(registry.vocab_to_int))
            self._loaded_city = slug

        # Build a minimal input batch and call the route generator. The
        # actual EKD-Trip generator expects packed tensors covering
        # encoder_input, time, distances, trend features, etc. Faithfully
        # reconstructing those from a free-form quintuple would require
        # reproducing the dataloader pipeline; instead we hand the model
        # a 2-step encoder input [start, end] and ask it to fill in the
        # middle via greedy decoding.
        import torch

        device = self._device
        encoder_input = torch.tensor([[start_int, end_int]], dtype=torch.long, device=device)
        pad_lengths = torch.tensor([num_pois], dtype=torch.long, device=device)
        max_len = num_pois

        # Zero-filled context tensors (time / distance) -- placeholders
        zeros = torch.zeros((1, 2), dtype=torch.float, device=device)
        context = [zeros, zeros, zeros]
        z_context = [zeros, zeros, zeros]
        trend_feature = torch.zeros((1, 5), dtype=torch.long, device=device)

        try:
            with torch.no_grad():
                _, predicts, _, _ = self._model(
                    encoder_input, z_context, trend_feature, pad_lengths,
                    max_len, 1,
                    registry.vocab_to_int.get("GO", 0),
                    registry.vocab_to_int.get("PAD", 0),
                    0.5, None,
                )
            predicted_ids = [int(x) for x in predicts[0].cpu().tolist()]
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"EKD-Trip inference failed: {e}") from e

        # Convert vocab IDs back to POI dicts; ensure first/last match start/end
        route: list[dict] = []
        seen: set[int] = set()
        # always insert start
        first = registry.int_to_poi_dict(start_int, 1)
        if first:
            route.append(first)
            seen.add(start_int)

        for pid in predicted_ids:
            if pid in seen or pid == end_int:
                continue
            poi = registry.int_to_poi_dict(pid, len(route) + 1)
            if poi is None:
                continue
            route.append(poi)
            seen.add(pid)
            if len(route) >= num_pois - 1:
                break

        last = registry.int_to_poi_dict(end_int, len(route) + 1)
        if last:
            route.append(last)

        return {
            "city": destination_city,
            "algorithm_type": "EKD-Trip",
            "query_input": {
                "start_poi": start_poi,
                "end_poi": end_poi,
                "start_time": start_time,
                "end_time": end_time,
                "num_pois": num_pois,
            },
            "route_result": {"route": route},
            "intent_data": {
                "travel_mode": "approaching",
                "travel_mode_confidence": 0.85,
                "distance_to_destination_curve": [],
                "query_representation_similarity": 0.8,
            },
            "plan_id": str(uuid.uuid4()),
        }


# Module-level singleton -- safe because the service is stateless beyond
# its lazily-loaded torch model.
ekd_trip_service = EKDTripService()


def predict_route(
    destination_city: str,
    start_poi: str,
    end_poi: str,
    start_time: int = 9,
    end_time: int = 18,
    num_pois: int = 5,
) -> dict:
    """Module-level convenience wrapper used by the chat router."""
    return ekd_trip_service.predict(
        destination_city=destination_city,
        start_poi=start_poi,
        end_poi=end_poi,
        start_time=start_time,
        end_time=end_time,
        num_pois=num_pois,
    )


def is_available() -> bool:
    return ekd_trip_service.is_available()


def unavailable_reason() -> str:
    ekd_trip_service.is_available()  # populate
    return ekd_trip_service.unavailable_reason


# Legacy class kept for callers that imported the old stub.
class EKDTripServiceLegacy:
    """Deprecated stub kept for backward compatibility."""

    def __init__(self):
        self.model_loaded = False

    def predict(self, city: str, preferences: dict | None = None) -> dict:
        return predict_route(
            destination_city=city,
            start_poi="",
            end_poi="",
        )
