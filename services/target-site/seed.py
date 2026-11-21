"""Скрипт наполнения БД тестовыми данными.

Запуск:
    docker compose exec target-site python seed.py
"""
import asyncio
import random
import sys

from faker import Faker
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Comment, Like, Post, User
from app.security import hash_password

fake = Faker("ru_RU")  # Русские имена и тексты

# Настройки генерации
NUM_USERS = 20
NUM_POSTS = 200
NUM_LIKES = 1000
NUM_COMMENTS = 300
ADMIN_USERNAMES = ["alice", "admin", "moderator"]

# Пул пользователей (будут созданы)
USERNAMES = [
    "alice", "bob", "charlie", "dave", "eve",
    "frank", "grace", "heidi", "ivan", "judy",
    "karl", "laura", "mallory", "niaj", "olivia",
    "peggy", "quentin", "rupert", "sybil", "trent",
]

POST_TEMPLATES = [
    "Только что посмотрел {movie}. Рекомендую! 🍿",
    "Погода сегодня просто {weather}. ☀️",
    "Кто-нибудь знает, как починить {thing}?",
    "Наконец-то доделал проект по {topic}. Ура! 🎉",
    "Завтра иду на {event}. Кто со мной?",
    "Не могу перестать слушать {band}. 🎵",
    "Купил новый {gadget}. Впечатления смешанные.",
    "Прочитал книгу «{book}». Мысли?",
    "Обед сегодня — {food}. Вкусно! 🍔",
    "Что-то я залипаю в {game}. Помогите.",
]

MOVIES = ["Интерстеллар", "Начало", "Матрицу", "Дюну", "Оппенгеймера"]
WEATHERS = ["отличная", "ужасная", "странная", "дождливая", "солнечная"]
THINGS = ["принтер", "роутер", "велосипед", "ноутбук", "телефон"]
TOPICS = ["FastAPI", "машинному обучению", "Docker", "Kubernetes", "Python"]
EVENTS = ["концерт", "митап", "выставку", "кино", "конференцию"]
BANDS = ["Radiohead", "Кино", "Muse", "Placebo", "The Beatles"]
GADGETS = ["iPhone", "ноутбук", "умные часы", "наушники", "робот-пылесос"]
BOOKS = ["1984", "Мастер и Маргарита", "Гарри Поттер", "Дюна", "Преступление и наказание"]
FOODS = ["пицца", "борщ", "суши", "бургер", "паста"]
GAMES = ["Dota 2", "CS2", "Minecraft", "Elden Ring", "Genshin Impact"]


def generate_post_content() -> str:
    template = random.choice(POST_TEMPLATES)
    return template.format(
        movie=random.choice(MOVIES),
        weather=random.choice(WEATHERS),
        thing=random.choice(THINGS),
        topic=random.choice(TOPICS),
        event=random.choice(EVENTS),
        band=random.choice(BANDS),
        gadget=random.choice(GADGETS),
        book=random.choice(BOOKS),
        food=random.choice(FOODS),
        game=random.choice(GAMES),
    )


async def seed() -> None:
    async with SessionLocal() as db:
        print("🧹 Очистка старых данных...")
        # Удаляем в правильном порядке (сначала дочерние)
        await db.execute(delete(Comment))
        await db.execute(delete(Like))
        await db.execute(delete(Post))
        await db.execute(delete(User))
        await db.commit()

        print(f"👤 Создание {NUM_USERS} пользователей...")
        users: list[User] = []
        for i in range(NUM_USERS):
            username = USERNAMES[i]
            user = User(
                username=username,
                email=f"{username}@example.com",
                password_hash=hash_password("password123"),
                bio=fake.sentence(nb_words=10),
                is_admin=(username in ADMIN_USERNAMES),
            )
            db.add(user)
            users.append(user)
        await db.commit()
        for u in users:
            await db.refresh(u)

        print(f"📝 Создание {NUM_POSTS} постов...")
        posts: list[Post] = []
        for _ in range(NUM_POSTS):
            author = random.choice(users)
            post = Post(
                author_id=author.id,
                content=generate_post_content(),
                image_url=None,  # без картинок, чтобы не плодить 404
            )
            db.add(post)
            posts.append(post)
        await db.commit()
        for p in posts:
            await db.refresh(p)

        print(f"❤️ Создание {NUM_LIKES} лайков...")
        # Используем set, чтобы не было дублей (unique constraint user_id + post_id)
        seen_likes: set[tuple[int, int]] = set()
        likes_created = 0
        attempts = 0
        while likes_created < NUM_LIKES and attempts < NUM_LIKES * 10:
            attempts += 1
            user = random.choice(users)
            post = random.choice(posts)
            key = (user.id, post.id)
            if key in seen_likes:
                continue
            seen_likes.add(key)
            db.add(Like(user_id=user.id, post_id=post.id))
            likes_created += 1
            if likes_created % 100 == 0:
                await db.commit()
        await db.commit()
        print(f"   создано {likes_created} лайков")

        print(f"💬 Создание {NUM_COMMENTS} комментариев...")
        for _ in range(NUM_COMMENTS):
            user = random.choice(users)
            post = random.choice(posts)
            comment = Comment(
                post_id=post.id,
                author_id=user.id,
                content=fake.sentence(nb_words=12),
            )
            db.add(comment)
        await db.commit()

        # Итог
        users_count = (await db.execute(select(User))).scalars().all()
        posts_count = (await db.execute(select(Post))).scalars().all()
        likes_count = (await db.execute(select(Like))).scalars().all()
        comments_count = (await db.execute(select(Comment))).scalars().all()

        print("\n✅ Готово!")
        print(f"   Пользователей: {len(users_count)}")
        print(f"   Постов:        {len(posts_count)}")
        print(f"   Лайков:        {len(likes_count)}")
        print(f"   Комментариев:  {len(comments_count)}")
        print(f"\n🔑 Пароль для всех: password123")
        print(f"👑 Админы: {', '.join(ADMIN_USERNAMES)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        # для CI/CD
        pass
    asyncio.run(seed())