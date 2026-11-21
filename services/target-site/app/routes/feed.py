from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user_optional
from app.models import Comment, Like, Post, User

router = APIRouter(tags=["feed"])
templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


async def _load_feed(
    db: AsyncSession, page: int, page_size: int
) -> tuple[list[dict], int]:
    """Возвращает (items, total). Намеренно без selectinload → N+1."""
    total = (await db.execute(select(func.count()).select_from(Post))).scalar_one()

    offset = (page - 1) * page_size
    # Намеренно без joinload: для каждого поста ниже отдельный запрос автора,
    # лайков и комментариев. Это даёт N+1 и «тяжёлую» ленту — фича для детектора.
    posts_result = await db.execute(
        select(Post).order_by(Post.created_at.desc()).offset(offset).limit(page_size)
    )
    posts = posts_result.scalars().all()

    items: list[dict] = []
    for p in posts:
        author = (
            await db.execute(select(User).where(User.id == p.author_id))
        ).scalar_one()
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
        items.append(
            {
                "id": p.id,
                "author": {"id": author.id, "username": author.username},
                "content": p.content,
                "image_url": p.image_url,
                "created_at": p.created_at,
                "likes_count": likes_count,
                "comments_count": comments_count,
            }
        )
    return items, total


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    page: int = 1,
    limit: int = settings.DEFAULT_PAGE_SIZE,
):
    # Намеренно без верхней границы по limit — ?limit=100000 работает.
    if page < 1:
        page = 1
    if limit < 1:
        limit = 1

    items, total = await _load_feed(db, page, limit)

    if _wants_json(request):
        return JSONResponse(
            {
                "items": [
                    {**it, "created_at": it["created_at"].isoformat()} for it in items
                ],
                "page": page,
                "page_size": limit,
                "total": total,
                "has_next": page * limit < total,
            }
        )

    return templates.TemplateResponse(
        "feed.html",
        {
            "request": request,
            "user": user,
            "items": items,
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.get("/feed")
async def feed_json(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    limit: int = settings.DEFAULT_PAGE_SIZE,
):
    """JSON-лента без HTML — удобно для ботов и тестов."""
    if page < 1:
        page = 1
    if limit < 1:
        limit = 1
    items, total = await _load_feed(db, page, limit)
    return JSONResponse(
        {
            "items": [{**it, "created_at": it["created_at"].isoformat()} for it in items],
            "page": page,
            "page_size": limit,
            "total": total,
            "has_next": page * limit < total,
        }
    )