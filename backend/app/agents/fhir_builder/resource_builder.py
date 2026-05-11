"""
FHIR R4 resource builders.
Constructs valid FHIR resources from coded clinical entities.
"""

import re
import uuid
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dosage(dosage_str: str) -> tuple[float | None, str | None]:
    """
    Parse a dosage string like '500mg', '500 milligrams', '10 mg' into
    a (numeric_value, ucum_unit) tuple for use in FHIR doseQuantity.
    Returns (None, None) if the string cannot be parsed.
    """
    if not dosage_str:
        return None, None

    # Map common natural-language unit names to UCUM codes
    unit_map = {
        "milligrams": "mg",
        "milligram": "mg",
        "mg": "mg",
        "grams": "g",
        "gram": "g",
        "g": "g",
        "micrograms": "ug",
        "microgram": "ug",
        "mcg": "ug",
        "ug": "ug",
        "milliliters": "mL",
        "milliliter": "mL",
        "ml": "mL",
        "liters": "L",
        "liter": "L",
        "l": "L",
        "units": "U",
        "unit": "U",
        "iu": "[iU]",
        "tablets": "Tab",
        "tablet": "Tab",
        "tab": "Tab",
        "capsules": "Cap",
        "capsule": "Cap",
        "cap": "Cap",
        "drops": "drop",
        "drop": "drop",
        "puffs": "puff",
        "puff": "puff",
    }

    match = re.match(r"([\d.]+)\s*([a-zA-Z]+)?", dosage_str.strip())
    if not match:
        return None, None

    try:
        value = float(match.group(1))
    except ValueError:
        return None, None

    raw_unit = (match.group(2) or "").lower().strip()
    unit = unit_map.get(raw_unit, raw_unit or None)
    return value, unit


def build_patient(
    patient_id: str,
    name: str = "Unknown Patient",
    age: int | None = None,
    gender: str | None = None,
) -> dict:
    """Build a FHIR Patient resource."""
    resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]},
        "text": {
            "status": "generated",
            "div": f'<div xmlns="http://www.w3.org/1999/xhtml">{name}</div>',
        },
        "name": [{"use": "official", "text": name}],
    }

    if gender:
        gender_map = {"male": "male", "female": "female", "other": "other"}
        resource["gender"] = gender_map.get(gender.lower(), "unknown")

    return resource


def build_encounter(
    encounter_id: str,
    patient_ref: str,
    consultation_id: str,
) -> dict:
    """Build a FHIR Encounter resource representing the consultation."""
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "11429006",
                        "display": "Consultation",
                    }
                ]
            }
        ],
        "subject": {"reference": f"Patient/{patient_ref}"},
        "period": {"start": _now_iso(), "end": _now_iso()},
        "identifier": [
            {
                "system": "urn:clinsync:consultation",
                "value": consultation_id,
            }
        ],
    }


def build_condition(
    condition_id: str,
    patient_ref: str,
    encounter_ref: str,
    diagnosis_term: str,
    icd11_code: str | None = None,
    icd11_description: str | None = None,
    snomed_code: str | None = None,
) -> dict:
    """Build a FHIR Condition resource for a diagnosis."""
    coding = []

    if icd11_code:
        coding.append({
            "system": "http://id.who.int/icd/release/11/mms",
            "code": icd11_code,
            "display": icd11_description or diagnosis_term,
        })

    if snomed_code:
        coding.append({
            "system": "http://snomed.info/sct",
            "code": snomed_code,
            "display": diagnosis_term,
        })

    if not coding:
        coding.append({
            "system": "http://terminology.hl7.org/CodeSystem/v3-NullFlavor",
            "code": "UNK",
            "display": diagnosis_term,
        })

    return {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                }
            ]
        },
        "code": {"coding": coding, "text": diagnosis_term},
        "subject": {"reference": f"Patient/{patient_ref}"},
        "encounter": {"reference": f"Encounter/{encounter_ref}"},
        "recordedDate": _now_iso(),
    }


def build_medication_request(
    med_request_id: str,
    patient_ref: str,
    encounter_ref: str,
    medication_name: str,
    dosage: str | None = None,
    frequency: str | None = None,
    duration: str | None = None,
    rxnorm_code: str | None = None,
    generic_name: str | None = None,
) -> dict:
    """Build a FHIR MedicationRequest resource."""
    coding = []
    if rxnorm_code:
        coding.append({
            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
            "code": rxnorm_code,
            "display": generic_name or medication_name,
        })
    else:
        coding.append({
            "system": "http://terminology.hl7.org/CodeSystem/v3-NullFlavor",
            "code": "UNK",
            "display": medication_name,
        })

    resource = {
        "resourceType": "MedicationRequest",
        "id": med_request_id,
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": coding,
            "text": medication_name,
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "encounter": {"reference": f"Encounter/{encounter_ref}"},
        "authoredOn": _now_iso(),
    }

    # Build dosage instruction
    dosage_instruction = {}

    # Always capture full human-readable text first
    if dosage or frequency or duration:
        dosage_instruction["text"] = " ".join(
            filter(None, [dosage, frequency, f"for {duration}" if duration else None])
        )

    if frequency:
        dosage_instruction["timing"] = {
            "code": {"text": frequency}
        }

    # Parse dosage string into numeric value + UCUM unit for FHIR compliance.
    # HAPI strictly requires doseQuantity.value to be a number, not a string.
    # If parsing fails, dosage info is still captured in dosage_instruction.text above.
    if dosage:
        numeric_value, unit_str = _parse_dosage(dosage)
        if numeric_value is not None:
            dose_quantity: dict = {
                "value": numeric_value,
                "system": "http://unitsofmeasure.org",
            }
            if unit_str:
                dose_quantity["unit"] = unit_str
                dose_quantity["code"] = unit_str

            dosage_instruction["doseAndRate"] = [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/dose-rate-type",
                                "code": "ordered",
                                "display": "Ordered",
                            }
                        ]
                    },
                    "doseQuantity": dose_quantity,
                }
            ]
        # If parse fails, skip doseAndRate — text field already has the info

    if dosage_instruction:
        resource["dosageInstruction"] = [dosage_instruction]

    return resource


def build_observation(
    obs_id: str,
    patient_ref: str,
    encounter_ref: str,
    vital_name: str,
    vital_value: str,
    vital_unit: str | None = None,
    snomed_code: str | None = None,
) -> dict:
    """Build a FHIR Observation resource for a vital sign."""

    # Well-known LOINC codes for common vitals
    loinc_map = {
        "blood pressure": ("55284-4", "Blood pressure systolic and diastolic"),
        "temperature": ("8310-5", "Body temperature"),
        "heart rate": ("8867-4", "Heart rate"),
        "pulse": ("8867-4", "Heart rate"),
        "spo2": ("59408-5", "Oxygen saturation"),
        "oxygen saturation": ("59408-5", "Oxygen saturation"),
        "respiratory rate": ("9279-1", "Respiratory rate"),
        "weight": ("29463-7", "Body weight"),
        "height": ("8302-2", "Body height"),
        "bmi": ("39156-5", "Body mass index"),
    }

    loinc_key = vital_name.lower().strip()
    loinc_code, loinc_display = loinc_map.get(loinc_key, (None, vital_name))

    coding = []
    if loinc_code:
        coding.append({
            "system": "http://loinc.org",
            "code": loinc_code,
            "display": loinc_display,
        })
    if snomed_code:
        coding.append({
            "system": "http://snomed.info/sct",
            "code": snomed_code,
        })

    # HAPI requires at least one coding entry with a system.
    # Fall back to NullFlavor if no known code is available.
    if not coding:
        coding.append({
            "system": "http://terminology.hl7.org/CodeSystem/v3-NullFlavor",
            "code": "UNK",
            "display": vital_name,
        })

    resource = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": coding,
            "text": vital_name,
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "encounter": {"reference": f"Encounter/{encounter_ref}"},
        "effectiveDateTime": _now_iso(),
        "valueString": f"{vital_value} {vital_unit or ''}".strip(),
    }

    return resource


def build_transaction_bundle(resources: list[dict]) -> dict:
    """
    Wrap multiple FHIR resources into a transaction bundle.
    Submitted as a single atomic POST to the FHIR server.
    """
    entries = []
    for resource in resources:
        resource_type = resource["resourceType"]
        resource_id = resource.get("id", str(uuid.uuid4()))
        entries.append({
            "fullUrl": f"urn:uuid:{resource_id}",
            "resource": resource,
            "request": {
                "method": "POST",
                "url": resource_type,
            },
        })

    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries,
    }