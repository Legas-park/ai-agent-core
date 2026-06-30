"""
코어 경계 회귀 테스트 — 특정 플러그인/서비스명이 core/ 에 하드코딩되지 않았는지 검사.
"""

from pathlib import Path

FORBIDDEN_PLUGIN_REFS = (
    "services.plugins.code_review",
    "services.plugins.doc_organizer",
    "services.plugins.error_autofix",
    "from services.plugins",
)

FORBIDDEN_SERVICE_NAMES_IN_LOGIC = (
    "code_review_service",
    "doc_organizer_service",
    "error_autofix_service",
)

CORE_ROOT = Path(__file__).resolve().parent.parent / "core"


def _iter_core_py_files():
    for path in CORE_ROOT.rglob("*.py"):
        yield path


def test_core_does_not_import_services_plugins():
    violations = []
    for path in _iter_core_py_files():
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_PLUGIN_REFS:
            if forbidden in text:
                violations.append(f"{path.relative_to(CORE_ROOT.parent)}: {forbidden}")
    assert not violations, "core/ 가 services.plugins 를 import 합니다:\n" + "\n".join(violations)


def test_core_does_not_branch_on_plugin_service_names():
    """플러그인 식별명으로 분기하는 코드가 core에 없어야 합니다."""
    violations = []
    for path in _iter_core_py_files():
        if path.name == "plugin.py":
            continue
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN_SERVICE_NAMES_IN_LOGIC:
            if name in text:
                violations.append(f"{path.relative_to(CORE_ROOT.parent)}: {name}")
    assert not violations, "core/ 에 플러그인 서비스명 분기가 있습니다:\n" + "\n".join(violations)
