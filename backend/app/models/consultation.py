"""
Consultation model — the central record for each doctor-patient session.
Tracks the full pipeline: audio → transcript → extraction → FHIR → approval.
"""

import uuid
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class ConsultationStatus(str, Enum):
    UPLOADED       = "uploaded"        # Audio received
    TRANSCRIBING   = "transcribing"    # Deepgram processing
    TRANSCRIBED    = "transcribed"     # Transcript ready
    EXTRACTING     = "extracting"      # LLM extraction in progress
    EXTRACTED      = "extracted"       # Clinical entities extracted
    CODING         = "coding"          # ICD-11/SNOMED mapping
    CODED          = "coded"           # Codes assigned
    BUILDING_FHIR  = "building_fhir"   # FHIR resources being built
    PENDING_REVIEW = "pending_review"  # Awaiting doctor approval (HITL)
    APPROVED       = "approved"        # Doctor approved
    REJECTED       = "rejected"        # Doctor rejected
    SUBMITTED      = "submitted"       # Pushed to HAPI FHIR server
    FAILED         = "failed"          # Pipeline error


class Consultation(Base, TimestampMixin):
    __tablename__ = "consultations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Link to patient (nullable until patient is identified)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=True,
    )

    # Pipeline state
    status: Mapped[ConsultationStatus] = mapped_column(
        SAEnum(ConsultationStatus),
        default=ConsultationStatus.UPLOADED,
        nullable=False,
    )

    # Audio
    audio_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    # Transcription output
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Extracted clinical data (JSON stored as text)
    extracted_entities: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Coded data (ICD-11/SNOMED — JSON stored as text)
    coded_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Doctor who conducted the consultation
    doctor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    patient: Mapped["Patient | None"] = relationship("Patient", back_populates="consultations")
    fhir_records: Mapped[list["FHIRRecord"]] = relationship(
        "FHIRRecord", back_populates="consultation"
    )
    approval_logs: Mapped[list["ApprovalLog"]] = relationship(
        "ApprovalLog", back_populates="consultation"
    )

    def __repr__(self) -> str:
        return f"<Consultation id={self.id} status={self.status}>"