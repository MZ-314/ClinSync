from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://clinsync:clinsync_secret@postgres:5432/clinsync_db"

    # LLM (Groq)
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Deepgram
    DEEPGRAM_API_KEY: str = ""

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_TRANSCRIPTION: str = "clinsync.transcription"
    KAFKA_TOPIC_EXTRACTION: str = "clinsync.extraction"
    KAFKA_TOPIC_FHIR: str = "clinsync.fhir"
    KAFKA_TOPIC_APPROVAL: str = "clinsync.approval"

    # FHIR
    HAPI_FHIR_URL: str = "http://hapi-fhir:8080/fhir"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "clinsync"
    # Aliases used by render.yaml
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "clinsync"

    # Security
    JWT_EXPIRE_MINUTES: int = 480


settings = Settings()