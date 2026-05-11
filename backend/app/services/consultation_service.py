"""
Consultation Service — business logic layer between API and agents.
When USE_KAFKA=false (production on Render), runs the pipeline in-process.
When USE_KAFKA=true (local Docker), emits events and lets consumers handle it.
"""

import os
import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.consultation import Consultation, ConsultationStatus
from app.agents.transcription.agent import transcription_agent

logger = structlog.get_logger(__name__)

USE_KAFKA = os.getenv("USE_KAFKA", "true").lower() == "true"

SUPPORTED_AUDIO_TYPES = {
    "audio/wav", "audio/wave", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/ogg", "audio/flac",
    "audio/webm", "video/webm",
}


class ConsultationService:

    async def create_and_transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        doctor_name: str | None,
        db: AsyncSession,
    ) -> Consultation:
        """
        Create consultation and run the pipeline.
        - USE_KAFKA=true: transcribe only, rest handled by Kafka consumers
        - USE_KAFKA=false: run full pipeline in-process (transcribe → extract → code → FHIR)
        """
        consultation = Consultation(
            id=uuid.uuid4(),
            status=ConsultationStatus.UPLOADED,
            doctor_name=doctor_name,
        )
        db.add(consultation)
        await db.commit()
        await db.refresh(consultation)

        logger.info(
            "Consultation created",
            consultation_id=str(consultation.id),
            doctor=doctor_name,
            kafka=USE_KAFKA,
        )

        # Step 1: Transcription (always runs synchronously)
        consultation = await transcription_agent.run(
            consultation=consultation,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            db=db,
        )

        # If Kafka is disabled, run the rest of the pipeline in-process
        if not USE_KAFKA and consultation.transcript:
            await self._run_pipeline_direct(consultation, db)

        return consultation

    async def _run_pipeline_direct(
        self, consultation: Consultation, db: AsyncSession
    ) -> None:
        """Run extraction → coding → FHIR in-process (no Kafka)."""
        import json
        from app.agents.extraction.agent import extraction_agent
        from app.agents.coding.agent import coding_agent
        from app.agents.fhir_builder.agent import fhir_builder_agent

        # Extraction
        consultation = await extraction_agent.run(
            consultation, consultation.transcript, db
        )

        if not consultation.extracted_entities:
            return

        entities = json.loads(consultation.extracted_entities)

        # Coding
        consultation = await coding_agent.run(consultation, entities, db)

        if not consultation.coded_data:
            return

        coding = json.loads(consultation.coded_data)

        # FHIR Builder
        await fhir_builder_agent.run(consultation, coding, db)

    async def get_by_id(
        self, consultation_id: uuid.UUID, db: AsyncSession
    ) -> Consultation | None:
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        return result.scalar_one_or_none()


consultation_service = ConsultationService()