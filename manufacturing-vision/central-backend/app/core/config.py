from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://mvision:mvision@localhost:5432/mvision"
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_NAME: str = "vision.events"
    REDIS_CONSUMER_GROUP: str = "backend-consumers"
    REDIS_CONSUMER_NAME: str = "backend-1"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    ADMIN_USER: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_PUBLIC_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "vision-evidence"
    MINIO_SECURE: bool = False
    MEDIA_URL_EXPIRE_SECONDS: int = 300

    LOG_FORMAT: str = "text"  # "text" | "json"

    class Config:
        env_file = ".env"


settings = Settings()
