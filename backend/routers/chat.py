from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from config import settings
from database import get_db
from models.dialog import Dialog
from models.user import User
from routers.auth import get_current_user
from schemas.chat import ChatRequest, DialogDetail, DialogSummary
from services import cross_city as cross_city_service
from services import ekd_trip as ekd_trip_service
from services.llm_agent import DeepSeekAgent
from services.mock_data import get_mock_route
from services.route_decision import determine_algorithm

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# SSE event helpers
# ---------------------------------------------------------------------------
def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event with named event type and JSON data."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Streaming generators
# ---------------------------------------------------------------------------
async def _stream_mock_route(mock_route: dict, algorithm: str):
    """Replay a mock route as SSE events with realistic timing.

    Mirrors the frontend simulateSSEStream logic.
    """
    # 1. Thinking
    yield _sse_event("thinking", {
        "status": "planning",
        "text": "正在为您规划路线...",
        "algorithm": algorithm,
    })
    await asyncio.sleep(0.8)

    # 2. Route intro text
    city = mock_route.get("city", "")
    pois = mock_route.get("route_result", {}).get("route", [])
    intro = f"好的，我为您规划了一条{city}旅行路线，共{len(pois)}个景点。\n\n"
    for i in range(0, len(intro), 3):
        yield _sse_event("route_text", {"delta": intro[i:i + 3]})
        await asyncio.sleep(0.03)
    await asyncio.sleep(0.3)

    # 3. For each POI, send poi_added then route_text description
    for poi in pois:
        yield _sse_event("poi_added", {"poi": poi})
        await asyncio.sleep(0.4)

        desc = f"**第{poi.get('visit_order', '?')}站：{poi.get('name', '')}**\n"
        desc += f"类型： {poi.get('category', '')}\n"
        desc += f"建议游玩时长： {poi.get('recommended_duration_min', 60)}分钟\n"
        if poi.get("description"):
            desc += f"行程亮点：\n{poi['description']}\n"
        desc += "\n"
        for i in range(0, len(desc), 5):
            yield _sse_event("route_text", {"delta": desc[i:i + 5]})
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.5)

    # 4. Intent data
    intent_data = mock_route.get("intent_data")
    if intent_data:
        await asyncio.sleep(0.3)
        yield _sse_event("intent_data", intent_data)
        await asyncio.sleep(0.2)

        intent_text = ""
        if intent_data.get("travel_mode"):
            mode = intent_data["travel_mode"]
            conf = round(intent_data.get("travel_mode_confidence", 0) * 100)
            mode_labels = {"approaching": "接近模式", "moving_away": "远离模式", "u_turn": "U型模式", "irregular": "不规则模式"}
            intent_text = f"\n系统识别到您的出行意图为【{mode_labels.get(mode, mode)}】，置信度：{conf}%"
        elif intent_data.get("preference_factors"):
            eta = round(intent_data.get("blend_weight_eta", 0) * 100)
            intent_text = f"\n路线中{eta}%基于您的个人偏好，{100 - eta}%参考了当地热门趋势"
        elif intent_data.get("agent_reasoning"):
            reasoning = intent_data["agent_reasoning"]
            steps = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasoning))
            intent_text = f"\n\n**AI 推理过程：**\n{steps}"
            if intent_data.get("estimated_total_time_hours"):
                intent_text += (
                    f"\n\n预计游览时间：{intent_data['estimated_total_time_hours']}小时"
                    f"（含交通{intent_data.get('estimated_transport_time_min', '?')}分钟）"
                )

        for i in range(0, len(intent_text), 4):
            yield _sse_event("route_text", {"delta": intent_text[i:i + 4]})
            await asyncio.sleep(0.025)

    # 5. Done
    await asyncio.sleep(0.2)
    yield _sse_event("done", {
        "plan_id": str(uuid.uuid4()),
        "algorithm": algorithm,
        "is_mock": True,
    })


# ---------------------------------------------------------------------------
# Real-algorithm streaming
# ---------------------------------------------------------------------------
async def _stream_real_algorithm(
    algorithm: str,  # "ekd_trip" or "cross_city"
    destination_city: str,
    source_city: str | None,
    start_poi: str,
    end_poi: str,
    start_time: int,
    end_time: int,
    num_pois: int,
    user_profile: dict | None,
):
    """Run a real algorithm wrapper, then replay the result as SSE.

    The wrappers return a dict shaped exactly like the mock JSON files,
    so we can reuse :func:`_stream_mock_route` for the actual streaming.
    Errors are caught here and surfaced as an SSE ``error`` event so the
    caller can fall back to a mock generator.
    """
    label = "EKD-Trip" if algorithm == "ekd_trip" else "CrossTrip"
    yield _sse_event("thinking", {
        "status": "planning",
        "text": f"正在调用 {label} 算法为您规划路线...",
        "algorithm": label,
    })

    # Run blocking inference in a thread to avoid blocking the event loop
    try:
        if algorithm == "ekd_trip":
            result = await asyncio.to_thread(
                ekd_trip_service.predict_route,
                destination_city=destination_city,
                start_poi=start_poi,
                end_poi=end_poi,
                start_time=start_time,
                end_time=end_time,
                num_pois=num_pois,
            )
        else:
            result = await asyncio.to_thread(
                cross_city_service.predict_route,
                source_city=source_city or "",
                destination_city=destination_city,
                start_poi=start_poi,
                end_poi=end_poi,
                start_time=start_time,
                end_time=end_time,
                num_pois=num_pois,
                user_profile=user_profile,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Real %s inference failed, will fall back: %s", label, exc)
        yield _sse_event("error", {
            "message": f"{label} 算法暂不可用，将使用备用方案: {exc}",
            "fallback": True,
        })
        return

    # Re-stream the structured result via the mock streamer
    async for event in _stream_mock_route(result, label):
        yield event


async def _stream_deepseek_route(
    destination_city: str,
    start_poi: str,
    end_poi: str,
    start_time: int,
    end_time: int,
    num_pois: int,
):
    """Call DeepSeek API and stream the result as SSE events.

    Strategy: Get full structured JSON from DeepSeek (non-streaming),
    then replay it as SSE events with timing to match frontend expectations.
    """
    # 1. Thinking
    yield _sse_event("thinking", {
        "status": "planning",
        "text": "正在调用 DeepSeek AI 为您规划路线...",
        "algorithm": "DeepSeek-Agent",
    })

    # 2. Call DeepSeek (non-streaming for reliable JSON parsing)
    agent = DeepSeekAgent()
    try:
        plan = await agent.plan_route(
            destination_city=destination_city,
            start_poi=start_poi,
            end_poi=end_poi,
            start_time=start_time,
            end_time=end_time,
            num_pois=num_pois,
        )
    except Exception as e:
        yield _sse_event("error", {"message": f"DeepSeek API 调用失败: {str(e)}"})
        return

    pois = plan.get("route", [])
    if not pois:
        yield _sse_event("error", {"message": "DeepSeek 未返回有效路线"})
        return

    # 3. Stream intro text
    intro = f"好的，我为您规划了一条{destination_city}旅行路线，共{len(pois)}个景点。\n\n"
    for i in range(0, len(intro), 3):
        yield _sse_event("route_text", {"delta": intro[i:i + 3]})
        await asyncio.sleep(0.03)
    await asyncio.sleep(0.3)

    # 4. Stream each POI
    for poi in pois:
        yield _sse_event("poi_added", {"poi": poi})
        await asyncio.sleep(0.4)

        desc = f"**第{poi.get('visit_order', '?')}站：{poi.get('name', '')}**\n"
        desc += f"类型： {poi.get('category', '')}\n"
        desc += f"建议游玩时长： {poi.get('recommended_duration_min', 60)}分钟\n"
        if poi.get("description"):
            desc += f"行程亮点：\n{poi['description']}\n"
        desc += "\n"
        for i in range(0, len(desc), 5):
            yield _sse_event("route_text", {"delta": desc[i:i + 5]})
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.5)

    # 5. Intent data (DeepSeek-Agent format)
    intent_data = {
        "agent_reasoning": plan.get("agent_reasoning", []),
        "confidence": plan.get("confidence", 0.85),
        "route_type": plan.get("route_type", ""),
        "estimated_total_time_hours": plan.get("estimated_total_time_hours", 0),
        "estimated_transport_time_min": plan.get("estimated_transport_time_min", 0),
    }
    await asyncio.sleep(0.3)
    yield _sse_event("intent_data", intent_data)
    await asyncio.sleep(0.2)

    # Intent description text
    reasoning = intent_data["agent_reasoning"]
    if reasoning:
        steps = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasoning))
        intent_text = f"\n\n**AI 推理过程：**\n{steps}"
        if intent_data["estimated_total_time_hours"]:
            intent_text += (
                f"\n\n预计游览时间：{intent_data['estimated_total_time_hours']}小时"
                f"（含交通{intent_data['estimated_transport_time_min']}分钟）"
            )
        for i in range(0, len(intent_text), 4):
            yield _sse_event("route_text", {"delta": intent_text[i:i + 4]})
            await asyncio.sleep(0.025)

    # 6. Done
    await asyncio.sleep(0.2)
    yield _sse_event("done", {
        "plan_id": str(uuid.uuid4()),
        "algorithm": "DeepSeek-Agent",
        "is_mock": False,
    })


# ---------------------------------------------------------------------------
# /chat/message endpoint (real SSE pipeline)
# ---------------------------------------------------------------------------
@router.post("/message")
async def send_message(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE streaming chat endpoint with full algorithm pipeline.

    Expects body.context to optionally contain:
        - destination_city, source_city, start_poi, end_poi
        - start_time, end_time, num_stops
    """
    dialog_id = body.dialog_id or str(uuid.uuid4())
    context = body.context or {}

    # Persist user message to dialog
    dialog = db.query(Dialog).filter(Dialog.dialog_id == dialog_id).first()
    if not dialog:
        dialog = Dialog(
            dialog_id=dialog_id,
            user_id=current_user.id,
            title=body.message[:30],
            messages_json="[]",
        )
        db.add(dialog)
        db.commit()
        db.refresh(dialog)

    messages = json.loads(dialog.messages_json or "[]")
    messages.append({"role": "user", "content": body.message})
    dialog.messages_json = json.dumps(messages, ensure_ascii=False)
    db.commit()

    # Determine algorithm path based on context
    destination_city = context.get("destination_city")
    source_city = context.get("source_city")
    start_poi = context.get("start_poi", "")
    end_poi = context.get("end_poi", "")
    start_time = context.get("start_time", 9)
    end_time = context.get("end_time", 18)
    num_pois = context.get("num_stops", 5)

    if not destination_city:
        # No destination -- return error stream
        async def _err():
            yield _sse_event("error", {"message": "缺少目的城市，无法规划路线"})
            yield _sse_event("done", {"plan_id": "", "algorithm": "", "is_mock": False})
        return StreamingResponse(_err(), media_type="text/event-stream")

    algorithm = determine_algorithm(destination_city, source_city)

    # Decide generator + label for the chosen algorithm. Strategy:
    #   - llm_only         -> always DeepSeek (real LLM)
    #   - ekd_trip / cross_city, USE_REAL_ALGORITHMS=True and wrapper available
    #                      -> real algorithm with mock fallback inside the stream
    #   - ekd_trip / cross_city, USE_MOCK_DATA=True (default for demo)
    #                      -> stream the mock JSON
    #   - otherwise        -> DeepSeek as a safe fallback
    if algorithm == "llm_only":
        generator = _stream_deepseek_route(
            destination_city=destination_city,
            start_poi=start_poi,
            end_poi=end_poi,
            start_time=start_time,
            end_time=end_time,
            num_pois=num_pois,
        )
        algorithm_label = "DeepSeek-Agent"
    else:
        algorithm_label = "EKD-Trip" if algorithm == "ekd_trip" else "CrossTrip"

        wrapper = ekd_trip_service if algorithm == "ekd_trip" else cross_city_service
        real_available = settings.USE_REAL_ALGORITHMS and wrapper.is_available()

        if real_available:
            mock_route = get_mock_route(destination_city)

            async def _real_with_mock_fallback(
                _alg=algorithm,
                _dest=destination_city,
                _src=source_city,
                _sp=start_poi,
                _ep=end_poi,
                _st=start_time,
                _et=end_time,
                _np=num_pois,
                _profile=context.get("user_profile"),
                _mock=mock_route,
                _label=algorithm_label,
            ):
                # Buffer: if the real generator emits an `error` event with
                # fallback=True, switch to the mock stream from scratch.
                got_error = False
                async for ev in _stream_real_algorithm(
                    _alg, _dest, _src, _sp, _ep, _st, _et, _np, _profile,
                ):
                    if "event: error" in ev and '"fallback": true' in ev:
                        got_error = True
                        # consume but don't forward the partial error
                        continue
                    if got_error:
                        continue
                    yield ev
                if got_error:
                    async for ev in _stream_mock_route(_mock, _label):
                        yield ev

            generator = _real_with_mock_fallback()
        elif settings.USE_MOCK_DATA:
            mock_route = get_mock_route(destination_city)
            generator = _stream_mock_route(mock_route, algorithm_label)
        else:
            # Last-resort fallback: DeepSeek
            generator = _stream_deepseek_route(
                destination_city=destination_city,
                start_poi=start_poi,
                end_poi=end_poi,
                start_time=start_time,
                end_time=end_time,
                num_pois=num_pois,
            )
            algorithm_label = "DeepSeek-Agent"

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Dialog-Id": dialog_id,
            "X-Algorithm": algorithm_label,
        },
    )


# ---------------------------------------------------------------------------
# Dialog management endpoints (unchanged from Phase 2)
# ---------------------------------------------------------------------------
@router.get("/dialogs", response_model=list[DialogSummary])
async def list_dialogs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dialogs = (
        db.query(Dialog)
        .filter(Dialog.user_id == current_user.id)
        .order_by(Dialog.updated_at.desc())
        .all()
    )
    results = []
    for d in dialogs:
        messages = json.loads(d.messages_json or "[]")
        last_msg = messages[-1]["content"] if messages else None
        results.append(
            DialogSummary(
                dialog_id=d.dialog_id,
                title=d.title,
                last_message=last_msg,
                created_at=d.created_at.isoformat() if d.created_at else None,
                updated_at=d.updated_at.isoformat() if d.updated_at else None,
            )
        )
    return results


@router.get("/dialogs/{dialog_id}", response_model=DialogDetail)
async def get_dialog(
    dialog_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dialog = (
        db.query(Dialog)
        .filter(Dialog.dialog_id == dialog_id, Dialog.user_id == current_user.id)
        .first()
    )
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")

    messages = json.loads(dialog.messages_json or "[]")
    return DialogDetail(
        dialog_id=dialog.dialog_id,
        title=dialog.title,
        messages=messages,
        created_at=dialog.created_at.isoformat() if dialog.created_at else None,
        updated_at=dialog.updated_at.isoformat() if dialog.updated_at else None,
    )


@router.delete("/dialogs/{dialog_id}")
async def delete_dialog(
    dialog_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dialog = (
        db.query(Dialog)
        .filter(Dialog.dialog_id == dialog_id, Dialog.user_id == current_user.id)
        .first()
    )
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")

    db.delete(dialog)
    db.commit()
    return {"message": "Dialog deleted"}
