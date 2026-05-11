"""
Patient model — stores basic patient demographics.
Linked to consultations and FHIR records.
"""

import uuid
from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[Date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # FHIR Patient resource ID (set after FHIR submission)
    fhir_patient_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    consultations: Mapped[list["Consultation"]] = relationship(
        "Consultation", back_populates="patient"
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} name={self.name}>"