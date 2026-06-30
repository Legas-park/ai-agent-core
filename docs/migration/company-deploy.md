# 회사 GitLab 배포 가이드 (E1-b)

GitHub 개인 E1 검증 후, 회사 GitLab MR에 동일 엔진을 붙이는 방법입니다.

---

## 1. env 전환

```bash
cp .env.gitlab.company.example .env
```

| 변수 | 설명 |
|------|------|
| `REPOSITORY_PROVIDER` | `gitlab` |
| `GITLAB_URL` | `https://gitlab.com` 또는 Self-hosted URL |
| `GITLAB_TOKEN` | `api` scope PAT |
| `WEBHOOK_SECRET` | GitLab webhook Secret token 과 동일 |
| LLM 변수 | GitHub E1과 동일하게 유지 가능 |

`STARTUP_MODE=strict` 권장.

검증:

```bash
python3 scripts/check_health.py --strict
```

---

## 2. 서버 배포 옵션

### A. 개인/사내 Mac + VPN + ngrok (PoC)

GitHub E1과 동일. GitLab SaaS가 webhook URL에 도달 가능해야 합니다.

### B. docker compose (권장 PoC+)

```bash
cp .env.gitlab.company.example .env
# CONFIG_ENCRYPTION_KEY 생성 후 .env에 추가 (installation_guide 참고)
docker compose up --build
```

자세히: [installation_guide.md](../setup/installation_guide.md)

### C. 사내 VM / K8s

- 포트 8000 (또는 리버스 프록시) 공개
- GitLab → `https://{host}/webhook/gateway`

---

## 3. GitLab Webhook

1. Project → **Settings** → **Webhooks**
2. URL: `https://{host}/webhook/gateway`
3. Secret token: `WEBHOOK_SECRET`
4. Trigger: **Merge request events**
5. Save

로컬 시뮬레이션 (GitLab MR payload):

```bash
curl -X POST http://127.0.0.1:8000/webhook/gateway \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: $WEBHOOK_SECRET" \
  -d '{
    "object_kind": "merge_request",
    "project": {"id": 105, "path_with_namespace": "group/project"},
    "object_attributes": {"iid": 1, "title": "test", "source_branch": "feat/x"}
  }'
```

---

## 4. GitHub ↔ GitLab 차이 (코드 변경 없음)

| | GitHub | GitLab |
|---|--------|--------|
| env | `REPOSITORY_PROVIDER=github` | `REPOSITORY_PROVIDER=gitlab` |
| webhook 헤더 | `X-Hub-Signature-256` | `X-Gitlab-Token` |
| 이벤트 | PR | MR |

한 프로세스당 **하나의 provider** 만 active. 전환 시 `.env` 수정 후 **재기동**.

---

## 5. 관련 문서

- [cutover-checklist.md](./cutover-checklist.md)
- [company-gap-analysis.md](./company-gap-analysis.md)
- [repository_provider_guide.md](../setup/repository_provider_guide.md)
