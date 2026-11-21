from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Like, Post, User

router = APIRouter(tags=["likes"])


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


async def _likes_count(db: AsyncSession, post_id: int) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Like).where(Like.post_id == post_id)
        )
    ).scalar_one()


# ---------- Like ----------
@router.post("/posts/{post_id}/like")
async def like_post(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # Намеренно БЕЗ rate limit — для like flood в детекторе.
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")

    existing = (
        await db.execute(
            select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        # Идемпотентность: уже лайкнут — возвращаем текущее состояние
        count = await _likes_count(db, post_id)
        return JSONResponse(
            {"detail": "already liked", "liked": True, "likes_count": count},
            status_code=200,
        )

    db.add(Like(user_id=user.id, post_id=post_id))
    await db.commit()

    count = await _likes_count(db, post_id)
    return JSONResponse(
        {"detail": "liked", "liked": True, "likes_count": count},
        status_code=201,
    )


# ---------- Unlike ----------
@router.delete("/posts/{post_id}/like")
async def unlike_post(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")

    existing = (
        await db.execute(
            select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
        )
    ).scalar_one_or_none()

    if existing is None:
        count = await _likes_count(db, post_id)
        return JSONResponse(
            {"detail": "not liked", "liked": False, "likes_count": count},
            status_code=200,
        )

    await db.delete(existing)
    await db.commit()

    count = await _likes_count(db, post_id)
    return JSONResponse(
        {"detail": "unliked", "liked": False, "likes_count": count},
        status_code=200,
    )


# ---------- Status ----------
@router.get("/posts/{post_id}/like")
async def like_status(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    existing = (
        await db.execute(
            select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
        )
    ).scalar_one_or_none()
    count = await _likes_count(db, post_id)
    return {"liked": existing is not None, "likes_count": count}