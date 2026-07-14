import logging
import os
import redis

from redis import Redis
from app.shared.circuit_breaker import CircuitBreaker

logger =logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client: Redis = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=0.2,  # connection timeout
    socket_timeout=0.2,
    retry_on_timeout=False,
    health_check_interval=0,
)

redis_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=10
)


