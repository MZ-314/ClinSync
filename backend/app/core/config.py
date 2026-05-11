from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # JWT
    JWT_EXPIRE_MINUTES: int = 60 * 8  # 8 hours — sensible for a clinical shift

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://clinsync:clinsync_secret@postgres:5432/clinsync_db"

    # LLM (Groq)
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Deepgram
    DEEPGRAM_API_KEY: str = ""

    # Kafka
    # Set USE_KAFKA=false on Render (no broker available) — pipeline will run
    # in-process via FastAPI BackgroundTasks instead. Local docker-compose keeps
    # Kafka enabled by default.
    USE_KAFKA: bool = True
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_TRANSCRIPTION: str = "clinsync.transcription"
    KAFKA_TOPIC_EXTRACTION: str = "clinsync.extraction"
    KAFKA_TOPIC_FHIR: str = "clinsync.fhir"
    KAFKA_TOPIC_APPROVAL: str = "clinsync.approval"

    # FHIR
    HAPI_FHIR_URL: str = "http://hapi-fhir:8080/fhir"

    # Audio storage
    # On Render the filesystem is ephemeral; for production use object storage.
    AUDIO_UPLOAD_DIR: str = "/tmp/clinsync_audio"

    # CORS — override in .env for Render deployment
    # e.g. CORS_ORIGINS=["https://your-app.onrender.com"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # LangSmith (observability)
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "clinsync"

settings = Settings()