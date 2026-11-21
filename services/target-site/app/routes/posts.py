from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models import Comment, Like, Post, User
from app.schemas import PostCreate

router = APIRouter(tags=["posts"])
templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


# ---------- Create ----------
@router.post("/posts")
async def create_post(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # Поддерживаем и JSON, и form
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    try:
        payload = PostCreate(
            content=data.get("content", ""),
            image_url=data.get("image_url") or None,
        )
    except Exception as e:
        if _wants_json(request) or "application/json" in content_type:
            return JSONResponse({"detail": str(e)}, status_code=400)
        raise HTTPException(status_code=400, detail="invalid post data")

    post = Post(author_id=user.id, content=payload.content, image_url=payload.image_url)
    db.add(post)
    await db.commit()
    await db.refresh(post)

    if _wants_json(request) or "application/json" in content_type:
        return JSONResponse(
            {
                "id": post.id,
                "author_id": post.author_id,
                "content": post.content,
                "image_url": post.image_url,
                "created_at": post.created_at.isoformat(),
            },
            status_code=201,
        )

    return RedirectResponse(url=f"/posts/{post.id}", status_code=status.HTTP_303_SEE_OTHER)


# ---------- Read (HTML + JSON) ----------
@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def get_post(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")

    # Автор
    author_result = await db.execute(select(User).where(User.id == post.author_id))
    author = author_result.scalar_one()

    # Счётчики
    likes_count = (
        await db.execute(select(func.count()).select_from(Like).where(Like.post_id == post.id))
    ).scalar_one()
    comments_count = (
        await db.execute(
            select(func.count()).select_from(Comment).where(Comment.post_id == post.id)
        )
    ).scalar_one()

    # Комментарии (простым запросом — N+1 тут не критичен)
    comments_result = await db.execute(
        select(Comment).where(Comment.post_id == post.id).order_by(Comment.created_at.asc())
    )
    comments = comments_result.scalars().all()

    if _wants_json(request):
        return JSONResponse(
            {
                "id": post.id,
                "author": {"id": author.id, "username": author.username},
                "content": post.content,
                "image_url": post.image_url,
                "created_at": post.created_at.isoformat(),
                "likes_count": likes_count,
                "comments_count": comments_count,
            }
        )

    return templates.TemplateResponse(
        "post.html",
        {
            "request": request,
            "user": user,
            "post": post,
            "author": author,
            "likes_count": likes_count,
            "comments_count": comments_count,
            "comments": comments,
        },
    )


# ---------- Delete ----------
@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    if post.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="not allowed")

    await db.delete(post)
    await db.commit()
    return {"detail": "deleted"}