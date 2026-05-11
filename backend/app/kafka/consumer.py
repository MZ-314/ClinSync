"""
Kafka consumer — listens to pipeline topics and routes events to agents.

Phase 8 change:
  handle_transcription_event now invokes the LangGraph workflow instead of
  calling extraction_agent directly. The graph manages the full
  transcription → extraction → coding → FHIR sequence internally.

  clinsync.extraction and clinsync.fhir are still emitted by agents for
  observability, but are no longer consumed here — LangGraph handles sequencing.

Topic routing (post Phase 8):
  clinsync.transcription  → run_consultation_workflow()  (LangGraph)
  clinsync.approval       → handle_approval_event()      (Phase 9 stub)
"""

import asyncio
import json
import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.consultation import Consultation
from app.agents.workflow.graph import run_consultation_workflow

logger = structlog.get_logger(__name__)
CONSUMER_GROUP = "clinsync-backend"


async def handle_transcription_event(payload: dict) -> None:
    """
    Triggered by transcription.completed on clinsync.transcription.

    Reads the audio file from disk (path stored in DB at upload time),
    then invokes the full LangGraph pipeline which runs:
      transcribe → extract → code → build_fhir → pending_review
    """
    consultation_id = payload.get("consultation_id")
    if not consultation_id:
        logger.warning("Invalid transcription event — missing consultation_id")
        return

    # ── Fetch audio file path from DB ──────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            logger.error("Consultation not found", consultation_id=consultation_id)
            return

        audio_file_path = consultation.audio_file_path
        if not audio_file_path:
            logger.error(
                "No audio file path on consultation",
                consultation_id=consultation_id,
            )
            return

    # ── Read audio bytes from disk ─────────────────────────────────────────────
    try:
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
    except FileNotFoundError:
        logger.error(
            "Audio file not found on disk",
            consultation_id=consultation_id,
            path=audio_file_path,
        )
        return

    # ── Infer MIME type from extension ─────────────────────────────────────────
    ext = audio_file_path.rsplit(".", 1)[-1].lower()
    mime_map = {
        "ogg": "audio/ogg",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "webm": "audio/webm",
        "flac": "audio/flac",
    }
    mime_type = mime_map.get(ext, "audio/ogg")

    logger.info(
        "Invoking LangGraph workflow",
        consultation_id=consultation_id,
        mime_type=mime_type,
        audio_bytes=len(audio_bytes),
    )

    # ── Hand off to LangGraph ──────────────────────────────────────────────────
    await run_consultation_workflow(
        consultation_id=consultation_id,
        audio_bytes=audio_bytes,
        mime_type=mime_type,
    )


async def handle_approval_event(payload: dict) -> None:
    """Phase 9 stub — doctor approve/reject HITL flow."""
    consultation_id = payload.get("consultation_id")
    action = payload.get("action")
    logger.info(
        "Approval event received — submission coming in Phase 9",
        consultation_id=consultation_id,
        action=action,
    )
    # TODO Phase 9: call approval_service.process(consultation_id, action)


# ── Topic → handler mapping ────────────────────────────────────────────────────
# extraction and fhir topics dropped — LangGraph handles sequencing internally.
TOPIC_HANDLERS = {
    settings.KAFKA_TOPIC_TRANSCRIPTION: handle_transcription_event,
    settings.KAFKA_TOPIC_APPROVAL: handle_approval_event,
}


async def start_consumer() -> None:
    topics = list(TOPIC_HANDLERS.keys())
    logger.info("Starting Kafka consumer", topics=topics, group=CONSUMER_GROUP)

    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    logger.info("Kafka consumer started")

    try:
        async for msg in consumer:
            topic = msg.topic
            payload = msg.value
            kafka_event = payload.get("event", "unknown")

            logger.info(
                "Kafka message received",
                topic=topic,
                kafka_event=kafka_event,
                partition=msg.partition,
                offset=msg.offset,
            )

            handler = TOPIC_HANDLERS.get(topic)
            if handler:
                try:
                    await handler(payload)
                except Exception as e:
                    logger.error(
                        "Event handler failed",
                        topic=topic,
                        kafka_event=kafka_event,
                        error=str(e),
                    )
            else:
                logger.warning("No handler for topic", topic=topic)

    except asyncio.CancelledError:
        logger.info("Kafka consumer cancelled — shutting down")
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")