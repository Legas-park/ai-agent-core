"""
플러그인 SPI 회귀 테스트.

fixture 더미 플러그인으로 can_handle → orchestrator → agent 실행까지 검증합니다.
프로덕션 services/plugins/ 는 건드리지 않습니다.
"""

from pathlib import Path

import pytest

from core.agent.context import AgentContext
from core.plugin_manager import PluginManager

pytestmark = pytest.mark.asyncio

FIXTURE_PLUGINS_DIR = Path(__file__).parent / "fixtures" / "spi_plugins"


@pytest.fixture
def spi_plugin_manager(monkeypatch):
    """tests/fixtures/spi_plugins 만 로드하는 PluginManager."""
    monkeypatch.setattr("core.plugin_manager.settings.plugins_dir", str(FIXTURE_PLUGINS_DIR))
    manager = PluginManager()
    manager.load_plugins()
    return manager


async def test_fixture_plugin_loads_without_production_plugins(spi_plugin_manager):
    assert len(spi_plugin_manager.plugins) == 1
    assert spi_plugin_manager.plugins[0].name == "dummy_spi_service"


async def test_fixture_plugin_can_handle_and_runs_pipeline(spi_plugin_manager):
    payload = {"spi_test": True, "spi_test_value": "hello-spi"}
    plugin = spi_plugin_manager.get_handler_for_payload(payload)
    assert plugin is not None
    assert plugin.name == "dummy_spi_service"

    context = AgentContext(task_id="spi-001", metadata={"payload": payload})
    orchestrator = plugin.build_orchestrator(payload)
    final = await orchestrator.run(context)

    assert final.error is None
    assert final.get_output("echo") == "hello-spi"


async def test_unmatched_payload_returns_no_handler(spi_plugin_manager):
    assert spi_plugin_manager.get_handler_for_payload({"other": True}) is None
