# LLM 프로바이더 설정 가이드

AI Agent Core는 **Gemini(Google)**, **OpenAI**, **Anthropic(Claude)** 중 하나를 기본 LLM으로 사용합니다.  
한 인스턴스당 `DEFAULT_LLM_PROVIDER`로 **하나를 선택**하고, 해당 공급자의 **API 키**와 **model id**를 `.env`에 설정합니다.

> **모델 ID는 하드코딩 목록이 없습니다.** 각 공급자 공식 문서에 나온 model id 문자열을 그대로 입력하세요.

---

## 1. 빠른 시작

```env
STARTUP_MODE=strict          # 운영: API 키 없으면 기동 불가
DEFAULT_LLM_PROVIDER=gemini  # gemini | openai | anthropic

# Gemini 선택 시
GEMINI_API_KEY=your-key
GEMINI_MODEL=<공급자-문서의-model-id>

# OpenAI 선택 시
# DEFAULT_LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=<공급자-문서의-model-id>

# Anthropic (Claude) 선택 시
# DEFAULT_LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=<공급자-문서의-model-id>
```

기동 후 확인:

```bash
curl http://localhost:8000/health
```

`/health` 응답의 `llm_model_doc_url`에서 현재 공급자의 model id 참고 문서 URL을 확인할 수 있습니다.

---

## 2. Model ID 입력 (공급자 문서 기준)

### Gemini (`DEFAULT_LLM_PROVIDER=gemini`)

| 항목 | 내용 |
|------|------|
| **API 키 발급** | [Google AI Studio](https://aistudio.google.com/apikey) → API key 생성 → `GEMINI_API_KEY` |
| **Model ID 문서** | [Gemini API Models](https://ai.google.dev/gemini-api/docs/models) |
| **env 변수** | `GEMINI_MODEL` — 문서에 나온 model id를 **그대로** 입력 |

새 모델이 출시되면 코드 수정 없이 문서의 model id만 바꿔 사용할 수 있습니다.

### OpenAI (`DEFAULT_LLM_PROVIDER=openai`)

| 항목 | 내용 |
|------|------|
| **API 키 발급** | [OpenAI Platform](https://platform.openai.com/api-keys) → Create key → `OPENAI_API_KEY` |
| **Model ID 문서** | [OpenAI Models](https://platform.openai.com/docs/models) |
| **env 변수** | `OPENAI_MODEL` — 문서에 나온 model id를 **그대로** 입력 |

### Anthropic Claude (`DEFAULT_LLM_PROVIDER=anthropic`)

| 항목 | 내용 |
|------|------|
| **API 키 발급** | [Anthropic Console](https://console.anthropic.com/settings/keys) → API key 생성 → `ANTHROPIC_API_KEY` |
| **Model ID 문서** | [Claude Models Overview](https://docs.anthropic.com/en/docs/about-claude/models/overview) |
| **env 변수** | `ANTHROPIC_MODEL` — 문서에 나온 model id를 **그대로** 입력 |

---

## 3. 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `DEFAULT_LLM_PROVIDER` | ✅ | `gemini`, `openai`, `anthropic` |
| `GEMINI_API_KEY` | gemini 선택 시 | Google AI API 키 |
| `GEMINI_MODEL` | gemini 선택 시 | Gemini API model id (공급자 문서 참고) |
| `OPENAI_API_KEY` | openai 선택 시 | OpenAI API 키 |
| `OPENAI_MODEL` | openai 선택 시 | OpenAI model id (공급자 문서 참고) |
| `ANTHROPIC_API_KEY` | anthropic 선택 시 | Anthropic API 키 |
| `ANTHROPIC_MODEL` | anthropic 선택 시 | Claude model id (공급자 문서 참고) |

> 선택한 공급자의 API 키만 있으면 됩니다. 다른 공급자 키는 비워도 됩니다.

---

## 4. 기동 모드

| `STARTUP_MODE` | LLM 키 없을 때 |
|----------------|----------------|
| `lenient` (기본) | 경고 후 기동, LLM 단계는 드라이런 |
| `strict` | **기동 불가** — 선택한 공급자 API 키·model id 필수 |

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

`/health`의 `llm_configured`를 확인하세요. `false`이면 API 키 또는 model id가 비어 있거나 형식이 잘못되었습니다.

### model id 오류 / API 404

- `llm_missing_fields`와 `llm_model_doc_url`을 확인하세요.
- 공급자 문서의 model id와 **완전히 동일한 문자열**인지 확인하세요 (대소문자·하이픈 포함).
- API 호출 실패는 카탈로그가 아니라 **공급자 API 응답**으로 확인합니다.

### strict 모드 기동 실패

로그에 `GEMINI_*`, `OPENAI_*`, `ANTHROPIC_*` 변수 누락 메시지가 나옵니다. `.env`를 채운 뒤 재시작하세요.
