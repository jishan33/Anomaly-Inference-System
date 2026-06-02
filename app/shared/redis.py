import logging
import os
import redis

from redis import Redis
from typing import Literal
from app.shared.circuit_breaker import CircuitBreaker

logger =logging.getLogger(__name__)

RedisHostType = Literal["sync", "inference"]
REDIS_HOST = os.getenv("REDIS_HOST", "unknown")

SYNC_REDIS_HOST = os.getenv("REDIS_SYNC_HOST", "localhost")
SYNC_REDIS_PORT = int(os.getenv("REDIS_SYNC_PORT", "6380"))

REDIS_INFERENCE_HOST = os.getenv("REDIS_INFERENCE_HOST", "localhost")
REDIS_INFERENCE_PORT = int(os.getenv("REDIS_INFERENCE_PORT", "6379"))

sync_redis_client: Redis = redis.Redis(
    host=SYNC_REDIS_HOST,
    port=SYNC_REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=0.2,  # connection timeout
    socket_timeout=0.2,
    retry_on_timeout=False,
    health_check_interval=0,
)

inference_redis_client: Redis = redis.Redis(
    host=REDIS_INFERENCE_HOST,
    port=REDIS_INFERENCE_PORT,
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

def get_redis_client() -> Redis:
   logger.info(f"REDIS_HOST: {REDIS_HOST}/////////////" +
               f"SYNC_REDIS_HOST: {SYNC_REDIS_HOST}/////////////"+
               f"SYNC_REDIS_PORT: {SYNC_REDIS_PORT}/////////////"+
               f"REDIS_INFERENCE_HOST: {REDIS_INFERENCE_HOST}/////////////"+
               f"REDIS_INFERENCE_PORT: {REDIS_INFERENCE_PORT}/////////////" )
   match REDIS_HOST:
    case "inference":
        return inference_redis_client
    case "sync":
        return sync_redis_client
   return sync_redis_client


