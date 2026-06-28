from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from routers.auth import get_current_user
from schemas.auth import UserInfo

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=UserInfo)
async def get_profile(current_user: User = Depends(get_current_user)):
    prefs = None
    if current_user.preferences:
        try:
            prefs = json.loads(current_user.preferences) if isinstance(current_user.preferences, str) else current_user.preferences
        except (json.JSONDecodeError, TypeError):
            prefs = None

    return UserInfo(
        username=current_user.username,
        nickname=current_user.nickname,
        avatar=current_user.avatar,
        preferences=prefs,
    )


@router.put("/profile", response_model=UserInfo)
async def update_profile(
    nickname: str | None = None,
    avatar: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if nickname is not None:
        current_user.nickname = nickname
    if avatar is not None:
        current_user.avatar = avatar

    db.commit()
    db.refresh(current_user)

    return UserInfo(
        username=current_user.username,
        nickname=current_user.nickname,
        avatar=current_user.avatar,
    )


@router.put("/preferences")
async def update_preferences(
    preferences: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.preferences = json.dumps(preferences, ensure_ascii=False)
    db.commit()

    return {"message": "Preferences updated", "preferences": preferences}
