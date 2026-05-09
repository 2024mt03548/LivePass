import json

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractRobustConnection

from app.config import get_settings


settings = get_settings()


class RabbitMQConsumer:
    def __init__(self, rabbitmq_url: str, queue_name: str) -> None:
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractChannel | None = None
        self.queue: AbstractQueue | None = None

    async def connect(self) -> AbstractQueue:
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
        await self.channel.declare_queue(settings.booking_confirmed_queue, durable=True)
        await self.channel.declare_queue(settings.booking_rejected_queue, durable=True)
        return self.queue

    async def publish_event(self, routing_key: str, payload: dict) -> None:
        if self.channel is None:
            await self.connect()

        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not available")

        message = Message(
            body=json.dumps(payload, default=str).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self.channel.default_exchange.publish(message, routing_key=routing_key)

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.queue = None


consumer = RabbitMQConsumer(
    rabbitmq_url=settings.rabbitmq_url,
    queue_name=settings.booking_queue,
)
