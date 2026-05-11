"""
Medical Coding Agent — Step 3 of the ClinSync pipeline.

Responsibilities:
1. Receive extracted entities from Kafka (clinsync.extraction topic)
2. Look up ICD-11 codes via WHO API for diagnoses
3. Use Groq LLaMA to assign SNOMED CT and RxNorm codes
4. Merge API results with LLM results
5. Store coded data in DB
6. Emit Kafka event to trigger FHIR builder
"""

import json
import structlog
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.coding.icd11_client import icd11_client
from app.agents.coding.schemas import CodingResult, CodedDiagnosis, CodedSymptom, CodedMedication
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.kafka.producer import kafka_producer
from app.models.consultation import Consultation, ConsultationStatus
from app.prompts.coding_prompt import CODING_SYSTEM_PROMPT, build_coding_prompt

logger = structlog.get_logger(__name__)


class CodingAgent:

    def __init__(self):
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def run_from_kafka(self, consultation_id: str, entities: dict) -> None:
        """Entry point called by the Kafka consumer."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Consultation).where(Consultation.id == consultation_id)
            )
            consultation = result.scalar_one_or_none()

            if not consultation:
                logger.error("Consultation not found", consultation_id=consultation_id)
                return

            await self.run(consultation, entities, db)

    async def run(
        self,
        consultation: Consultation,
        entities: dict,
        db: AsyncSession,
        emit_kafka: bool = True,  # ← added: False when called from LangGraph
    ) -> Consultation:
        consultation_id = str(consultation.id)
        logger.info("Coding agent started", consultation_id=consultation_id)

        # ── Step 1: Mark as coding ────────────────────────────────────────────
        consultation.status = ConsultationStatus.CODING
        await db.commit()

        try:
            # ── Step 2: ICD-11 lookup for diagnoses ───────────────────────────
            diagnoses = entities.get("diagnosis", [])
            icd11_results = await self._lookup_icd11(diagnoses)

            # ── Step 3: Groq for SNOMED + RxNorm ─────────────────────────────
            llm_coding = await self._code_with_llm(entities)

            # ── Step 4: Merge results ─────────────────────────────────────────
            coding_result = self._merge_results(icd11_results, llm_coding, entities)

        except Exception as e:
            logger.error("Coding failed", consultation_id=consultation_id, error=str(e))
            consultation.status = ConsultationStatus.FAILED
            consultation.error_message = f"Coding error: {str(e)}"
            await db.commit()
            raise

        # ── Step 5: Persist coded data ────────────────────────────────────────
        consultation.coded_data = coding_result.model_dump_json()
        consultation.status = ConsultationStatus.CODED
        consultation.error_message = None
        await db.commit()

        logger.info(
            "Coding complete",
            consultation_id=consultation_id,
            diagnoses=[f"{d.term}→{d.icd11_code}" for d in coding_result.diagnoses],
            medications=[m.name for m in coding_result.medications],
        )

        # ── Step 6: Emit Kafka event (skipped when called from LangGraph) ─────
        if emit_kafka:
            await self._emit_fhir_event(consultation_id, coding_result)

        return consultation

    async def _lookup_icd11(self, diagnoses: list[str]) -> dict[str, tuple]:
        """Look up ICD-11 codes for each diagnosis via WHO API."""
        results = {}
        for diagnosis in diagnoses:
            code, description = await icd11_client.get_best_match(diagnosis)
            results[diagnosis] = (code, description)
            logger.info(
                "ICD-11 lookup",
                term=diagnosis,
                code=code,
                description=description,
            )
        return results

    async def _code_with_llm(self, entities: dict) -> CodingResult:
        """Use Groq LLaMA to assign SNOMED CT and RxNorm codes."""
        response = await self._client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": CODING_SYSTEM_PROMPT},
                {"role": "user", "content": build_coding_prompt(entities)},
            ],
            temperature=0.1,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        return CodingResult(**data)

    def _merge_results(
        self,
        icd11_results: dict,
        llm_coding: CodingResult,
        entities: dict,
    ) -> CodingResult:
        """
        Merge ICD-11 API results (authoritative) with LLM SNOMED/RxNorm codes.
        ICD-11 API results override LLM ICD-11 codes where available.
        """
        merged_diagnoses = []
        for llm_diag in llm_coding.diagnoses:
            icd_code, icd_desc = icd11_results.get(llm_diag.term, (None, None))
            merged_diagnoses.append(CodedDiagnosis(
                term=llm_diag.term,
                icd11_code=icd_code or llm_diag.icd11_code,
                icd11_description=icd_desc or llm_diag.icd11_description,
                snomed_code=llm_diag.snomed_code,
                snomed_description=llm_diag.snomed_description,
            ))

        llm_terms = {d.term for d in llm_coding.diagnoses}
        for term, (code, desc) in icd11_results.items():
            if term not in llm_terms and code:
                merged_diagnoses.append(CodedDiagnosis(
                    term=term,
                    icd11_code=code,
                    icd11_description=desc,
                ))

        return CodingResult(
            diagnoses=merged_diagnoses,
            symptoms=llm_coding.symptoms,
            medications=llm_coding.medications,
        )

    async def _emit_fhir_event(
        self, consultation_id: str, coding_result: CodingResult
    ) -> None:
        """Publish event to Kafka so the FHIR builder picks it up."""
        payload = {
            "event": "coding.completed",
            "consultation_id": consultation_id,
            "coding": coding_result.model_dump(),
        }
        try:
            await kafka_producer.send(
                topic=settings.KAFKA_TOPIC_FHIR,
                payload=payload,
            )
            logger.info(
                "Kafka event emitted",
                topic=settings.KAFKA_TOPIC_FHIR,
                consultation_id=consultation_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to emit Kafka event",
                consultation_id=consultation_id,
                error=str(e),
            )


# Singleton
coding_agent = CodingAgent()