"""
Consultations API
Handles audio upload and triggers the multi-agent pipeline.
"""

import json
import uuid
import structlog
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow.graph import run_post_transcription_workflow
from app.core.config import settings
from app.core.database import get_db
from app.models.consultation import Consultation, ConsultationStatus
from app.models.fhir_record import FHIRRecord
from app.services.consultation_service import consultation_service, SUPPORTED_AUDIO_TYPES

logger = structlog.get_logger(__name__)
router = APIRouter()


class ConsultationResponse(BaseModel):
    consultation_id: str
    status: str
    message: str
    transcript: str | None = None
    language: str | None = None
    duration_seconds: float | None = None


class ConsultationListItem(BaseModel):
    consultation_id: str
    status: str
    doctor_name: str | None = None
    transcript_preview: str | None = None
    language: str | None = None
    duration_seconds: float | None = None
    created_at: str
    updated_at: str


class ConsultationDetail(BaseModel):
    consultation_id: str
    status: str
    doctor_name: str | None = None
    transcript: str | None = None
    language: str | None = None
    duration_seconds: float | None = None
    extracted_entities: dict | None = None
    coded_data: dict | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class FHIRRecordItem(BaseModel):
    id: str
    resource_type: str
    resource_json: dict
    fhir_server_id: str | None = None
    is_submitted: bool
    is_valid: bool
    validation_errors: str | None = None


def _parse_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


@router.post("/", response_model=ConsultationResponse)
async def create_consultation(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    doctor_name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an audio file to start the clinical documentation pipeline.

    - Accepts: wav, mp3, m4a, ogg, flac, webm
    - Transcribes using Deepgram (multilingual)
    - Triggers extraction agent via Kafka
    """
    # Validate file type
    mime_type = audio.content_type or "audio/wav"
    if mime_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {mime_type}. "
                   f"Supported: {', '.join(SUPPORTED_AUDIO_TYPES)}",
        )

    # Read audio bytes
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    logger.info(
        "Audio upload received",
        filename=audio.filename,
        mime_type=mime_type,
        size_bytes=len(audio_bytes),
    )

    # Run transcription synchronously so the response carries the transcript.
    # When USE_KAFKA=False (e.g. on Render), the rest of the pipeline runs
    # in-process via BackgroundTasks instead of through a Kafka consumer.
    try:
        consultation = await consultation_service.create_and_transcribe(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            doctor_name=doctor_name,
            db=db,
            emit_kafka=settings.USE_KAFKA,
        )
    except Exception as e:
        logger.error("Pipeline failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    if not settings.USE_KAFKA and consultation.transcript:
        background_tasks.add_task(
            run_post_transcription_workflow,
            consultation_id=str(consultation.id),
            transcript=consultation.transcript,
            language=consultation.transcript_language,
            duration_seconds=consultation.audio_duration_seconds,
        )
        logger.info(
            "Post-transcription workflow scheduled in-process",
            consultation_id=str(consultation.id),
        )

    return ConsultationResponse(
        consultation_id=str(consultation.id),
        status=consultation.status.value,
        message="Transcription complete. Extraction pipeline triggered.",
        transcript=consultation.transcript,
        language=consultation.transcript_language,
        duration_seconds=consultation.audio_duration_seconds,
    )


@router.get("/", response_model=list[ConsultationListItem])
async def list_consultations(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List consultations, newest first.
    Used by the dashboard to render the recent consultations panel.
    """
    if limit > 200:
        limit = 200

    result = await db.execute(
        select(Consultation)
        .order_by(Consultation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    consultations = result.scalars().all()

    items: list[ConsultationListItem] = []
    for c in consultations:
        preview = (c.transcript or "")[:200] if c.transcript else None
        items.append(
            ConsultationListItem(
                consultation_id=str(c.id),
                status=c.status.value,
                doctor_name=c.doctor_name,
                transcript_preview=preview,
                language=c.transcript_language,
                duration_seconds=c.audio_duration_seconds,
                created_at=c.created_at.isoformat() if c.created_at else "",
                updated_at=c.updated_at.isoformat() if c.updated_at else "",
            )
        )
    return items


@router.get("/{consultation_id}", response_model=ConsultationDetail)
async def get_consultation(
    consultation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the full state of a consultation, including extracted entities
    and coded data parsed back into JSON for the frontend.
    """
    try:
        cid = uuid.UUID(consultation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid consultation ID format.")

    consultation = await consultation_service.get_by_id(cid, db)

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found.")

    return ConsultationDetail(
        consultation_id=str(consultation.id),
        status=consultation.status.value,
        doctor_name=consultation.doctor_name,
        transcript=consultation.transcript,
        language=consultation.transcript_language,
        duration_seconds=consultation.audio_duration_seconds,
        extracted_entities=_parse_json(consultation.extracted_entities),
        coded_data=_parse_json(consultation.coded_data),
        error_message=consultation.error_message,
        created_at=consultation.created_at.isoformat() if consultation.created_at else "",
        updated_at=consultation.updated_at.isoformat() if consultation.updated_at else "",
    )


@router.get("/{consultation_id}/fhir-records", response_model=list[FHIRRecordItem])
async def list_fhir_records(
    consultation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all FHIR resources generated for a consultation."""
    try:
        cid = uuid.UUID(consultation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid consultation ID format.")

    result = await db.execute(
        select(FHIRRecord)
        .where(FHIRRecord.consultation_id == cid)
        .order_by(FHIRRecord.created_at.asc())
    )
    records = result.scalars().all()

    items: list[FHIRRecordItem] = []
    for r in records:
        items.append(
            FHIRRecordItem(
                id=str(r.id),
                resource_type=r.resource_type.value,
                resource_json=_parse_json(r.resource_json) or {},
                fhir_server_id=r.fhir_server_id,
                is_submitted=r.is_submitted,
                is_valid=r.is_valid,
                validation_errors=r.validation_errors,
            )
        )
    return items