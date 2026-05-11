"""
Pydantic schemas for medical coding output.
"""

from pydantic import BaseModel, Field


class CodedDiagnosis(BaseModel):
    term: str
    icd11_code: str | None = None
    icd11_description: str | None = None
    snomed_code: str | None = None
    snomed_description: str | None = None


class CodedSymptom(BaseModel):
    term: str
    snomed_code: str | None = None
    snomed_description: str | None = None


class CodedMedication(BaseModel):
    name: str
    rxnorm_code: str | None = None
    rxnorm_description: str | None = None
    generic_name: str | None = None


class CodingResult(BaseModel):
    """Complete coding result for a consultation."""
    diagnoses: list[CodedDiagnosis] = Field(default_factory=list)
    symptoms: list[CodedSymptom] = Field(default_factory=list)
    medications: list[CodedMedication] = Field(default_factory=list)