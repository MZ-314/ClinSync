"""
ClinSync LangGraph workflow graph.

Defines the StateGraph, wires nodes and conditional edges,
and compiles it into a runnable. This is the single entry point
the Kafka consumer calls to run the full pipeline.

Graph shape:

    [START]
       │
  transcribe_node
       │
  route_after_transcribe ──────────────────────┐
       │ (no error)                             │ (error)
  extract_node                            handle_error_node
       │                                        │
  route_after_extract ─────────────────┐   [END]
       │ (diagnosis found)             │ (no diagnosis / error)
  code_node                     pending_review_node
       │                                        │
  route_after_code ──────────────────┐     [END]
       │ (no error)                  │ (error)
  build_fhir_node             handle_error_node
       │
  route_after_fhir ──────────────────┐
       │ (no error)                  │ (error)
  pending_review_node         handle_error_node
       │
    [END]
"""

import structlog
from langgraph.graph import StateGraph, END

from app.agents.workflow.state import ClinSyncState
from app.agents.workflow.nodes import (
    transcribe_node,
    extract_node,
    code_node,
    build_fhir_node,
    pending_review_node,
    handle_error_node,
    route_after_transcribe,
    route_after_extract,
    route_after_code,
    route_after_fhir,
)

logger = structlog.get_logger(__name__)


def build_graph() -> StateGraph:
    """
    Construct and compile the ClinSync LangGraph StateGraph.
    Called once at startup; the compiled graph is reused for every consultation.
    """
    graph = StateGraph(ClinSyncState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("extract", extract_node)
    graph.add_node("code", code_node)
    graph.add_node("build_fhir", build_fhir_node)
    graph.add_node("pending_review", pending_review_node)
    graph.add_node("handle_error", handle_error_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("transcribe")

    # ── Conditional edges ──────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "transcribe",
        route_after_transcribe,
        {
            "extract": "extract",
            "handle_error": "handle_error",
        },
    )

    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "code": "code",
            "pending_review": "pending_review",   # no diagnosis branch
            "handle_error": "handle_error",
        },
    )

    graph.add_conditional_edges(
        "code",
        route_after_code,
        {
            "build_fhir": "build_fhir",
            "handle_error": "handle_error",
        },
    )

    graph.add_conditional_edges(
        "build_fhir",
        route_after_fhir,
        {
            "pending_review": "pending_review",
            "handle_error": "handle_error",
        },
    )

    # ── Terminal nodes go to END ───────────────────────────────────────────────
    graph.add_edge("pending_review", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


def build_post_transcription_graph() -> StateGraph:
    """
    Variant of the main graph that starts at `extract`, used when transcription
    has already been completed synchronously by the upload endpoint
    (in-process / no-Kafka mode). Skips the transcribe node to avoid a second
    Deepgram call on the same audio.
    """
    graph = StateGraph(ClinSyncState)

    graph.add_node("extract", extract_node)
    graph.add_node("code", code_node)
    graph.add_node("build_fhir", build_fhir_node)
    graph.add_node("pending_review", pending_review_node)
    graph.add_node("handle_error", handle_error_node)

    graph.set_entry_point("extract")

    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "code": "code",
            "pending_review": "pending_review",
            "handle_error": "handle_error",
        },
    )
    graph.add_conditional_edges(
        "code",
        route_after_code,
        {"build_fhir": "build_fhir", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "build_fhir",
        route_after_fhir,
        {"pending_review": "pending_review", "handle_error": "handle_error"},
    )

    graph.add_edge("pending_review", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


# ── Compiled graph singletons ──────────────────────────────────────────────────
# `clinsync_graph`             — full pipeline starting at transcribe (Kafka path)
# `clinsync_post_transcription_graph` — extraction onward (in-process path)
clinsync_graph = build_graph()
clinsync_post_transcription_graph = build_post_transcription_graph()


async def run_consultation_workflow(
    consultation_id: str,
    audio_bytes: bytes,
    mime_type: str,
) -> ClinSyncState:
    """
    Entry point for the Kafka consumer.
    Initialises state and runs the compiled graph to completion.
    Returns the final state for logging/debugging.
    """
    logger.info(
        "Starting ClinSync workflow",
        consultation_id=consultation_id,
        mime_type=mime_type,
        audio_size=len(audio_bytes),
    )

    initial_state: ClinSyncState = {
        "consultation_id": consultation_id,
        "audio_bytes": audio_bytes,
        "mime_type": mime_type,
        "transcript": None,
        "language": None,
        "duration_seconds": None,
        "extracted_entities": None,
        "coding": None,
        "fhir_bundle_response": None,
        "status": "uploaded",
        "error": None,
    }

    final_state = await clinsync_graph.ainvoke(initial_state)

    logger.info(
        "ClinSync workflow complete",
        consultation_id=consultation_id,
        final_status=final_state.get("status"),
        error=final_state.get("error"),
    )

    return final_state


async def run_post_transcription_workflow(
    consultation_id: str,
    transcript: str,
    language: str | None = None,
    duration_seconds: float | None = None,
) -> ClinSyncState:
    """
    Entry point used by the upload endpoint when running in-process
    (no Kafka). Assumes transcription has already completed synchronously,
    so the graph starts at `extract`.
    """
    logger.info(
        "Starting post-transcription workflow",
        consultation_id=consultation_id,
        transcript_len=len(transcript or ""),
    )

    initial_state: ClinSyncState = {
        "consultation_id": consultation_id,
        "audio_bytes": b"",
        "mime_type": "",
        "transcript": transcript,
        "language": language,
        "duration_seconds": duration_seconds,
        "extracted_entities": None,
        "coding": None,
        "fhir_bundle_response": None,
        "status": "transcribed",
        "error": None,
    }

    final_state = await clinsync_post_transcription_graph.ainvoke(initial_state)

    logger.info(
        "Post-transcription workflow complete",
        consultation_id=consultation_id,
        final_status=final_state.get("status"),
        error=final_state.get("error"),
    )

    return final_state