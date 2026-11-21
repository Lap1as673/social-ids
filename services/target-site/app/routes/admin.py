from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models import Comment, Like, Post, User

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


# ---------- /debug (намеренно открыт) ----------
@router.get("/debug", response_class=HTMLResponse)
async def debug_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
):
    # Намеренная уязвимость: без проверки авторизации.
    # Отдаём версии, фрагмент env, список роутов, счётчики БД.
    import os
    import sys

    import fastapi
    import sqlalchemy

    # Собираем роуты
    routes = []
    for r in request.app.routes:
        path = getattr(r, "path", None)
        methods = sorted(getattr(r, "methods", []) or [])
        name = getattr(r, "name", None)
        if path is not None:
            routes.append({"path": path, "methods": methods, "name": name})

    # Счётчики БД
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    posts_count = (await db.execute(select(func.count()).select_from(Post))).scalar_one()
    likes_count = (await db.execute(select(func.count()).select_from(Like))).scalar_one()
    comments_count = (
        await db.execute(select(func.count()).select_from(Comment))
    ).scalar_one()

    # Фрагмент env — намеренно показываем «интересное»
    env_safe = {
        "APP_NAME": settings.APP_NAME,
        "APP_ENV": settings.APP_ENV,
        "JWT_ALG": settings.JWT_ALG,
        "JWT_EXPIRE_MINUTES": str(settings.JWT_EXPIRE_MINUTES),
        # DATABASE_URL показываем частично, чтобы не палить пароль в открытом виде
        "DATABASE_URL": _mask_dsn(settings.DATABASE_URL),
        "PYTHON_VERSION": sys.version.split()[0],
        "PLATFORM": sys.platform,
        "CWD": os.getcwd(),
    }

    payload = {
        "versions": {
            "fastapi": fastapi.__version__,
            "sqlalchemy": sqlalchemy.__version__,
            "python": sys.version.split()[0],
        },
        "env": env_safe,
        "counts": {
            "users": users_count,
            "posts": posts_count,
            "likes": likes_count,
            "comments": comments_count,
        },
        "routes": routes,
        "current_user": (
            {"id": user.id, "username": user.username, "is_admin": user.is_admin}
            if user
            else None
        ),
    }

    if _wants_json(request):
        return JSONResponse(payload)

    return templates.TemplateResponse(
        "debug.html",
        {"request": request, "user": user, "data": payload},
    )


def _mask_dsn(dsn: str) -> str:
    """postgresql+asyncpg://user:pass@host:port/db -> ...://user:***@host:port/db"""
    try:
        scheme, rest = dsn.split("://", 1)
        creds, hostpart = rest.split("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            creds = f"{user}:***"
        return f"{scheme}://{creds}@{hostpart}"
    except Exception:
        return "***"


# ---------- /admin (только админ) ----------
@router.get("/admin", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")

    users_result = await db.execute(select(User).order_by(User.id.asc()))
    users = users_result.scalars().all()

    posts_result = await db.execute(
        select(Post).order_by(Post.created_at.desc()).limit(50)
    )
    posts = posts_result.scalars().all()

    if _wants_json(request):
        return JSONResponse(
            {
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "is_admin": u.is_admin,
                        "created_at": u.created_at.isoformat(),
                    }
                    for u in users
                ],
                "recent_posts": [
                    {
                        "id": p.id,
                        "author_id": p.author_id,
                        "content": p.content[:120],
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in posts
                ],
            }
        )

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "user": user, "users": users, "posts": posts},
    )


@router.post("/admin/user/{user_id}/toggle-admin")
async def toggle_admin(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="user not found")
    if target.id == current.id:
        raise HTTPException(status_code=400, detail="cannot change own admin flag")
    target.is_admin = not target.is_admin
    await db.commit()
    return {"id": target.id, "username": target.username, "is_admin": target.is_admin}


@router.delete("/admin/post/{post_id}")
async def admin_delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    await db.delete(post)
    await db.commit()
    return {"detail": "deleted", "id": post_id}