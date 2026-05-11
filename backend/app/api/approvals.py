"""
Approvals API – Human-in-the-Loop (HITL) review endpoints.
Doctor approves or rejects AI-generated FHIR records before submission.
"""

import uuid
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.consultation import Consultation, ConsultationStatus
from app.models.approval_log import ApprovalLog, ApprovalAction
from app.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────────────────

class ApprovalDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"


class ApprovalRequest(BaseModel):
    decision: ApprovalDecision
    reviewer_id: str = "anonymous"
    reviewer_name: str | None = None
    notes: str = ""


class ApprovalResponse(BaseModel):
    consultation_id: str
    decision: ApprovalDecision
    status: str
    message: str


class ConsultationStatusResponse(BaseModel):
    consultation_id: str
    status: str
    transcript: str | None
    extracted_entities: str | None
    coded_data: str | None
    error_message: str | None


# ── Dependency ─────────────────────────────────────────────────────────────────

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/{consultation_id}", response_model=ApprovalResponse)
async def submit_approval(
    consultation_id: str,
    payload: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Doctor submits approval or rejection for a consultation.

    - APPROVED → status moves to APPROVED
    - REJECTED → status moves to REJECTED, no further pipeline action
    - Kafka event only emitted when USE_KAFKA=true (not on Render)
    """
    # ── Fetch consultation ─────────────────────────────────────────────────────
    try:
        cid = uuid.UUID(consultation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid consultation ID format.")

    result = await db.execute(
        select(Consultation).where(Consultation.id == cid)
    )
    consultation = result.scalar_one_or_none()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if consultation.status != ConsultationStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Consultation is not pending review. Current status: {consultation.status.value}",
        )

    # ── Fetch FHIR snapshot for audit log ─────────────────────────────────────
    fhir_snapshot = consultation.coded_data

    # ── Map decision to action and status ─────────────────────────────────────
    if payload.decision == ApprovalDecision.approved:
        action = ApprovalAction.APPROVED
        new_status = ConsultationStatus.APPROVED
        message = "Consultation approved. FHIR records will be submitted."
    else:
        action = ApprovalAction.REJECTED
        new_status = ConsultationStatus.REJECTED
        message = "Consultation rejected. No FHIR submission will occur."

    # ── Write approval log ─────────────────────────────────────────────────────
    approval_log = ApprovalLog(
        consultation_id=consultation.id,
        reviewer_id=payload.reviewer_id,
        reviewer_name=payload.reviewer_name,
        action=action,
        notes=payload.notes or None,
        fhir_snapshot=fhir_snapshot,
    )
    db.add(approval_log)

    # ── Update consultation status ─────────────────────────────────────────────
    consultation.status = new_status
    await db.commit()

    logger.info(
        "Approval submitted",
        consultation_id=consultation_id,
        decision=payload.decision,
        reviewer=payload.reviewer_id,
        new_status=new_status.value,
    )

    # ── Emit Kafka event only when Kafka is enabled (not on Render) ───────────
    if payload.decision == ApprovalDecision.approved and settings.USE_KAFKA:
        await _emit_approval_event(consultation_id, payload)

    return ApprovalResponse(
        consultation_id=consultation_id,
        decision=payload.decision,
        status=new_status.value,
        message=message,
    )


@router.get("/{consultation_id}/status", response_model=ConsultationStatusResponse)
async def get_consultation_status(
    consultation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current status and data for a consultation.
    Useful for the frontend to poll after upload.
    """
    try:
        cid = uuid.UUID(consultation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid consultation ID format.")

    result = await db.execute(
        select(Consultation).where(Consultation.id == cid)
    )
    consultation = result.scalar_one_or_none()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return ConsultationStatusResponse(
        consultation_id=str(consultation.id),
        status=consultation.status.value,
        transcript=consultation.transcript,
        extracted_entities=consultation.extracted_entities,
        coded_data=consultation.coded_data,
        error_message=consultation.error_message,
    )


@router.get("/{consultation_id}/logs")
async def get_approval_logs(
    consultation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all approval/rejection history for a consultation.
    Full audit trail.
    """
    try:
        cid = uuid.UUID(consultation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid consultation ID format.")

    result = await db.execute(
        select(Consultation).where(Consultation.id == cid)
    )
    consultation = result.scalar_one_or_none()

    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    logs_result = await db.execute(
        select(ApprovalLog)
        .where(ApprovalLog.consultation_id == cid)
        .order_by(ApprovalLog.created_at.desc())
    )
    logs = logs_result.scalars().all()

    return {
        "consultation_id": consultation_id,
        "current_status": consultation.status.value,
        "logs": [
            {
                "id": str(log.id),
                "action": log.action.value,
                "reviewer_id": log.reviewer_id,
                "reviewer_name": log.reviewer_name,
                "notes": log.notes,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _emit_approval_event(consultation_id: str, payload: ApprovalRequest) -> None:
    """
    Emit approval event to Kafka.
    Only called when USE_KAFKA=true — import is lazy to avoid
    startup errors on Render where Kafka is not available.
    """
    from app.kafka.producer import kafka_producer  # lazy import — safe on Render

    kafka_payload = {
        "event": "approval.completed",
        "consultation_id": consultation_id,
        "decision": payload.decision.value,
        "reviewer_id": payload.reviewer_id,
        "notes": payload.notes,
    }
    try:
        await kafka_producer.send(
            topic=settings.KAFKA_TOPIC_APPROVAL,
            payload=kafka_payload,
        )
        logger.info(
            "Approval Kafka event emitted",
            consultation_id=consultation_id,
            topic=settings.KAFKA_TOPIC_APPROVAL,
        )
    except Exception as e:
        logger.warning(
            "Failed to emit approval Kafka event",
            consultation_id=consultation_id,
            error=str(e),
        )