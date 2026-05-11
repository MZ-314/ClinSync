"""
ApprovalLog model — full audit trail of every HITL decision.
Every approve/reject action by a doctor is recorded here.
"""

import uuid
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class ApprovalAction(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class ApprovalLog(Base, TimestampMixin):
    __tablename__ = "approval_logs"

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

    # Who made the decision
    reviewer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # What they decided
    action: Mapped[ApprovalAction] = mapped_column(
        SAEnum(ApprovalAction),
        nullable=False,
    )

    # Optional notes from the doctor
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Which version of the FHIR record was reviewed
    fhir_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    consultation: Mapped["Consultation"] = relationship(
        "Consultation", back_populates="approval_logs"
    )

    def __repr__(self) -> str:
        return f"<ApprovalLog id={self.id} action={self.action} reviewer={self.reviewer_id}>"