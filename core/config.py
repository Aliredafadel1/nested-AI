from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://nestai:nestai@db:5432/nestai"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://nestai:nestai@db:5432/nestai"
    REDIS_URL: str = "redis://redis:6379/0"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "nestai"
    MINIO_ROOT_PASSWORD: str = "nestai_secret"
    MINIO_SECURE: bool = False

    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"
    BCRYPT_WORK_FACTOR: int = 12
    COOKIE_SECURE: bool = False

    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    OSRM_URL: str = "http://osrm:5000"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@nestai.app"
    FRONTEND_URL: str = "http://localhost:3000"


settings = Settings()
