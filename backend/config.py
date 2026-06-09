from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    MAX_UPLOAD_SIZE_MB: int = 500
    UPLOAD_DIR: str = "/tmp/retailsense_uploads"

    DEMO_EMAIL: str = "demo@retailsense.io"
    DEMO_PASSWORD: str = "Demo@RetailSense2024"

    class Config:
        env_file = ".env"


settings = Settings()
