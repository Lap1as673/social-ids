from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "MiniLink"
    APP_ENV: str = "dev"
    SECRET_KEY: str = "change-me"
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # DB
    DATABASE_URL: str = "postgresql+asyncpg://social:social@localhost:5432/social"

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100  # намеренно большой (для уязвимости)

    # Uploads
    UPLOAD_DIR: str = "app/static/uploads"
    UPLOAD_URL_PREFIX: str = "/static/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Debug / admin
    DEBUG_OPEN: bool = True

settings = Settings()