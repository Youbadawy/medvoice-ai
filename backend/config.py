"""
MedVoice AI - Configuration Management
Loads environment variables and provides type-safe configuration.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Twilio
    twilio_account_sid: str = Field(..., alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(..., alias="TWILIO_PHONE_NUMBER")

    # Deepgram
    deepgram_api_key: str = Field(..., alias="DEEPGRAM_API_KEY")

    # Google Cloud TTS (uses GOOGLE_APPLICATION_CREDENTIALS - no extra key needed)
    # TTS is authenticated via Firebase service account

    # OpenRouter
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_model_primary: str = Field(
        default="deepseek/deepseek-v3.2",
        alias="OPENROUTER_MODEL_PRIMARY"
    )
    openrouter_model_fallback: str = Field(
        default="openai/gpt-4o-mini",
        alias="OPENROUTER_MODEL_FALLBACK"
    )

    # n8n
    n8n_webhook_base_url: Optional[str] = Field(default=None, alias="N8N_WEBHOOK_BASE_URL")

    # Firebase
    firebase_project_id: Optional[str] = Field(default=None, alias="FIREBASE_PROJECT_ID")
    google_application_credentials: Optional[str] = Field(
        default=None,
        alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # Redis (optional)
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")

    # Clinic Configuration
    default_language: str = Field(default="fr", alias="DEFAULT_LANGUAGE")
    clinic_name: str = Field(
        default="Clinique KaiMed",
        alias="CLINIC_NAME"
    )
    clinic_address: str = Field(
        default="Montreal, QC",
        alias="CLINIC_ADDRESS"
    )
    clinic_hours: str = Field(
        default="Lundi-Vendredi 9h-18h",
        alias="CLINIC_HOURS"
    )

    # Voice & Personality
    voice_gender: str = Field(default="female", alias="VOICE_GENDER")  # 'male' or 'female'
    emotion_level: str = Field(default="medium", alias="EMOTION_LEVEL") # 'low', 'medium', 'high'

    class Config:
        env_file = ".env"  # Optional .env file for local development
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
