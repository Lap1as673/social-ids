from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


# ---------- User ----------
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bio: str | None = None
    created_at: datetime


class UserBrief(BaseModel):
    """Короткая карточка автора — для ленты."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


# ---------- Post ----------
class PostCreate(BaseModel):
    content: str = Field(min_length=1)  # без max_length — намеренно
    image_url: str | None = None


class PostPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int
    content: str
    image_url: str | None
    created_at: datetime


class PostWithAuthor(PostPublic):
    author: UserBrief
    likes_count: int = 0
    comments_count: int = 0


# ---------- Comment ----------
class CommentCreate(BaseModel):
    content: str = Field(min_length=1)


class CommentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime


# ---------- Pagination ----------
class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    has_next: bool


class FeedPage(Page[PostWithAuthor]):
    pass