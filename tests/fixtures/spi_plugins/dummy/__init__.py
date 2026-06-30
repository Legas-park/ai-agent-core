"""SPI 회귀 테스트용 더미 플러그인 — 프로덕션 plugins_dir 밖, 테스트에서만 로드."""

from typing import Any, Dict, List

from core.agent.base_agent import BaseAgent
from core.agent.context import AgentContext
from core.plugin import ServicePlugin


class DummyEchoAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentContext:
        payload: Dict[str, Any] = context.metadata.get("payload", {})
        context.set_output("echo", payload.get("spi_test_value", ""))
        await self.log_info(context, "SPI 더미 에이전트 실행 완료")
        return context


class DummySpiPlugin(ServicePlugin):
    @property
    def name(self) -> str:
        return "dummy_spi_service"

    def can_handle(self, payload: Dict[str, Any]) -> bool:
        return payload.get("spi_test") is True

    def get_pipeline(self, payload: Dict[str, Any]) -> List[BaseAgent]:
        return [DummyEchoAgent(name="DummyEchoAgent")]


plugin = DummySpiPlugin()
