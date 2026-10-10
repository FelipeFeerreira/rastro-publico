"""Limitador de taxa simples baseado em Redis, com fallback em memória.

Em produção usa Redis (contadores por janela deslizante de 60s). Se o Redis não
estiver disponível ou configurado, cai para um contador em memória do processo,
suficiente para desenvolvimento e testes.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_memory_lock = threading.Lock()
_memory_counters: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))

_redis_client = None
_redis_unavailable = False


def _get_redis():
    global _redis_client, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # noqa: PLC0415

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        _redis_client = client
        return client
    except Exception:  # noqa: BLE001 - fallback intencional
        _redis_unavailable = True
        logger.info("Redis indisponível; usando limite de taxa em memória.")
        return None


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
    """Retorna (permitido, contagem_atual)."""
    client = _get_redis()
    if client is not None:
        try:
            redis_key = f"ratelimit:{key}"
            current = client.incr(redis_key)
            if current == 1:
                client.expire(redis_key, window_seconds)
            return current <= limit, int(current)
        except Exception:  # noqa: BLE001
            logger.warning("Falha ao consultar Redis para rate limit; usando memória.")

    now = time.time()
    with _memory_lock:
        count, window_start = _memory_counters[key]
        if now - window_start >= window_seconds:
            count, window_start = 0, now
        count += 1
        _memory_counters[key] = (count, window_start)
        return count <= limit, count


def reset_rate_limits() -> None:
    """Limpa o estado em memória (usado em testes)."""
    with _memory_lock:
        _memory_counters.clear()
