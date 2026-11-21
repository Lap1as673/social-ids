from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user_optional
from app.models import Comment, Like, Post, User

router = APIRouter(tags=["search"])
templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


async def _search(
    db: AsyncSession,
    q: str,
    limit: int,
) -> dict:
    """Поиск по постам и пользователям.

    Намеренно используется ILIKE '%q%' без GIN/pg_trgm индексов:
    на больших объёмах это медленно → удобно для Slowloris.
    """
    if not q:
        return {"users": [], "posts": [], "total_users": 0, "total_posts": 0}

    pattern = f"%{q}%"

    # --- Пользователи ---
    # Намеренно без индекса по username в ILIKE (индекс есть, но btree не помогает для '%q%')
    users_result = await db.execute(
        select(User)
        .where(or_(User.username.ilike(pattern), User.bio.ilike(pattern)))
        .order_by(User.username.asc())
        .limit(limit)
    )
    users = users_result.scalars().all()

    total_users = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(or_(User.username.ilike(pattern), User.bio.ilike(pattern)))
        )
    ).scalar_one()

    # --- Посты ---
    posts_result = await db.execute(
        select(Post)
        .where(Post.content.ilike(pattern))
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    posts = posts_result.scalars().all()

    total_posts = (
        await db.execute(
            select(func.count()).select_from(Post).where(Post.content.ilike(pattern))
        )
    ).scalar_one()

    # Авторы постов (одним запросом)
    author_ids = {p.author_id for p in posts}
    authors_map: dict[int, str] = {}
    if author_ids:
        authors = (
            await db.execute(select(User).where(User.id.in_(author_ids)))
        ).scalars().all()
        authors_map = {u.id: u.username for u in authors}

    post_items: list[dict] = []
    for p in posts:
        likes_count = (
            await db.execute(
                select(func.count()).select_from(Like).where(Like.post_id == p.id)
            )
        ).scalar_one()
        comments_count = (
            await db.execute(
                select(func.count()).select_from(Comment).where(Comment.post_id == p.id)
            )
        ).scalar_one()
        post_items.append(
            {
                "id": p.id,
                "author": {"id": p.author_id, "username": authors_map.get(p.author_id, "?")},
                "content": p.content,
                "image_url": p.image_url,
                "created_at": p.created_at,
                "likes_count": likes_count,
                "comments_count": comments_count,
            }
        )

    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "bio": u.bio,
                "created_at": u.created_at,
            }
            for u in users
        ],
        "posts": post_items,
        "total_users": total_users,
        "total_posts": total_posts,
    }


@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    q: str = "",
    limit: int = settings.DEFAULT_PAGE_SIZE,
):
    # Намеренно без верхней границы на limit — ?limit=100000 работает.
    if limit < 1:
        limit = 1

    results = await _search(db, q.strip(), limit)

    if _wants_json(request):
        return JSONResponse(
            {
                "query": q,
                "users": [
                    {**u, "created_at": u["created_at"].isoformat()} for u in results["users"]
                ],
                "posts": [
                    {**p, "created_at": p["created_at"].isoformat()} for p in results["posts"]
                ],
                "total_users": results["total_users"],
                "total_posts": results["total_posts"],
                "limit": limit,
            }
        )

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "user": user,
            "q": q,
            "results": results,
            "limit": limit,
        },
    )