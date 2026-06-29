import pytest

from core.provider.llm import BaseLLMProvider, LLMError
from core.utils.retry import async_retry

pytestmark = pytest.mark.asyncio


# =====================================================================
# JSON 파싱 방어 로직 검증 (LLM이 코드펜스/잡텍스트를 섞어 보내는 케이스)
# =====================================================================

def test_parse_plain_json():
    assert BaseLLMProvider._parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_with_code_fence():
    raw = '```json\n{"summary": "ok", "issues": []}\n```'
    parsed = BaseLLMProvider._parse_json(raw)
    assert parsed["summary"] == "ok"
    assert parsed["issues"] == []


def test_parse_json_embedded_in_prose():
    raw = '리뷰 결과입니다:\n{"issues": [{"file": "a.py"}]}\n이상입니다.'
    parsed = BaseLLMProvider._parse_json(raw)
    assert parsed["issues"][0]["file"] == "a.py"


def test_parse_json_failure_raises():
    with pytest.raises(LLMError):
        BaseLLMProvider._parse_json("이건 JSON이 전혀 아닙니다")


# =====================================================================
# 지수 백오프 재시도 데코레이터 검증
# =====================================================================

async def test_async_retry_recovers_after_failures():
    calls = {"n": 0}

    @async_retry(max_attempts=3, base_delay=0.001)
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("일시 오류")
        return "성공"

    result = await flaky()
    assert result == "성공"
    assert calls["n"] == 3


async def test_async_retry_exhausts_and_raises():
    calls = {"n": 0}

    @async_retry(max_attempts=2, base_delay=0.001)
    async def always_fail():
        calls["n"] += 1
        raise ValueError("영구 오류")

    with pytest.raises(ValueError):
        await always_fail()
    assert calls["n"] == 2
