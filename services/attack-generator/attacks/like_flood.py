import asyncio
import httpx
from . import TARGET_URL, login

async def run_like_flood(username: str = "bob", post_id: int = 1, count: int = 500):
    """Ставит лайки на пост count раз."""
    print(f"❤️ Starting Like Flood on post #{post_id} ({count} times)...")
    
    async with httpx.AsyncClient() as client:
        token = await login(client, username, "password123")
        if not token:
            print("Login failed")
            return
            
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        
        for _ in range(count):
            try:
                await client.post(f"{TARGET_URL}/posts/{post_id}/like?format=json", headers=headers, timeout=2.0)
            except Exception:
                pass
                
    print("✅ Like Flood finished.")