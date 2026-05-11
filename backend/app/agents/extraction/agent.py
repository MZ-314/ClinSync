"""
Clinical Extraction Agent — Step 2 of the ClinSync pipeline.

Responsibilities:
1. Receive transcript from Kafka (clinsync.transcription topic)
2. Call Groq LLaMA to extract structured clinical entities
3. Validate output against Pydantic schema
4. Store extracted entities in DB
5. Emit Kafka event to trigger the coding agent
"""

import json
import structlog
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.extraction.schemas import ClinicalEntities
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.kafka.producer import kafka_producer
from app.models.consultation import Consultation, ConsultationStatus
from app.prompts.extraction_prompt import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
)

logger = structlog.get_logger(__name__)


class ExtractionAgent:

    def __init__(self):
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def run_from_kafka(self, consultation_id: str, transcript: str) -> None:
        """
        Entry point called by the Kafka consumer.
        Opens its own DB session since it runs outside the request lifecycle.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(
                    Consultation.id == consultation_id
                )
            )
            consultation = result.scalar_one_or_none()

            if not consultation:
                logger.error(
                    "Consultation not found for extraction",
                    consultation_id=consultation_id,
                )
                return

            await self.run(consultation, transcript, db)

    async def run(
        self,
        consultation: Consultation,
        transcript: str,
        db: AsyncSession,
        emit_kafka: bool = True,  # ← added: False when called from LangGraph
    ) -> Consultation:
        """
        Run the extraction pipeline step.
        """
        consultation_id = str(consultation.id)
        logger.info("Extraction agent started", consultation_id=consultation_id)

        # ── Step 1: Mark as extracting ────────────────────────────────────────
        consultation.status = ConsultationStatus.EXTRACTING
        await db.commit()

        # ── Step 2: Call Groq LLM ─────────────────────────────────────────────
        try:
            entities = await self._extract_entities(transcript)
        except Exception as e:
            logger.error(
                "Extraction failed",
                consultation_id=consultation_id,
                error=str(e),
            )
            consultation.status = ConsultationStatus.FAILED
            consultation.error_message = f"Extraction error: {str(e)}"
            await db.commit()
            raise

        # ── Step 3: Persist extracted entities ────────────────────────────────
        consultation.extracted_entities = entities.model_dump_json()
        consultation.status = ConsultationStatus.EXTRACTED
        consultation.error_message = None
        await db.commit()

        logger.info(
            "Entities extracted and saved",
            consultation_id=consultation_id,
            diagnosis=entities.diagnosis,
            medications=[m.name for m in entities.medications],
            symptoms=entities.symptoms,
        )

        # ── Step 4: Emit Kafka event (skipped when called from LangGraph) ─────
        if emit_kafka:
            await self._emit_coding_event(consultation_id, entities)

        return consultation

    async def _extract_entities(self, transcript: str) -> ClinicalEntities:
        """Call Groq LLaMA to extract clinical entities from transcript."""
        response = await self._client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": build_extraction_prompt(transcript)},
            ],
            temperature=0.1,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw_json = response.choices[0].message.content
        logger.debug("LLM raw response", raw=raw_json)

        data = json.loads(raw_json)
        return ClinicalEntities(**data)

    async def _emit_coding_event(
        self, consultation_id: str, entities: ClinicalEntities
    ) -> None:
        """Publish event to Kafka so the coding agent picks it up."""
        payload = {
            "event": "extraction.completed",
            "consultation_id": consultation_id,
            "entities": entities.model_dump(),
        }
        try:
            await kafka_producer.send(
                topic=settings.KAFKA_TOPIC_EXTRACTION,
                payload=payload,
            )
            logger.info(
                "Kafka event emitted",
                topic=settings.KAFKA_TOPIC_EXTRACTION,
                consultation_id=consultation_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to emit Kafka event",
                consultation_id=consultation_id,
                error=str(e),
            )


# Singleton
extraction_agent = ExtractionAgent()