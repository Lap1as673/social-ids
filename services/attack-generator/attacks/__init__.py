import httpx
import os

# Базовый URL сайта (из docker-compose или локально)
TARGET_URL = os.getenv("TARGET_URL", "http://target-site:8000")

async def login(client: httpx.AsyncClient, username: str, password: str) -> str | None:
    """Логинится и возвращает JWT токен."""
    try:
        r = await client.post(
            f"{TARGET_URL}/login?format=json",
            headers={"Accept": "application/json"},
            data={"username": username, "password": password},
            timeout=5.0,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass
    return None

async def get_feed_posts(client: httpx.AsyncClient, limit: int = 20) -> list[dict]:
    """Получает список постов из ленты."""
    try:
        r = await client.get(
            f"{TARGET_URL}/feed?format=json&limit={limit}",
            headers={"Accept": "application/json"},
            timeout=5.0,
        )
        if r.status_code == 200:
            return r.json().get("items", [])
    except Exception:
        pass
    return []