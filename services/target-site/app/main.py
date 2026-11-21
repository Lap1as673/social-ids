from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.db import init_db
from app.routes import admin, auth, comments, feed, likes, posts, search, upload, users

# 1. Импортируем наши обработчики ошибок
from app.errors import http_exception_handler, server_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    from app.db import engine
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# 2. Подключаем обработчики ошибок
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, server_error_handler)

# Монтируем статику
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(feed.router)
app.include_router(likes.router)
app.include_router(comments.router)
app.include_router(users.router)
app.include_router(search.router)
app.include_router(upload.router)
app.include_router(admin.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}