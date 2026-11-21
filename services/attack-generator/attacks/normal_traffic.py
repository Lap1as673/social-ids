import asyncio
import random
import httpx
from faker import Faker
from . import TARGET_URL, login, get_feed_posts

fake = Faker("ru_RU")

async def run_normal_traffic(duration: int = 60):
    """Генерирует нормальный трафик в течение duration секунд."""
    users = ["alice", "bob", "charlie", "dave", "eve"] # Из нашего seed.py
    password = "password123"
    
    async with httpx.AsyncClient() as client:
        # 1. Логинимся
        username = random.choice(users)
        token = await login(client, username, password)
        if not token:
            print(f"Failed to login as {username}")
            return
        
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        print(f"👤 Logged in as {username}. Generating normal traffic for {duration}s...")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < duration:
            action = random.choices(
                ["view_feed", "like", "comment"], 
                weights=[0.7, 0.2, 0.1], 
                k=1
            )[0]
            
            try:
                if action == "view_feed":
                    # Просто листаем ленту
                    await client.get(f"{TARGET_URL}/feed?format=json", headers=headers)
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    
                elif action == "like":
                    posts = await get_feed_posts(client, limit=10)
                    if posts:
                        post_id = random.choice(posts)["id"]
                        await client.post(f"{TARGET_URL}/posts/{post_id}/like?format=json", headers=headers)
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                    
                elif action == "comment":
                    posts = await get_feed_posts(client, limit=10)
                    if posts:
                        post_id = random.choice(posts)["id"]
                        text = fake.sentence()
                        await client.post(
                            f"{TARGET_URL}/posts/{post_id}/comments?format=json",
                            headers=headers,
                            json={"content": text}
                        )
                    await asyncio.sleep(random.uniform(3.0, 7.0))
                    
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(1.0)
                
    print("✅ Normal traffic finished.")