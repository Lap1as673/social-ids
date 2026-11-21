from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models import Comment, Post, User
from app.schemas import CommentCreate

router = APIRouter(tags=["comments"])
templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


# ---------- List ----------
@router.get("/posts/{post_id}/comments")
async def list_comments(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")

    result = await db.execute(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()

    # Достаём авторов одним запросом (оптимизация только здесь — не «фича»)
    author_ids = {c.author_id for c in comments}
    authors_map: dict[int, str] = {}
    if author_ids:
        authors = (
            await db.execute(select(User).where(User.id.in_(author_ids)))
        ).scalars().all()
        authors_map = {u.id: u.username for u in authors}

    return JSONResponse(
        {
            "items": [
                {
                    "id": c.id,
                    "post_id": c.post_id,
                    "author": {"id": c.author_id, "username": authors_map.get(c.author_id, "?")},
                    "content": c.content,
                    "created_at": c.created_at.isoformat(),
                }
                for c in comments
            ],
            "total": len(comments),
        }
    )


# ---------- Create ----------
@router.post("/posts/{post_id}/comments")
async def create_comment(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # Намеренно БЕЗ rate limit и без max_length — comment flood возможен.
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    try:
        payload = CommentCreate(content=data.get("content", ""))
    except Exception as e:
        if _wants_json(request) or "application/json" in content_type:
            return JSONResponse({"detail": str(e)}, status_code=400)
        raise HTTPException(status_code=400, detail="invalid comment")

    comment = Comment(post_id=post_id, author_id=user.id, content=payload.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    if _wants_json(request) or "application/json" in content_type:
        return JSONResponse(
            {
                "id": comment.id,
                "post_id": comment.post_id,
                "author": {"id": user.id, "username": user.username},
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
            },
            status_code=201,
        )

    return RedirectResponse(url=f"/posts/{post_id}", status_code=status.HTTP_303_SEE_OTHER)


# ---------- Delete ----------
@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    comment = (
        await db.execute(select(Comment).where(Comment.id == comment_id))
    ).scalar_one_or_none()
    if comment is None:
        raise HTTPException(status_code=404, detail="comment not found")
    if comment.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="not allowed")

    await db.delete(comment)
    await db.commit()
    return {"detail": "deleted"}