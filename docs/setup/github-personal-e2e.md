# GitHub 개인 연동 E2E 가이드 (E1)

개인 Mac에서 **GitHub PR webhook → code_review 플러그인**을 1차 검증하는 절차입니다.  
회사 GitLab 테스트 전에 이 문서 순서대로 진행하세요.

관련 문서:

- [repository_provider_guide.md](./repository_provider_guide.md) §4 GitHub
- [llm_provider_guide.md](./llm_provider_guide.md)
- [../architecture/plugin-boundary.md](../architecture/plugin-boundary.md)

---

## 0. 사전 준비

- Python 3.9+
- 이 저장소 clone (`Legas-park/ai-agent-core`)
- GitHub Personal Access Token (PAT)
- LLM API 키 1개 (Gemini / Anthropic / OpenAI 등)
- 공개 HTTPS URL용 **ngrok** 또는 **cloudflared** (아래 Step 3)

> **본 repo를 지저분하게 하지 않으려면** [e2e-sandbox.md](./e2e-sandbox.md) 방식(별도 sandbox repo)을 권장합니다.

---

## Step 1 — `.env` 작성

```bash
cp .env.github.example .env
```

`.env`에 채울 항목:

| 변수 | 설명 |
|------|------|
| `STARTUP_MODE` | `strict` (운영 연동) |
| `REPOSITORY_PROVIDER` | `github` |
| `GITHUB_ACCESS_TOKEN` | PAT — **repo** (classic) 또는 fine-grained **Contents read + Pull requests read/write** |
| `WEBHOOK_SECRET` | 임의 긴 문자열 (GitHub Webhook Secret 과 동일하게) |
| `GEMINI_API_KEY` + `GEMINI_MODEL` | 또는 다른 LLM 공급자 |

`.env`는 **절대 git에 커밋하지 마세요.**

---

## Step 2 — 서버 기동 및 `/health`

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

다른 터미널:

```bash
python3 scripts/check_health.py
python3 scripts/check_health.py --strict
```

`--strict` 성공 조건:

- `repository_configured: true`
- `llm_configured: true`
- `loaded_plugins`에 `code_review_service` 포함

---

## Step 3 — 공개 URL (ngrok / cloudflared)

GitHub webhook은 **인터넷에서 접근 가능한 HTTPS** URL이 필요합니다.

### 방법 A: ngrok (권장, 처음 사용자)

```bash
# macOS (Homebrew)
brew install ngrok/ngrok/ngrok

# ngrok.com 가입 후 authtoken 설정 (1회)
ngrok config add-authtoken <YOUR_TOKEN>

# 터미널 2 — 서버(8000) 실행 중인 상태에서
ngrok http 8000
```

출력의 `Forwarding https://xxxx.ngrok-free.app` URL을 복사합니다.

### 방법 B: cloudflared (ngrok 대안)

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8000
```

표시된 `https://*.trycloudflare.com` URL을 사용합니다.

---

## Step 4 — GitHub Repository Webhook

대상: `Legas-park/ai-agent-core` (또는 테스트 repo)

1. GitHub → repo **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://{공개URL}/webhook/gateway`
3. **Content type**: `application/json`
4. **Secret**: `.env`의 `WEBHOOK_SECRET`과 **동일**
5. **Events**: **Pull requests** 만 선택
6. **Add webhook**

Delivery 실패 시: Recent Deliveries 탭에서 HTTP 상태 코드 확인 (401 → Secret 불일치, 502 → ngrok/서버 중단).

---

## Step 5 — 테스트 PR

```bash
git checkout -b feat/e1-webhook-test
# README 등 작은 변경 1건
git commit -am "test: E1 GitHub webhook 검증"
git push -u origin HEAD
gh pr create --title "test: E1 webhook" --body "GitHub PR webhook E2E 테스트"
```

확인:

1. GitHub Webhook **Recent Deliveries** → `200`
2. `logs/app.log` → `Webhook routed to plugin: code_review_service`
3. PR **Comments** → AI 리뷰 코멘트

### 로컬만 먼저 확인 (ngrok 없이)

서버 실행 후:

```bash
WEBHOOK_SECRET=change-me-to-a-long-random-string python3 scripts/simulate_github_pr_webhook.py
```

`.env`의 `WEBHOOK_SECRET`과 동일하게 맞추세요.  
응답 `{"status":"accepted","task_id":"..."}` 이면 라우팅 OK (LLM/ GitHub API는 `.env` strict 설정 시 백그라운드에서 실행).

---

## Step 6 — 문제 해결

| 증상 | 확인 |
|------|------|
| 서버 기동 실패 (strict) | `check_health.py --strict` → missing_fields |
| Webhook 401 | `WEBHOOK_SECRET` 일치, GitHub HMAC 헤더 |
| Webhook 200 but 코멘트 없음 | PAT scope, PR files API, LLM 키, `logs/app.log` |
| ignored 응답 | PR event가 아님 — action이 `opened`/`synchronize` 인지 |

---

## Step 7 — 회사 GitLab으로 넘어가기

GitHub 검증 OK 후:

1. [company-deploy.md](../migration/company-deploy.md)
2. [cutover-checklist.md](../migration/cutover-checklist.md)
3. `cp .env.gitlab.company.example .env` 후 GitLab 값 입력

코어 코드 변경 없이 **env + webhook URL** 만 교체합니다.
