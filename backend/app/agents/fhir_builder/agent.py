"""
FHIR Builder Agent — Step 4 of the ClinSync pipeline.

Responsibilities:
1. Receive coded data from Kafka (clinsync.fhir topic)
2. Build valid FHIR R4 resources from coded entities
3. Submit resources to HAPI FHIR server as a transaction bundle
4. Store resource references in DB
5. Update consultation status to PENDING_REVIEW (awaiting doctor approval)

Key design note on FHIR transaction bundles:
  Each entry has a `fullUrl: urn:uuid:<id>`. ALL cross-resource references
  (subject, encounter, etc.) must use the same `urn:uuid:<id>` form so that
  HAPI resolves them within the bundle instead of trying to fetch them from
  the server (which causes HAPI-1094 "resource not found" errors).
"""

import json
import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.fhir_builder.fhir_client import hapi_fhir_client
from app.agents.fhir_builder.resource_builder import (
    build_patient,
    build_encounter,
    build_condition,
    build_medication_request,
    build_observation,
    build_transaction_bundle,
)
from app.core.database import AsyncSessionLocal
from app.models.consultation import Consultation, ConsultationStatus
from app.models.fhir_record import FHIRRecord, FHIRResourceType

logger = structlog.get_logger(__name__)


class FHIRBuilderAgent:

    async def run_from_kafka(
        self, consultation_id: str, coding: dict
    ) -> None:
        """Entry point called by the Kafka consumer."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()

            if not consultation:
                logger.error("Consultation not found", consultation_id=consultation_id)
                return

            await self.run(consultation, coding, db)

    async def run(
        self,
        consultation: Consultation,
        coding: dict,
        db: AsyncSession,
    ) -> Consultation:
        consultation_id = str(consultation.id)
        logger.info("FHIR builder agent started", consultation_id=consultation_id)

        # ── Step 1: Mark as building FHIR ─────────────────────────────────────
        consultation.status = ConsultationStatus.BUILDING_FHIR
        await db.commit()

        try:
            # ── Step 2: Build FHIR resources ──────────────────────────────────
            resources, fhir_records = self._build_resources(consultation, coding)

            # ── Step 3: Submit bundle to HAPI FHIR server ─────────────────────
            bundle = build_transaction_bundle(resources)
            bundle_response = await hapi_fhir_client.submit_bundle(bundle)

            # ── Step 4: Extract server-assigned IDs from response ─────────────
            server_ids = self._extract_server_ids(bundle_response)

        except Exception as e:
            logger.error(
                "FHIR build failed",
                consultation_id=consultation_id,
                error=str(e),
            )
            consultation.status = ConsultationStatus.FAILED
            consultation.error_message = f"FHIR error: {str(e)}"
            await db.commit()
            raise

        # ── Step 5: Save FHIR records to DB ───────────────────────────────────
        for i, (fhir_record, resource) in enumerate(zip(fhir_records, resources)):
            fhir_record.resource_json = json.dumps(resource)
            fhir_record.is_valid = True
            fhir_record.is_submitted = True
            if i < len(server_ids):
                fhir_record.fhir_server_id = server_ids[i]
            db.add(fhir_record)

        # ── Step 6: Move to PENDING_REVIEW (awaiting doctor approval) ─────────
        consultation.status = ConsultationStatus.PENDING_REVIEW
        consultation.error_message = None
        await db.commit()

        logger.info(
            "FHIR resources built and submitted",
            consultation_id=consultation_id,
            resource_count=len(resources),
            status="pending_review",
        )

        return consultation

    def _build_resources(
        self,
        consultation: Consultation,
        coding: dict,
    ) -> tuple[list[dict], list[FHIRRecord]]:
        """
        Build all FHIR resources for this consultation.

        IMPORTANT: References between resources (subject, encounter) must use
        `urn:uuid:<id>` — not `Patient/<id>` or `Encounter/<id>` — so that
        HAPI FHIR resolves them within the transaction bundle rather than
        trying to fetch them from the server (which causes HAPI-1094).
        """
        consultation_id = str(consultation.id)
        resources = []
        fhir_records = []

        # Parse extracted entities for demographics
        extracted = {}
        if consultation.extracted_entities:
            extracted = json.loads(consultation.extracted_entities)

        # Generate stable UUIDs for intra-bundle references
        patient_uuid = str(uuid.uuid4())
        encounter_uuid = str(uuid.uuid4())

        # Use urn:uuid: prefix for all cross-resource references
        patient_ref = f"urn:uuid:{patient_uuid}"
        encounter_ref = f"urn:uuid:{encounter_uuid}"

        # ── Patient ────────────────────────────────────────────────────────────
        patient = build_patient(
            patient_id=patient_uuid,
            name="Patient",
            age=extracted.get("patient_age"),
            gender=extracted.get("patient_gender"),
        )
        resources.append(patient)
        fhir_records.append(FHIRRecord(
            consultation_id=consultation.id,
            resource_type=FHIRResourceType.PATIENT,
            resource_json="{}",
        ))

        # ── Encounter ─────────────────────────────────────────────────────────
        encounter = build_encounter(
            encounter_id=encounter_uuid,
            patient_ref=patient_ref,       # urn:uuid: reference
            consultation_id=consultation_id,
        )
        resources.append(encounter)
        fhir_records.append(FHIRRecord(
            consultation_id=consultation.id,
            resource_type=FHIRResourceType.ENCOUNTER,
            resource_json="{}",
        ))

        # ── Conditions (diagnoses) ─────────────────────────────────────────────
        for diag in coding.get("diagnoses", []):
            condition = build_condition(
                condition_id=str(uuid.uuid4()),
                patient_ref=patient_ref,       # urn:uuid: reference
                encounter_ref=encounter_ref,   # urn:uuid: reference
                diagnosis_term=diag.get("term", ""),
                icd11_code=diag.get("icd11_code"),
                icd11_description=diag.get("icd11_description"),
                snomed_code=diag.get("snomed_code"),
            )
            resources.append(condition)
            fhir_records.append(FHIRRecord(
                consultation_id=consultation.id,
                resource_type=FHIRResourceType.CONDITION,
                resource_json="{}",
            ))

        # ── MedicationRequests ────────────────────────────────────────────────
        extracted_meds = {
            m["name"].lower(): m
            for m in extracted.get("medications", [])
        }
        for med in coding.get("medications", []):
            med_name = med.get("name", "")
            extracted_med = extracted_meds.get(med_name.lower(), {})
            med_request = build_medication_request(
                med_request_id=str(uuid.uuid4()),
                patient_ref=patient_ref,       # urn:uuid: reference
                encounter_ref=encounter_ref,   # urn:uuid: reference
                medication_name=med_name,
                dosage=extracted_med.get("dosage"),
                frequency=extracted_med.get("frequency"),
                duration=extracted_med.get("duration"),
                rxnorm_code=med.get("rxnorm_code"),
                generic_name=med.get("generic_name"),
            )
            resources.append(med_request)
            fhir_records.append(FHIRRecord(
                consultation_id=consultation.id,
                resource_type=FHIRResourceType.MEDICATION_REQUEST,
                resource_json="{}",
            ))

        # ── Observations (vitals) ──────────────────────────────────────────────
        for vital in extracted.get("vitals", []):
            observation = build_observation(
                obs_id=str(uuid.uuid4()),
                patient_ref=patient_ref,       # urn:uuid: reference
                encounter_ref=encounter_ref,   # urn:uuid: reference
                vital_name=vital.get("name", ""),
                vital_value=vital.get("value", ""),
                vital_unit=vital.get("unit"),
            )
            resources.append(observation)
            fhir_records.append(FHIRRecord(
                consultation_id=consultation.id,
                resource_type=FHIRResourceType.OBSERVATION,
                resource_json="{}",
            ))

        return resources, fhir_records

    def _extract_server_ids(self, bundle_response: dict) -> list[str]:
        """Extract FHIR server-assigned IDs from bundle response."""
        server_ids = []
        for entry in bundle_response.get("entry", []):
            location = entry.get("response", {}).get("location", "")
            if location:
                # location format: "ResourceType/id/_history/1"
                parts = location.split("/")
                if len(parts) >= 2:
                    server_ids.append(f"{parts[0]}/{parts[1]}")
        return server_ids


# Singleton
fhir_builder_agent = FHIRBuilderAgent()