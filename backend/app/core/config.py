from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lens:lens@localhost:5432/lecturelens"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://lens:lens@localhost:5432/lecturelens"

    # Auth / JWT
    JWT_SECRET: str = "change-me-generate-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # CORS
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000"

    # Redis / ARQ
    REDIS_URL: str = "redis://localhost:6379"

    # Object storage
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    LOCAL_STORAGE_PATH: str = (
        "/tmp/lecturelens"  # nosec B108 — dev default, overridden by env var in prod
    )
    S3_BUCKET: str = ""
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # ML
    WHISPER_MODEL_SIZE: str = "base"
    FAISS_INDEX_PATH: str = "/tmp/lecturelens/faiss.index"  # nosec B108 — dev default

    # Upload limits
    MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024  # 50 MB


settings = Settings()
