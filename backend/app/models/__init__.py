"""
Import all models here so Alembic can detect them automatically.
"""

from app.models.base import Base, TimestampMixin
from app.models.patient import Patient
from app.models.consultation import Consultation, ConsultationStatus
from app.models.fhir_record import FHIRRecord, FHIRResourceType
from app.models.approval_log import ApprovalLog, ApprovalAction
from app.models.user import User  # noqa

__all__ = [
    "Base",
    "TimestampMixin",
    "Patient",
    "Consultation",
    "ConsultationStatus",
    "FHIRRecord",
    "FHIRResourceType",
    "ApprovalLog",
    "ApprovalAction",
]