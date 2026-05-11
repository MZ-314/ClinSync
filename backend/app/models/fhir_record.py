"""
FHIRRecord model — stores individual FHIR resources generated per consultation.
One consultation can produce multiple FHIR resources (Patient, Encounter,
Condition, MedicationRequest, etc.)
"""

import uuid
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class FHIRResourceType(str, Enum):
    PATIENT             = "Patient"
    ENCOUNTER           = "Encounter"
    CONDITION           = "Condition"
    MEDICATION_REQUEST  = "MedicationRequest"
    OBSERVATION         = "Observation"
    DIAGNOSTIC_REPORT   = "DiagnosticReport"
    PROCEDURE           = "Procedure"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"


class FHIRRecord(Base, TimestampMixin):
    __tablename__ = "fhir_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultations.id"),
        nullable=False,
    )

    # Which FHIR resource type this record represents
    resource_type: Mapped[FHIRResourceType] = mapped_column(
        SAEnum(FHIRResourceType),
        nullable=False,
    )

    # The full FHIR resource as JSON string
    resource_json: Mapped[str] = mapped_column(Text, nullable=False)

    # FHIR server ID after successful submission
    fhir_server_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Whether this resource was submitted to the HAPI FHIR server
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Validation status
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_errors: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    consultation: Mapped["Consultation"] = relationship(
        "Consultation", back_populates="fhir_records"
    )

    def __repr__(self) -> str:
        return f"<FHIRRecord id={self.id} type={self.resource_type} submitted={self.is_submitted}>"