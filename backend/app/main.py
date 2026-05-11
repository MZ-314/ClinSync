"""
ClinSync – AI-Powered Clinical Documentation & FHIR Automation System
Entry point for the FastAPI backend.
"""

import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, consultations, fhir, approvals
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.database import create_all_tables

logger = structlog.get_logger(__name__)

_consumer_task: asyncio.Task | None = None
USE_KAFKA = os.getenv("USE_KAFKA", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _consumer_task

    configure_logging()
    logger.info("ClinSync backend starting", env=settings.ENVIRONMENT, kafka=USE_KAFKA)

    await create_all_tables()
    logger.info("Database tables ready")

    if USE_KAFKA:
        from app.kafka.producer import kafka_producer
        try:
            await kafka_producer.start()
            logger.info("Kafka producer connected")
        except Exception as e:
            logger.warning("Kafka not ready at startup", error=str(e))

        try:
            from app.kafka.consumer import start_consumer
            _consumer_task = asyncio.create_task(start_consumer())
            logger.info("Kafka consumer started")
        except Exception as e:
            logger.warning("Kafka consumer failed to start", error=str(e))
    else:
        logger.info("Kafka disabled — running in direct pipeline mode")

    yield

    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass

    if USE_KAFKA:
        try:
            from app.kafka.producer import kafka_producer
            await kafka_producer.stop()
        except Exception:
            pass

    logger.info("ClinSync backend shutting down")


app = FastAPI(
    title="ClinSync API",
    description="AI-Powered Clinical Documentation & FHIR Automation System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(consultations.router, prefix="/api/v1/consultations", tags=["Consultations"])
app.include_router(fhir.router, prefix="/api/v1/fhir", tags=["FHIR"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Approvals"])