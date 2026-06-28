from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.route import Route
from models.user import User
from routers.auth import get_current_user
from schemas.plan import RoutePlanRequest, RoutePlanResponse
from services.route_decision import determine_algorithm

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/route", response_model=RoutePlanResponse)
async def create_route_plan(
    body: RoutePlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new route plan and persist to database."""
    algorithm = determine_algorithm(
        destination_city=body.destination_city,
        source_city=body.source_city,
    )

    plan_id = str(uuid.uuid4())

    # Store query input
    query_input = {
        "destination_city": body.destination_city,
        "source_city": body.source_city,
        "days": body.days,
        "preferences": body.preferences,
        "budget": body.budget,
        "travel_style": body.travel_style,
    }

    # Persist to database
    route = Route(
        user_id=current_user.id,
        city=body.destination_city,
        algorithm_used=algorithm,
        query_input=json.dumps(query_input, ensure_ascii=False),
        route_result=None,  # Will be filled after algorithm execution
        intent_data=None,
        summary=f"Plan for {body.destination_city} using {algorithm} ({body.days} days).",
    )
    db.add(route)
    db.commit()
    db.refresh(route)

    return RoutePlanResponse(
        plan_id=str(route.id),
        city=body.destination_city,
        algorithm=algorithm,
        days=[],
        summary=route.summary,
    )


@router.get("/history", response_model=list[RoutePlanResponse])
async def get_plan_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all route plans for current user."""
    routes = (
        db.query(Route)
        .filter(Route.user_id == current_user.id)
        .order_by(Route.created_at.desc())
        .all()
    )
    results = []
    for r in routes:
        results.append(
            RoutePlanResponse(
                plan_id=str(r.id),
                city=r.city,
                algorithm=r.algorithm_used,
                days=[],
                summary=r.summary,
            )
        )
    return results


@router.get("/{plan_id}", response_model=RoutePlanResponse)
async def get_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific plan by ID."""
    route = (
        db.query(Route)
        .filter(Route.id == int(plan_id), Route.user_id == current_user.id)
        .first()
    )
    if not route:
        raise HTTPException(status_code=404, detail="Plan not found")

    return RoutePlanResponse(
        plan_id=str(route.id),
        city=route.city,
        algorithm=route.algorithm_used,
        days=[],
        summary=route.summary,
    )
