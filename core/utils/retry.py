import asyncio
import random
from functools import wraps
from typing import Callable, Tuple, Type
from loguru import logger


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.2,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    [코어 유틸] 외부 I/O(LLM API, GitLab API 등) 호출처럼 일시적 실패가 잦은 코루틴에
    지수 백오프(exponential backoff) + 지터(jitter) 기반 자동 재시도를 입히는 데코레이터입니다.

    네트워크 순단·5xx·레이트리밋 같은 일시 장애를 흡수하여 파이프라인이 단발성 오류로
    통째로 무너지는 것을 예방합니다. 마지막 시도까지 실패하면 원본 예외를 그대로 전파합니다.

    Args:
        max_attempts: 최초 1회를 포함한 총 시도 횟수
        base_delay: 첫 재시도 전 대기 시간(초)
        max_delay: 백오프 상한(초)
        backoff_factor: 시도마다 대기 시간을 곱할 배수
        jitter: 천둥 무리(thundering herd)를 막기 위한 무작위 가중치 비율
        retry_on: 재시도를 허용할 예외 타입 튜플
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:  # noqa: PERF203
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            f"[retry] {func.__name__} 최종 실패 (시도 {attempt}/{max_attempts}): {exc}"
                        )
                        raise
                    sleep_for = min(delay, max_delay) * (1 + random.uniform(0, jitter))
                    logger.warning(
                        f"[retry] {func.__name__} 실패 (시도 {attempt}/{max_attempts}), "
                        f"{sleep_for:.2f}s 후 재시도: {exc}"
                    )
                    await asyncio.sleep(sleep_for)
                    delay *= backoff_factor
            # 도달 불가 (방어적)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
