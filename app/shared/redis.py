import redis

from app.shared.circuit_breaker import CircuitBreaker

# connect to Redis (service name = redis)
redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    socket_connect_timeout=1,  # connection timeout
)

redis_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=10
)