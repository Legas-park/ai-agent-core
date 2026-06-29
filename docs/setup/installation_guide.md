# 설치 가이드 (Docker)

AI Agent Core를 **설치형 제품**으로 띄우는 방법입니다.  
연동 설정(GitLab/GitHub, LLM)은 **Phase 3 Setup API**에서 DB에 저장합니다. 지금 단계에서는 **인프라(Postgres + 앱 + 마이그레이션)** 만 준비됩니다.

---

## 1. 사전 요구

- Docker + Docker Compose
- (선택) Git / 웹훅용 공개 URL — ngrok 등

---

## 2. 빠른 시작

```bash
cp .env.example .env
# CONFIG_ENCRYPTION_KEY 생성 후 .env에 붙여넣기 (아래 참고)

docker compose up --build
```

- 앱: http://localhost:8000
- Postgres: `localhost:5432` (user/pass/db: `agent` / `agent` / `agent_core`)
- 컨테이너 기동 시 `alembic upgrade head` 자동 실행

---

## 3. CONFIG_ENCRYPTION_KEY 생성

DB에 API 키·토큰을 암호화해 저장할 때 사용합니다.

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`.env`:

```env
CONFIG_ENCRYPTION_KEY=<생성된-키>
```

---

## 4. .env 역할 (설치형 vs 연동 설정)

| 구분 | .env (부트스트랩) | DB + Setup API (연동 설정) |
|------|-------------------|---------------------------|
| 목적 | **어떻게 실행할지** | **무엇에 연결할지** |
| 예시 | `DATABASE_URL`, `CONFIG_ENCRYPTION_KEY`, `STARTUP_MODE` | GitLab 토큰, LLM API 키, model id |
| 변경 | 재시작 필요 | API로 변경, 재시작 없이 반영(Phase 4) |

개발 중에는 `.env`의 `GITLAB_TOKEN`, `GEMINI_API_KEY` 등으로도 동작합니다(호환 기간).  
설치형 목표는 **시크릿을 DB로 옮기는 것**입니다.

---

## 5. DB 스키마 (초기)

| 테이블 | 역할 |
|--------|------|
| `repository_config` | 저장소 1건 (GitLab/GitHub) |
| `llm_provider_config` | LLM N건 (priority = primary/fallback) |
| `system_meta` | `setup_completed` 등 |

마이그레이션 수동 실행:

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_core \
  alembic upgrade head
```

---

## 6. 로컬 Python만 (Docker 없이)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
uvicorn main:app --reload
```

Postgres는 별도 설치하거나 `docker compose up postgres -d`만 실행해도 됩니다.

---

## 7. 다음 단계

1. **Phase 3** — `POST /api/setup/*` 로 저장소·LLM 등록
2. **Phase 4** — `main.py` lifespan이 DB 설정을 읽어 registry/router에 주입
3. `.env` 연동 키 → DB 1회 import 후 deprecated

가이드: [저장소 설정](repository_provider_guide.md) · [LLM 설정](llm_provider_guide.md)
