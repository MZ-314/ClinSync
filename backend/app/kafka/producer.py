"""
Kafka producer – thin async wrapper used by the agents to emit events.
"""

import json
from aiokafka import AIOKafkaProducer
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class KafkaProducerClient:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info("Kafka producer started", servers=settings.KAFKA_BOOTSTRAP_SERVERS)

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def send(self, topic: str, payload: dict):
        if not self._producer:
            raise RuntimeError("Kafka producer not started.")
        await self._producer.send_and_wait(topic, payload)
        logger.debug("Kafka message sent", topic=topic)


# Singleton used across the app
kafka_producer = KafkaProducerClient()