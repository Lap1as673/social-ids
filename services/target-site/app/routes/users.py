from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user_optional
from app.models import Comment, Like, Post, User

router = APIRouter(tags=["users"])
templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


async def _load_profile_data(
    db: AsyncSession, user: User, page: int, limit: int
) -> dict:
    # Счётчики
    posts_count = (
        await db.execute(
            select(func.count()).select_from(Post).where(Post.author_id == user.id)
        )
    ).scalar_one()
    likes_given = (
        await db.execute(
            select(func.count()).select_from(Like).where(Like.user_id == user.id)
        )
    ).scalar_one()
    comments_count = (
        await db.execute(
            select(func.count()).select_from(Comment).where(Comment.author_id == user.id)
        )
    ).scalar_one()

    # Посты пользователя (с пагинацией)
    offset = (page - 1) * limit
    posts_result = await db.execute(
        select(Post)
        .where(Post.author_id == user.id)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    posts = posts_result.scalars().all()

    # Для каждого поста — счётчики (намеренно N+1, как в ленте)
    post_items: list[dict] = []
    for p in posts:
        likes_count = (
            await db.execute(
                select(func.count()).select_from(Like).where(Like.post_id == p.id)
            )
        ).scalar_one()
        comments_count_p = (
            await db.execute(
                select(func.count()).select_from(Comment).where(Comment.post_id == p.id)
            )
        ).scalar_one()
        post_items.append(
            {
                "id": p.id,
                "content": p.content,
                "image_url": p.image_url,
                "created_at": p.created_at,
                "likes_count": likes_count,
                "comments_count": comments_count_p,
            }
        )

    return {
        "user": user,
        "posts_count": posts_count,
        "likes_given": likes_given,
        "comments_count": comments_count,
        "posts": post_items,
        "total_posts": posts_count,
    }


@router.get("/user/{username}", response_class=HTMLResponse)
async def profile(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
    page: int = 1,
    limit: int = settings.DEFAULT_PAGE_SIZE,
):
    result = await db.execute(select(User).where(User.username == username))
    profile_user = result.scalar_one_or_none()
    if profile_user is None:
        raise HTTPException(status_code=404, detail="user not found")

    if page < 1:
        page = 1
    if limit < 1:
        limit = 1

    data = await _load_profile_data(db, profile_user, page, limit)

    if _wants_json(request):
        return JSONResponse(
            {
                "user": {
                    "id": profile_user.id,
                    "username": profile_user.username,
                    "bio": profile_user.bio,
                    "created_at": profile_user.created_at.isoformat(),
                },
                "stats": {
                    "posts": data["posts_count"],
                    "likes_given": data["likes_given"],
                    "comments": data["comments_count"],
                },
                "posts": [
                    {**p, "created_at": p["created_at"].isoformat()}
                    for p in data["posts"]
                ],
                "page": page,
                "page_size": limit,
                "total": data["total_posts"],
                "has_next": page * limit < data["total_posts"],
            }
        )

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "profile_user": profile_user,
            "stats": {
                "posts": data["posts_count"],
                "likes_given": data["likes_given"],
                "comments": data["comments_count"],
            },
            "posts": data["posts"],
            "page": page,
            "limit": limit,
            "total": data["total_posts"],
            "has_next": page * limit < data["total_posts"],
            "has_prev": page > 1,
        },
    )