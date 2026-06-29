import importlib
import pkgutil
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from core.plugin import ServicePlugin
from config import settings

class PluginManager:
    """
    [코어 핵심] 'services/plugins' 폴더 하위에 위치한 플러그인들을 동적으로 탐색하고 로드하는 매니저 클래스입니다.
    코드가 특정 서비스명을 몰라도 파이썬의 pkgutil 모듈을 사용해 패키지들을 런타임에 자동 등록함으로써
    코어와 서비스의 결합도를 완전히 제거해 주는 중추 역할을 담당합니다.
    """
    def __init__(self):
        # 로드 완료된 활성 서비스 플러그인 인스턴스들의 보관 리스트
        self.plugins: List[ServicePlugin] = []

    def load_plugins(self):
        """
        [동적 탐색] 지정된 플러그인 디렉토리를 훑으며, 패키지들을 메모리에 자동으로 동적 로드합니다.
        각 플러그인 모듈 내부에 선언된 `plugin` 전역 변수가 ServicePlugin 규격을 만족하면 등록을 수락합니다.
        """
        plugins_path = Path(settings.plugins_dir)
        if not plugins_path.exists():
            logger.warning(f"플러그인 디렉토리 {plugins_path} 가 존재하지 않아 동적 로드를 중단합니다.")
            return

        # 동적 로딩 중 패키지 경로 탐색을 정상화하기 위해 프로젝트의 최상위 루트 디렉토리를 sys.path에 수동 삽입
        project_root = str(plugins_path.parent.parent.absolute())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # services.plugins 모듈 하위의 전체 디렉토리 탐색 수행
        import services.plugins
        prefix = services.plugins.__name__ + "."
        
        # pkgutil.iter_modules를 통해 services.plugins 패키지 안의 폴더 목록을 순회
        for _, module_name, is_pkg in pkgutil.iter_modules(services.plugins.__path__, prefix):
            if is_pkg:
                try:
                    # 런타임 동적 임포트 (예: import services.plugins.code_review)
                    module = importlib.import_module(module_name)
                    
                    # 로드한 모듈 내부에 'plugin'이라는 이름의 객체가 선언되어 있는지 조회
                    if hasattr(module, "plugin"):
                        plugin_instance = getattr(module, "plugin")
                        # 해당 객체가 우리가 코어에서 약속한 ServicePlugin 클래스를 상속받은 구현체인지 검사
                        if isinstance(plugin_instance, ServicePlugin):
                            self.plugins.append(plugin_instance)
                            logger.info(f"동적 서비스 플러그인 로드 성공: {plugin_instance.name}")
                except Exception as e:
                    logger.error(f"모듈 {module_name} 에서 서비스 플러그인을 로드하는 데 실패했습니다: {e}")

    def get_handler_for_payload(self, payload: Dict[str, Any]) -> Optional[ServicePlugin]:
        """
        [동적 라우팅] 유입된 웹훅 페이로드를 읽고, 자격이 있는 첫 번째 서비스 플러그인을 즉석에서 검색합니다.
        
        Args:
            payload: 외부 웹훅 서버로부터 들어온 원본 페이로드 데이터
        Returns:
            해당 웹훅을 처리하겠다고 승인한(can_handle이 참인) 서비스 플러그인 인스턴스 (없으면 None)
        """
        for plugin in self.plugins:
            # 개별 플러그인의 처리 자격 검증 함수를 순차 기동
            if plugin.can_handle(payload):
                return plugin
        return None

# 전역에서 손쉽게 가져다 쓸 수 있도록 플러그인 매니저 싱글톤 인스턴스화
plugin_manager = PluginManager()
