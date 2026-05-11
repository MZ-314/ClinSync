"""
Pydantic schemas for structured clinical entity extraction output.
These define exactly what the LLM must return.
"""

from pydantic import BaseModel, Field


class Medication(BaseModel):
    name: str = Field(description="Drug name e.g. Paracetamol")
    dosage: str | None = Field(default=None, description="e.g. 500mg")
    frequency: str | None = Field(default=None, description="e.g. twice daily")
    duration: str | None = Field(default=None, description="e.g. 5 days")
    route: str | None = Field(default=None, description="e.g. oral, IV")


class Vital(BaseModel):
    name: str = Field(description="e.g. Blood Pressure, Temperature")
    value: str = Field(description="e.g. 140/90, 38.5")
    unit: str | None = Field(default=None, description="e.g. mmHg, °C")


class ClinicalEntities(BaseModel):
    """
    Structured clinical data extracted from a doctor-patient consultation transcript.
    """

    # Patient demographics (if mentioned in transcript)
    patient_age: int | None = Field(default=None, description="Patient age in years")
    patient_gender: str | None = Field(default=None, description="male / female / other")

    # Chief complaint — why the patient came in
    chief_complaint: str | None = Field(
        default=None,
        description="Primary reason for the consultation in one sentence"
    )

    # Symptoms reported
    symptoms: list[str] = Field(
        default_factory=list,
        description="List of symptoms mentioned e.g. ['fever', 'headache', 'body ache']"
    )

    # Duration of illness
    duration_of_illness: str | None = Field(
        default=None,
        description="How long the patient has had symptoms e.g. '3 days'"
    )

    # Vitals recorded during consultation
    vitals: list[Vital] = Field(
        default_factory=list,
        description="Vital signs recorded e.g. blood pressure, temperature, SpO2"
    )

    # Diagnosis
    diagnosis: list[str] = Field(
        default_factory=list,
        description="Diagnoses made e.g. ['viral fever', 'hypertension']"
    )

    # Medications prescribed
    medications: list[Medication] = Field(
        default_factory=list,
        description="Medications prescribed with dosage and frequency"
    )

    # Lab tests ordered
    lab_tests: list[str] = Field(
        default_factory=list,
        description="Lab tests ordered e.g. ['CBC', 'blood glucose']"
    )

    # Follow-up instructions
    follow_up: str | None = Field(
        default=None,
        description="Follow-up instructions e.g. 'Review in 5 days'"
    )

    # Additional clinical notes
    notes: str | None = Field(
        default=None,
        description="Any other clinically relevant information"
    )