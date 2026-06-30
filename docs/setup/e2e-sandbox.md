# E1 실연동 — Sandbox 방식 (본 repo 오염 방지)

`ai-agent-core` 본 저장소에 테스트 PR·webhook 실험을 남기지 않기 위한 **분리 운영** 가이드입니다.

---

## 왜 Sandbox repo?

| 본 repo (`ai-agent-core`) | Sandbox repo |
|---------------------------|--------------|
| 엔진 소스·문서 | webhook + 테스트 PR **만** |
| PR은 기능 개발용 | 아무 파일이나 수정해도 OK |
| webhook 실패 delivery가 쌓이면 지저분 | 본 repo Settings 영향 없음 |

**Sandbox:** https://github.com/Legas-park/ai-agent-core-e2e-sandbox

---

## 1. 로컬 `.env` 준비 (1회)

```bash
./scripts/prepare_e2e_env.sh
```

- `.env` 생성 (gitignore — **커밋 안 됨**)
- `WEBHOOK_SECRET` 자동 생성 → 출력된 값 메모
- `GITHUB_DEFAULT_REPO=Legas-park/ai-agent-core-e2e-sandbox`

`.env`에 **직접 입력** (3개):

```env
GITHUB_ACCESS_TOKEN=glpat_... 또는 ghp_...
GEMINI_API_KEY=...
GEMINI_MODEL=...
```

---

## 2. 서버 + health

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

다른 터미널:

```bash
python3 scripts/check_health.py --strict
```

---

## 3. ngrok (Mac → GitHub)

```bash
brew install ngrok/ngrok/ngrok   # 1회
ngrok config add-authtoken <TOKEN>   # ngrok.com 1회
ngrok http 8000
```

`https://xxxx.ngrok-free.app` URL 복사.

---

## 4. Webhook — Sandbox repo에만 등록

**본 repo (`ai-agent-core`)가 아니라 sandbox에 등록:**

1. https://github.com/Legas-park/ai-agent-core-e2e-sandbox/settings/hooks
2. **Add webhook**
3. URL: `https://{ngrok-url}/webhook/gateway`
4. Secret: `prepare_e2e_env.sh` 출력값 (= `.env` `WEBHOOK_SECRET`)
5. Events: **Pull requests** only

---

## 5. 테스트 PR — Sandbox에서만

```bash
# sandbox clone (본 repo와 별도 폴더 권장)
cd ~/workspace
git clone https://github.com/Legas-park/ai-agent-core-e2e-sandbox.git
cd ai-agent-core-e2e-sandbox
git checkout -b test/webhook-e2e
echo "# E2E test $(date +%Y-%m-%d)" >> README.md
git commit -am "test: webhook E2E"
git push -u origin HEAD
gh pr create --title "test: E2E webhook" --body "sandbox PR"
```

확인:

- GitHub Webhook **Recent Deliveries** → 200
- Sandbox PR **Comments** → AI 리뷰
- 본 repo `ai-agent-core` — **변경 없음**

---

## 6. 로컬만 먼저 (ngrok 없이)

서버 실행 중:

```bash
source .env 2>/dev/null || true
python3 scripts/simulate_github_pr_webhook.py \
  --repo Legas-park/ai-agent-core-e2e-sandbox --pr 1
```

---

## 정리

- **맥:** `ai-agent-core` 서버 1개
- **GitHub:** sandbox repo 1개 (webhook + PR)
- **본 repo:** 소스만, 테스트 흔적 없음
- **`.env`:** 로컬만, git 제외

회사 GitLab 전환: [company-deploy.md](../migration/company-deploy.md)
