"""외부 서비스(GitLab, GitHub, Slack 등) 중앙 레지스트리."""
from typing import Any, Dict, Optional

from loguru import logger


class ServiceRegistry:
    """
    코어가 제공하는 추상 서비스 구현체를 이름으로 보관합니다.
    에이전트는 `service_registry.get("repository")`로 GitLab/GitHub를 구분하지 않고 사용합니다.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any):
        if service is None:
            logger.debug(f"서비스 '{name}' 등록 생략 (구현체 없음)")
            return
        self._services[name] = service
        logger.info(f"서비스 레지스트리 등록: {name} ({type(service).__name__})")

    def get(self, name: str) -> Optional[Any]:
        return self._services.get(name)

    def has(self, name: str) -> bool:
        return name in self._services


service_registry = ServiceRegistry()
