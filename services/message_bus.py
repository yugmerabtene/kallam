import json
import os

from django.conf import settings

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:  # pragma: no cover
    KafkaProducer = None
    KafkaError = Exception


class MessageBus:
    _instance = None

    def __init__(self):
        self.enabled = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self._producer = None
        self._init_producer()

    def _init_producer(self):
        if self.enabled and self.bootstrap_servers and KafkaProducer:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=2,
            )

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(self, topic, value):
        if not self.enabled or not self._producer:
            return
        try:
            self._producer.send(topic, value)
            self._producer.flush()
        except KafkaError:
            pass
