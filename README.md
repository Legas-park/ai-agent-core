# AI Agent Core

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> GitLab/GitHub 웹훅을 받아 **플러그인형 AI 에이전트 파이프라인**을 실행하는 오픈소스 코어 프레임워크

코어는 비즈니스 도메인을 모릅니다. 에이전트 생명주기, 워크플로우, GitLab/GitHub·LLM 연동 추상화, 동적 플러그인 로딩만 담당합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **플러그인 아키텍처** | `services/plugins/`에 폴더만 추가하면 자동 로드 |
| **저장소 추상화** | GitLab MR / GitHub PR을 동일 API로 처리 |
| **LLM 레지스트리** | Gemini, OpenAI, Anthropic, Local(Ollama 등) + fallback router |
| **웹훅 게이트웨이** | `POST /webhook/gateway` 단일 진입점 |
| **설정 진단** | `GET /health` — 저장소·LLM 설정 상태 확인 |
| **strict / lenient** | 운영(strict) vs 개발(lenient) 기동 정책 |

### 플러그인 상태

| 플러그인 | 상태 |
|----------|------|
| `code_review_service` | MR/PR diff → LLM 리뷰 → 코멘트 게시 |
| `doc_organizer_service` | experimental (스텁) |
| `error_autofix_service` | experimental (스텁) |

---

## 빠른 시작 (로컬 개발)

### 요구 사항

- Python 3.9+
- (선택) GitLab 또는 GitHub Access Token
- (선택) Gemini 또는 OpenAI API Key

### 설치

```bash
git clone https://github.com/Legas-park/ai-agent-core.git
cd ai-agent-core
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env 편집 — README 하단 "환경 변수" 참고
python main.py
```

서버: `http://localhost:8000`  
API 문서: `http://localhost:8000/docs`

### 설정 확인

```bash
curl http://localhost:8000/health | python -m json.tool
```

---

## 환경 변수

`.env.example`을 참고하세요. 핵심 항목:

| 변수 | 설명 |
|------|------|
| `STARTUP_MODE` | `lenient`(기본, 개발) / `strict`(운영, 설정 필수) |
| `REPOSITORY_PROVIDER` | `gitlab` 또는 `github` |
| `GITLAB_URL`, `GITLAB_TOKEN` | GitLab 연동 |
| `GITHUB_BASE_URL`, `GITHUB_ACCESS_TOKEN` | GitHub 연동 |
| `DEFAULT_LLM_PROVIDER` | `gemini`, `openai`, `anthropic`, `local` |
| `LLM_FALLBACK_PROVIDERS` | primary 실패 시 순서 (예: `gemini,local`) |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | OpenAI |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Anthropic (Claude) |
| `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL` | Local LLM (Ollama/vLLM, 예: qwen3.5) |
| `WEBHOOK_SECRET` | 웹훅 검증 (비우면 검증 생략) |

상세 가이드:

- [저장소 설정 (GitLab / GitHub)](docs/setup/repository_provider_guide.md)
- [LLM 설정](docs/setup/llm_provider_guide.md)

> **로드맵**: Docker Compose + PostgreSQL + Setup API로 설정을 DB에 저장하는 기능을 개발 중입니다.

---

## API

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 상태 및 설정 진단 |
| `POST` | `/webhook/gateway` | 통합 웹훅 (GitLab MR, GitHub PR 등) |

### 웹훅 예시 (GitLab MR)

```bash
curl -X POST http://localhost:8000/webhook/gateway \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: YOUR_WEBHOOK_SECRET" \
  -d '{
    "object_kind": "merge_request",
    "project": {"id": 105},
    "object_attributes": {"iid": 12, "title": "feat: API", "source_branch": "feature/x"}
  }'
```

---

## 프로젝트 구조

```
ai-agent-core/
├── main.py                 # FastAPI 진입점
├── config.py               # pydantic-settings
├── core/                   # 코어 (도메인 무지)
│   ├── agent/              # BaseAgent, AgentContext
│   ├── workflow/           # Orchestrator
│   ├── provider/           # LLM
│   ├── services/           # Repository 추상화 (GitLab/GitHub)
│   ├── setup/              # 설정 검증
│   └── integrations/       # REST 클라이언트
├── routers/webhook.py
├── services/plugins/       # 비즈니스 플러그인
├── tests/
└── docs/setup/             # 설정 가이드
```

---

## 새 플러그인 추가

1. `services/plugins/my_service/` 생성
2. `ServicePlugin` 구현 — `can_handle()`, `get_pipeline()`
3. `BaseAgent` 상속 — `process()`만 구현
4. `__init__.py`에 `plugin = MyPlugin()` export

자세한 예시는 [ARCHITECTURE.md](ARCHITECTURE.md) 및 기존 `code_review` 플러그인을 참고하세요.

---

## 테스트

```bash
pytest tests/ -v
```

로컬에서 위 명령으로 테스트를 실행합니다.

---

## 문서

| 문서 | 내용 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 아키텍처·데이터 흐름 |
| [core_features_guide.md](core_features_guide.md) | 5대 코어 기능 |
| [implementation_plan.md](implementation_plan.md) | 설계 배경 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 기여 방법 |
| [SECURITY.md](SECURITY.md) | 보안·시크릿 |

---

## 로드맵

- [x] 코어 프레임워크 + code_review 플러그인
- [x] GitLab / GitHub 저장소 어댑터
- [x] 설정 검증 + `/health`
- [x] LLM fallback router (primary + fallback chain)
- [x] Local LLM (Ollama OpenAI 호환 API)
- [ ] Docker Compose + PostgreSQL + Setup API
- [ ] agent_task / agent_step_log 감사 DB
- [ ] v0.1.0 public release

---

## 라이선스

[MIT License](LICENSE) — Copyright (c) 2026 legas

기여는 [CONTRIBUTING.md](CONTRIBUTING.md)를 따릅니다.
