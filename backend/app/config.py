"""
Application Configuration — pydantic-settings
All sensitive values are loaded from environment variables / .env file
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Attender"
    APP_ENV: str = "development"  # development | production
    DEBUG: bool = True

    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/attender"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # JWT
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-256-BIT-RANDOM"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis (Upstash or local)
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://attender.vercel.app",
    ]

    # Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.85  # Cosine similarity (0-1)
    LIVENESS_SCORE_THRESHOLD: float = 0.85
    INSIGHTFACE_MODEL: str = "buffalo_l"
    MAX_FACE_ENROLLMENT_IMAGES: int = 5

    # GPS / Geofencing
    DEFAULT_GEOFENCE_RADIUS_METERS: int = 100
    MAX_TRAVEL_SPEED_KMH: float = 200.0
    GPS_IP_MAX_DISCREPANCY_KM: float = 50.0

    # HMAC for liveness token
    LIVENESS_TOKEN_SECRET: str = "CHANGE-ME-LIVENESS-SECRET"
    LIVENESS_TOKEN_TTL_SECONDS: int = 30

    # Email (Resend)
    RESEND_API_KEY: str = ""

    # Storage (Supabase Storage)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
