import aio_pika
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
        return self.queue

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
