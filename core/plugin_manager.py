import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings
from core.plugin import ServicePlugin


class PluginManager:
    """
    [코어 핵심] settings.plugins_dir 하위 플러그인을 동적으로 탐색·로드합니다.
    `_` 접두사 폴더는 제외되며, 코어는 특정 서비스명을 알 필요가 없습니다.
    """

    def __init__(self):
        self.plugins: List[ServicePlugin] = []

    @staticmethod
    def _resolve_plugins_path() -> Path:
        path = Path(settings.plugins_dir)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()

    @staticmethod
    def _resolve_project_root(plugins_path: Path) -> Path:
        if plugins_path.name == "plugins" and plugins_path.parent.name == "services":
            return plugins_path.parent.parent.resolve()
        return Path.cwd().resolve()

    @staticmethod
    def _import_plugin_module(plugin_dir: Path, project_root: Path):
        services_plugins = (project_root / "services" / "plugins").resolve()
        if plugin_dir.resolve().parent == services_plugins:
            module_name = f"services.plugins.{plugin_dir.name}"
            return importlib.import_module(module_name)

        module_name = f"_dynamic_plugin.{plugin_dir.name}"
        init_file = plugin_dir / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_file,
            submodule_search_locations=[str(plugin_dir)],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"플러그인 모듈을 로드할 수 없습니다: {plugin_dir}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def load_plugins(self):
        """
        plugins_dir 하위 디렉터리를 스캔해 `plugin` 전역 변수가 있는 ServicePlugin을 등록합니다.
        """
        self.plugins.clear()
        plugins_path = self._resolve_plugins_path()
        if not plugins_path.exists():
            logger.warning(f"플러그인 디렉토리 {plugins_path} 가 존재하지 않아 동적 로드를 중단합니다.")
            return

        project_root = self._resolve_project_root(plugins_path)
        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        for plugin_dir in sorted(plugins_path.iterdir()):
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("_") or plugin_dir.name.startswith("."):
                continue
            if not (plugin_dir / "__init__.py").is_file():
                continue
            try:
                module = self._import_plugin_module(plugin_dir, project_root)
                if not hasattr(module, "plugin"):
                    continue
                plugin_instance = getattr(module, "plugin")
                if isinstance(plugin_instance, ServicePlugin):
                    self.plugins.append(plugin_instance)
                    logger.info(f"동적 서비스 플러그인 로드 성공: {plugin_instance.name}")
            except Exception as exc:
                logger.error(f"플러그인 {plugin_dir.name} 로드 실패: {exc}")

    def get_handler_for_payload(self, payload: Dict[str, Any]) -> Optional[ServicePlugin]:
        for plugin in self.plugins:
            if plugin.can_handle(payload):
                return plugin
        return None


plugin_manager = PluginManager()
