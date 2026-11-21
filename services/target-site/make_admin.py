"""Сделать пользователя админом: python make_admin.py <username>"""
import asyncio
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User


async def main(username: str) -> None:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if user is None:
            print(f"user '{username}' not found")
            return
        user.is_admin = True
        await db.commit()
        print(f"@{username} is now admin")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python make_admin.py <username>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))