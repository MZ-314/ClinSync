"""
Transcription Agent — Step 1 of the ClinSync pipeline.

Responsibilities:
1. Accept audio bytes for a consultation
2. Call Deepgram to transcribe
3. Update consultation status and store transcript in DB
4. Emit Kafka event to trigger the next agent (extraction)

Phase 8 note:
  When called from the LangGraph workflow, emit_kafka=False is passed so the
  agent does NOT emit to clinsync.transcription. LangGraph manages sequencing
  internally. Emitting would cause the consumer to pick up the event and
  trigger a second workflow run, creating an infinite loop.
"""

import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.transcription.deepgram_client import deepgram_client
from app.core.config import settings
from app.kafka.producer import kafka_producer
from app.models.consultation import Consultation, ConsultationStatus

logger = structlog.get_logger(__name__)


class TranscriptionAgent:

    async def run(
        self,
        consultation: Consultation,
        audio_bytes: bytes,
        mime_type: str,
        db: AsyncSession,
        emit_kafka: bool = True,  # Set False when called from LangGraph
    ) -> Consultation:
        """
        Run the transcription pipeline step.

        Args:
            consultation: The Consultation DB record
            audio_bytes: Raw audio content
            mime_type: Audio MIME type
            db: Database session
            emit_kafka: Whether to emit Kafka event after transcription.
                        Pass False when called from LangGraph workflow to
                        prevent the consumer triggering a second run.

        Returns:
            Updated Consultation record
        """
        consultation_id = str(consultation.id)
        logger.info("Transcription agent started", consultation_id=consultation_id)

        # ── Step 1: Mark as transcribing ──────────────────────────────────────
        consultation.status = ConsultationStatus.TRANSCRIBING
        await db.commit()

        # ── Step 2: Transcribe with Deepgram ──────────────────────────────────
        try:
            result = await deepgram_client.transcribe_file(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                detect_language=True,
            )
        except Exception as e:
            logger.error(
                "Transcription failed",
                consultation_id=consultation_id,
                error=str(e),
            )
            consultation.status = ConsultationStatus.FAILED
            consultation.error_message = f"Transcription error: {str(e)}"
            await db.commit()
            raise

        # ── Step 3: Persist transcript ─────────────────────────────────────────
        consultation.transcript = result.transcript
        consultation.transcript_language = result.language
        consultation.audio_duration_seconds = result.duration_seconds
        consultation.status = ConsultationStatus.TRANSCRIBED
        consultation.error_message = None
        await db.commit()

        logger.info(
            "Transcript saved",
            consultation_id=consultation_id,
            language=result.language,
            duration=result.duration_seconds,
            word_count=len(result.words),
        )

        # ── Step 4: Optionally emit Kafka event ────────────────────────────────
        # Skipped when called from LangGraph to prevent infinite loop.
        if emit_kafka:
            await self._emit_extraction_event(consultation_id, result.transcript)

        return consultation

    async def _emit_extraction_event(
        self, consultation_id: str, transcript: str
    ) -> None:
        """Publish event to Kafka so the extraction agent picks it up."""
        payload = {
            "event": "transcription.completed",
            "consultation_id": consultation_id,
            "transcript": transcript,
        }
        try:
            await kafka_producer.send(
                topic=settings.KAFKA_TOPIC_TRANSCRIPTION,
                payload=payload,
            )
            logger.info(
                "Kafka event emitted",
                topic=settings.KAFKA_TOPIC_TRANSCRIPTION,
                consultation_id=consultation_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to emit Kafka event",
                consultation_id=consultation_id,
                error=str(e),
            )


# Singleton
transcription_agent = TranscriptionAgent()