"""
ClinSync LangGraph workflow state.

This TypedDict is passed between every node in the graph.
Each node receives the full state and returns a partial update.
"""

from typing import TypedDict


class ClinSyncState(TypedDict):
    # ── Identity ───────────────────────────────────────────────────────────────
    consultation_id: str

    # ── Input ─────────────────────────────────────────────────────────────────
    audio_bytes: bytes
    mime_type: str

    # ── Transcription output ───────────────────────────────────────────────────
    transcript: str | None
    language: str | None
    duration_seconds: float | None

    # ── Extraction output ──────────────────────────────────────────────────────
    extracted_entities: dict | None   # parsed ClinicalEntities dict

    # ── Coding output ──────────────────────────────────────────────────────────
    coding: dict | None               # diagnoses + medications with codes

    # ── FHIR output ────────────────────────────────────────────────────────────
    fhir_bundle_response: dict | None

    # ── Control ────────────────────────────────────────────────────────────────
    status: str                       # mirrors ConsultationStatus enum value
    error: str | None                 # set on any failure, triggers error branch