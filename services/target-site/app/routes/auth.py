from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import COOKIE_NAME, get_current_user_optional
from app.models import User
from app.schemas import UserCreate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])

templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def _set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        # secure=False для dev (http). В prod — True.
    )


# ---------- Register ----------
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": None}
    )


@router.post("/register")
async def register(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    # Pydantic-валидация (длина, формат email)
    try:
        payload = UserCreate(username=username, email=email, password=password)
    except Exception as e:
        if _wants_json(request):
            return JSONResponse({"detail": str(e)}, status_code=400)
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Проверьте поля: логин ≥3, пароль ≥6, валидный email."},
            status_code=400,
        )

    # Проверка уникальности
    exists = await db.execute(
        select(User).where((User.username == payload.username) | (User.email == payload.email))
    )
    if exists.scalar_one_or_none() is not None:
        if _wants_json(request):
            return JSONResponse({"detail": "username or email already taken"}, status_code=409)
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Логин или email уже заняты."},
            status_code=409,
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Автологин после регистрации
    token = create_access_token(user.id)

    if _wants_json(request):
        resp = JSONResponse(
            {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username}},
            status_code=201,
        )
        _set_auth_cookie(resp, token)
        return resp

    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _set_auth_cookie(resp, token)
    return resp


# ---------- Login ----------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    # Намеренно БЕЗ rate limit — для brute-force в детекторе.
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        if _wants_json(request):
            return JSONResponse({"detail": "invalid credentials"}, status_code=401)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль."},
            status_code=401,
        )

    token = create_access_token(user.id)

    if _wants_json(request):
        resp = JSONResponse(
            {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username}},
        )
        _set_auth_cookie(resp, token)
        return resp

    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _set_auth_cookie(resp, token)
    return resp


# ---------- Logout ----------
@router.get("/logout")
async def logout(request: Request):
    if _wants_json(request):
        resp = JSONResponse({"detail": "logged out"})
    else:
        resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---------- Me ----------
@router.get("/api/me")
async def me(user: Annotated[User | None, Depends(get_current_user_optional)]):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_admin}