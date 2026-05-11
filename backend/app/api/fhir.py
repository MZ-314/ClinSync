"""FHIR resource endpoints – stub for now, filled in the FHIR builder step."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/patient/{patient_id}")
async def get_patient(patient_id: str):
    # TODO: proxy to HAPI FHIR server
    return {"patient_id": patient_id, "status": "not_implemented"}