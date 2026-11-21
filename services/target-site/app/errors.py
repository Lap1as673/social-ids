from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

templates = Jinja2Templates(directory="app/templates")


def _wants_json(request: Request) -> bool:
    if request.query_params.get("format") == "json":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Для API (JSON) отдаём честный статус и detail
    if _wants_json(request):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    # Для HTML отдаём кастомные страницы
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html", {"request": request}, status_code=404
        )
    if exc.status_code == 500:
        return templates.TemplateResponse(
            "errors/500.html", {"request": request}, status_code=500
        )
    
    # Для остальных (401, 403) — простой HTML или редирект
    return HTMLResponse(
        f"<h1>{exc.status_code}</h1><p>{exc.detail}</p><a href='/'>На главную</a>",
        status_code=exc.status_code,
    )


async def server_error_handler(request: Request, exc: Exception):
    if _wants_json(request):
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)
    return templates.TemplateResponse(
        "errors/500.html", {"request": request}, status_code=500
    )