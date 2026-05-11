"""
ClinSync – AI-Powered Clinical Documentation & FHIR Automation System
Entry point for the FastAPI backend.
"""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, consultations, fhir, approvals, auth
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.database import create_all_tables
from app.kafka.producer import kafka_producer
from app.api import health, consultations, fhir, approvals, auth


logger = structlog.get_logger(__name__)

_consumer_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _consumer_task
    configure_logging()
    logger.info("ClinSync backend starting", env=settings.ENVIRONMENT)
    await create_all_tables()
    logger.info("Database tables ready")

    if settings.USE_KAFKA:
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
        logger.info(
            "Kafka disabled (USE_KAFKA=false) — pipeline will run in-process via BackgroundTasks"
        )

    yield

    if _consumer_task:
        _consumer_task.cancel()
    if settings.USE_KAFKA:
        try:
            await kafka_producer.stop()
        except Exception:
            pass
    logger.info("ClinSync backend shutting down")

# 1. Create the App FIRST
app = FastAPI(
    title="ClinSync API",
    lifespan=lifespan,
)

# 2. Define allowed origins
# Local dev defaults cover Vite (5173), the old static frontend (5500),
# and the docker-compose frontend (3000). Production URLs come from
# settings.CORS_ORIGINS (.env).
origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

# Add Render / Vercel URLs from CORS_ORIGINS env var if set.
if settings.CORS_ORIGINS:
    if isinstance(settings.CORS_ORIGINS, list):
        origins.extend(settings.CORS_ORIGINS)
    else:
        origins.append(settings.CORS_ORIGINS)

# Deduplicate while preserving order.
origins = list(dict.fromkeys(origins))

# 3. Add Middleware SECOND
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"], # Crucial for some browsers to read the response
)

# 4. Include Routers LAST
app.include_router(health.router, tags=["Health"])
app.include_router(consultations.router, prefix="/api/v1/consultations", tags=["Consultations"])
app.include_router(fhir.router, prefix="/api/v1/fhir", tags=["FHIR"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Approvals"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])