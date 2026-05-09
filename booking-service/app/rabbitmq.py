import json

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

from app.config import get_settings
from app.schemas import BookingMessage


settings = get_settings()


class RabbitMQProducer:
    def __init__(self, rabbitmq_url: str, queue_name: str) -> None:
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractChannel | None = None

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(self.queue_name, durable=True)

    async def publish_booking(self, booking: BookingMessage) -> None:
        if self.channel is None:
            await self.connect()

        if self.channel is None:
            raise RuntimeError("RabbitMQ channel is not available")

        message = Message(
            body=json.dumps(booking.model_dump()).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.queue_name,
        )

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
            self.channel = None


producer = RabbitMQProducer(
    rabbitmq_url=settings.rabbitmq_url,
    queue_name=settings.booking_queue,
)
