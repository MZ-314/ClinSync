"""
Consultation Service — business logic layer between API and agents.
Handles consultation creation and orchestrates the pipeline.

Phase 8 note:
  Audio bytes are now saved to disk at upload time and the path stored in
  consultation.audio_file_path. This allows the Kafka consumer to later
  read the audio back and pass it into the LangGraph workflow without
  needing to re-upload or carry bytes through Kafka messages.
"""

import uuid
import os
import structlog
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.consultation import Consultation, ConsultationStatus
from app.agents.transcription.agent import transcription_agent
from app.core.config import settings

logger = structlog.get_logger(__name__)

# Supported audio MIME types
SUPPORTED_AUDIO_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "video/webm",
}

# MIME type → file extension map for saving to disk
MIME_TO_EXT = {
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/webm": "webm",
    "video/webm": "webm",
}

# Directory where audio files are stored
# Falls back to /tmp/clinsync_audio if AUDIO_UPLOAD_DIR is not set
AUDIO_UPLOAD_DIR = Path(getattr(settings, "AUDIO_UPLOAD_DIR", "/tmp/clinsync_audio"))


def _save_audio_to_disk(
    consultation_id: uuid.UUID,
    audio_bytes: bytes,
    mime_type: str,
) -> str:
    """
    Write audio bytes to disk and return the absolute file path.
    Creates the upload directory if it doesn't exist.
    """
    AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    ext = MIME_TO_EXT.get(mime_type, "ogg")
    filename = f"{consultation_id}.{ext}"
    file_path = AUDIO_UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    logger.info(
        "Audio saved to disk",
        consultation_id=str(consultation_id),
        path=str(file_path),
        size_bytes=len(audio_bytes),
    )

    return str(file_path)


class ConsultationService:

    async def create_and_transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        doctor_name: str | None,
        db: AsyncSession,
        emit_kafka: bool = True,
    ) -> Consultation:
        """
        Create a new consultation record, save audio to disk,
        and immediately start transcription.

        Args:
            audio_bytes: Raw audio content from the upload
            mime_type: Audio MIME type
            doctor_name: Name of the doctor (optional)
            db: Database session

        Returns:
            Consultation record (status will be TRANSCRIBED if successful)
        """
        consultation_id = uuid.uuid4()

        # ── Save audio to disk first ──────────────────────────────────────────
        audio_file_path = _save_audio_to_disk(consultation_id, audio_bytes, mime_type)

        # ── Create consultation record with audio path ─────────────────────────
        consultation = Consultation(
            id=consultation_id,
            status=ConsultationStatus.UPLOADED,
            doctor_name=doctor_name,
            audio_file_path=audio_file_path,   # ← stored so consumer can read it back
        )
        db.add(consultation)
        await db.commit()
        await db.refresh(consultation)

        logger.info(
            "Consultation created",
            consultation_id=str(consultation.id),
            doctor=doctor_name,
        )

        # ── Run transcription agent ───────────────────────────────────────────
        consultation = await transcription_agent.run(
            consultation=consultation,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            db=db,
            emit_kafka=emit_kafka,
        )

        return consultation

    async def get_by_id(
        self,
        consultation_id: uuid.UUID,
        db: AsyncSession,
    ) -> Consultation | None:
        """Fetch a consultation by ID."""
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        return result.scalar_one_or_none()


# Singleton
consultation_service = ConsultationService()