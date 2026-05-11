"""
ClinSync LangGraph nodes.

Each function is one node in the StateGraph. Nodes:
  - Receive the full ClinSyncState
  - Call the relevant existing agent (no logic duplicated here)
  - Return a partial state dict with only the fields they update

Error handling: every node catches exceptions, sets state["error"],
and returns immediately. The router after each node checks for errors
and redirects to handle_error_node.
"""

import json
import structlog
from sqlalchemy import select

from app.agents.transcription.agent import transcription_agent
from app.agents.extraction.agent import extraction_agent
from app.agents.coding.agent import coding_agent
from app.agents.fhir_builder.agent import fhir_builder_agent
from app.agents.workflow.state import ClinSyncState
from app.core.database import AsyncSessionLocal
from app.models.consultation import Consultation, ConsultationStatus

logger = structlog.get_logger(__name__)


# ── Node 1: Transcribe ─────────────────────────────────────────────────────────

async def transcribe_node(state: ClinSyncState) -> dict:
    """
    Calls TranscriptionAgent with raw audio bytes.
    emit_kafka=False prevents the agent from publishing to clinsync.transcription,
    which would cause the consumer to trigger a second workflow run.
    """
    consultation_id = state["consultation_id"]
    logger.info("Node: transcribe", consultation_id=consultation_id)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()
            if not consultation:
                raise ValueError(f"Consultation {consultation_id} not found")

            updated = await transcription_agent.run(
                consultation=consultation,
                audio_bytes=state["audio_bytes"],
                mime_type=state["mime_type"],
                db=db,
                emit_kafka=False,       # ← prevents infinite loop
            )

            return {
                "transcript": updated.transcript,
                "language": updated.transcript_language,
                "duration_seconds": updated.audio_duration_seconds,
                "status": ConsultationStatus.TRANSCRIBED.value,
                "error": None,
            }

    except Exception as e:
        logger.error("Node transcribe failed", consultation_id=consultation_id, error=str(e))
        return {"error": str(e), "status": ConsultationStatus.FAILED.value}


# ── Node 2: Extract ────────────────────────────────────────────────────────────

async def extract_node(state: ClinSyncState) -> dict:
    """
    Calls ExtractionAgent with the transcript.
    emit_kafka=False prevents triggering the coding agent via Kafka —
    the graph handles sequencing directly.
    """
    consultation_id = state["consultation_id"]
    logger.info("Node: extract", consultation_id=consultation_id)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()

            updated = await extraction_agent.run(
                consultation=consultation,
                transcript=state["transcript"],
                db=db,
                emit_kafka=False,       # ← prevents double coding trigger
            )

            extracted = json.loads(updated.extracted_entities or "{}")
            return {
                "extracted_entities": extracted,
                "status": ConsultationStatus.EXTRACTED.value,
                "error": None,
            }

    except Exception as e:
        logger.error("Node extract failed", consultation_id=consultation_id, error=str(e))
        return {"error": str(e), "status": ConsultationStatus.FAILED.value}


# ── Node 3: Code ───────────────────────────────────────────────────────────────

async def code_node(state: ClinSyncState) -> dict:
    """
    Calls CodingAgent with extracted entities.
    emit_kafka=False prevents triggering the FHIR builder via Kafka —
    the graph calls build_fhir_node directly.
    """
    consultation_id = state["consultation_id"]
    logger.info("Node: code", consultation_id=consultation_id)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()

            updated = await coding_agent.run(
                consultation=consultation,
                entities=state["extracted_entities"],  # ← fix: was 'extracted'
                db=db,
                emit_kafka=False,                      # ← prevents double FHIR build
            )

            coded = json.loads(updated.coded_data or "{}")
            return {
                "coding": coded,
                "status": ConsultationStatus.CODED.value,
                "error": None,
            }

    except Exception as e:
        logger.error("Node code failed", consultation_id=consultation_id, error=str(e))
        return {"error": str(e), "status": ConsultationStatus.FAILED.value}


# ── Node 4: Build FHIR ─────────────────────────────────────────────────────────

async def build_fhir_node(state: ClinSyncState) -> dict:
    """
    Calls FHIRBuilderAgent with coded entities.
    Builds and submits a FHIR R4 transaction bundle to HAPI FHIR.
    """
    consultation_id = state["consultation_id"]
    logger.info("Node: build_fhir", consultation_id=consultation_id)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()

            await fhir_builder_agent.run(
                consultation=consultation,
                coding=state["coding"],
                db=db,
            )

            return {
                "status": ConsultationStatus.PENDING_REVIEW.value,
                "error": None,
            }

    except Exception as e:
        logger.error("Node build_fhir failed", consultation_id=consultation_id, error=str(e))
        return {"error": str(e), "status": ConsultationStatus.FAILED.value}


# ── Node 5: Pending Review ─────────────────────────────────────────────────────

async def pending_review_node(state: ClinSyncState) -> dict:
    """
    Terminal success node. Consultation sits here until a doctor
    approves or rejects it via the HITL API (Phase 9).

    Also used when extraction finds no diagnosis — flagged for
    manual review rather than going through coding.
    """
    consultation_id = state["consultation_id"]
    no_diagnosis = not (state.get("extracted_entities") or {}).get("diagnosis")

    logger.info(
        "Node: pending_review",
        consultation_id=consultation_id,
        flagged_no_diagnosis=no_diagnosis,
    )

    if no_diagnosis:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()
            if consultation:
                consultation.status = ConsultationStatus.PENDING_REVIEW
                consultation.error_message = "No diagnosis extracted — flagged for manual review"
                await db.commit()

    return {
        "status": ConsultationStatus.PENDING_REVIEW.value,
        "error": None,
    }


# ── Node 6: Handle Error ───────────────────────────────────────────────────────

async def handle_error_node(state: ClinSyncState) -> dict:
    """
    Terminal failure node. Persists FAILED status and error message to DB.
    Called whenever any node sets state["error"].
    """
    consultation_id = state["consultation_id"]
    error = state.get("error", "Unknown error")
    logger.error("Node: handle_error", consultation_id=consultation_id, error=error)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if consultation:
            consultation.status = ConsultationStatus.FAILED
            consultation.error_message = error
            await db.commit()

    return {"status": ConsultationStatus.FAILED.value}


# ── Conditional edge routers ───────────────────────────────────────────────────

def route_after_transcribe(state: ClinSyncState) -> str:
    if state.get("error"):
        return "handle_error"
    return "extract"


def route_after_extract(state: ClinSyncState) -> str:
    if state.get("error"):
        return "handle_error"

    extracted = state.get("extracted_entities") or {}
    diagnoses = extracted.get("diagnosis") or []
    if not diagnoses:
        logger.warning(
            "No diagnosis extracted — routing to manual review",
            consultation_id=state["consultation_id"],
        )
        return "pending_review"

    return "code"


def route_after_code(state: ClinSyncState) -> str:
    if state.get("error"):
        return "handle_error"
    return "build_fhir"


def route_after_fhir(state: ClinSyncState) -> str:
    if state.get("error"):
        return "handle_error"
    return "pending_review"