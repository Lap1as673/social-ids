import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.deps import get_current_user
from app.models import User

router = APIRouter(tags=["upload"])

# Разрешённые расширения (намеренно поверхностная проверка — только по имени файла).
# MIME и содержимое НЕ проверяем — это фича для детектора.
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    # 1) Проверка расширения (поверхностная)
    original_name = file.filename or ""
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file type, allowed: {sorted(ALLOWED_EXT)}",
        )

    # 2) Читаем содержимое
    data = await file.read()

    # 3) Мягкий лимит размера
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"file too large, max {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    # 4) Уникальное имя
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename

    # 5) Пишем на диск (синхронно — ок для демо)
    dest.write_bytes(data)

    url = f"{settings.UPLOAD_URL_PREFIX}/{filename}"

    # Намеренно: не пишем в БД, не ограничиваем частоту.
    # На этапе 9 (seed) можем добавить запись в uploads-таблицу, но не обязательно.
    return JSONResponse(
        {
            "filename": filename,
            "url": url,
            "size": len(data),
            "content_type": file.content_type,
        },
        status_code=201,
    )