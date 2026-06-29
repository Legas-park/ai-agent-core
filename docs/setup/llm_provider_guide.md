# LLM 프로바이더 설정 가이드

AI Agent Core는 **Gemini(Google)** 또는 **OpenAI** 중 하나를 기본 LLM으로 사용합니다.  
한 인스턴스당 `DEFAULT_LLM_PROVIDER`로 **하나를 선택**하고, 해당 공급자의 **API 키**를 `.env`에 설정합니다.

---

## 1. 빠른 시작

```env
STARTUP_MODE=strict          # 운영: API 키 없으면 기동 불가
DEFAULT_LLM_PROVIDER=gemini  # 또는 openai

# Gemini 선택 시
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.0-flash

# OpenAI 선택 시
# DEFAULT_LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

기동 후 확인:

```bash
curl http://localhost:8000/health
```

---

## 2. 지원 모델 목록

### Gemini (`DEFAULT_LLM_PROVIDER=gemini`)

| 모델명 | 특징 |
|--------|------|
| `gemini-2.0-flash` | **기본 추천** — 빠르고 비용 효율적 |
| `gemini-2.0-flash-lite` | 더 가벼운 변형 |
| `gemini-1.5-flash` | 1.5 세대 경량 |
| `gemini-1.5-flash-8b` | 소형 |
| `gemini-1.5-pro` | 고품질·긴 컨텍스트 |

**API 키 발급**: [Google AI Studio](https://aistudio.google.com/apikey) → API key 생성 → `GEMINI_API_KEY`

### OpenAI (`DEFAULT_LLM_PROVIDER=openai`)

| 모델명 | 특징 |
|--------|------|
| `gpt-4o-mini` | **기본 추천** — 빠르고 저렴 |
| `gpt-4o` | 고성능 멀티모달 |
| `gpt-4-turbo` | 긴 컨텍스트 GPT-4 |
| `o1-mini` | 추론 특화 (경량) |
| `o3-mini` | 추론 특화 (차세대) |

**API 키 발급**: [OpenAI Platform](https://platform.openai.com/api-keys) → Create key → `OPENAI_API_KEY`

---

## 3. 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `DEFAULT_LLM_PROVIDER` | ✅ | `gemini` 또는 `openai` |
| `GEMINI_API_KEY` | gemini 선택 시 | Google AI API 키 |
| `GEMINI_MODEL` | gemini 선택 시 | 위 Gemini 모델명 중 하나 |
| `OPENAI_API_KEY` | openai 선택 시 | OpenAI API 키 |
| `OPENAI_MODEL` | openai 선택 시 | 위 OpenAI 모델명 중 하나 |

> 선택한 공급자의 API 키만 있으면 됩니다. 다른 공급자 키는 비워도 됩니다.

---

## 4. 기동 모드

| `STARTUP_MODE` | LLM 키 없을 때 |
|----------------|----------------|
| `lenient` (기본) | 경고 후 기동, LLM 단계는 드라이런 |
| `strict` | **기동 불가** — 선택한 공급자 API 키 필수 |

---

## 5. 코드에서 사용

```python
from core.provider.registry import llm_registry

provider = llm_registry.get_default()
if provider:
    text = await provider.complete("프롬프트", system="시스템 지시")
    data = await provider.complete_json("JSON으로 답하세요")
```

---

## 6. 문제 해결

### `repository_configured`는 true인데 LLM이 동작하지 않음

`/health`의 `llm_configured`를 확인하세요. `false`이면 API 키 또는 모델명이 잘못되었습니다.

### 모델명 오류

`llm_missing_fields`에 지원 목록이 표시됩니다. 위 **지원 모델 목록**과 정확히 일치해야 합니다.

### strict 모드 기동 실패

로그에 `GEMINI_API_KEY` 또는 `OPENAI_API_KEY` 누락 메시지가 나옵니다. `.env`를 채운 뒤 재시작하세요.
