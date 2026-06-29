# 저장소 프로바이더 설정 가이드

AI Agent Core는 **GitLab** 또는 **GitHub** 중 하나를 저장소·웹훅 소스로 사용합니다.  
한 인스턴스당 **하나만** 선택합니다 (`REPOSITORY_PROVIDER`).

> **참고**: 저장소 API 어댑터 연동은 **코어 3**에서 구현됩니다.  
> 본 가이드는 `.env`에 무엇을 준비해야 하는지, 웹훅을 어떻게 등록하는지 안내합니다.

---

## 1. 빠른 시작 체크리스트

### 공통 (필수)

- [ ] `.env.example`을 복사해 `.env` 생성
- [ ] `REPOSITORY_PROVIDER` 선택 (`gitlab` 또는 `github`)
- [ ] `WEBHOOK_SECRET` 생성 (운영 환경 권장)
- [ ] `GET /health`로 `repository_configured` 확인

### GitLab 선택 시

- [ ] `GITLAB_URL` 설정
- [ ] `GITLAB_TOKEN` 발급 (`api` scope)
- [ ] GitLab Project/Group Webhook 등록

### GitHub 선택 시

- [ ] `GITHUB_BASE_URL` 설정
- [ ] `GITHUB_ACCESS_TOKEN` 발급 (`repo`, PR 쓰기 권한)
- [ ] GitHub Repository Webhook 등록

---

## 2. 기동 모드 (`STARTUP_MODE`)

| 모드 | 동작 |
|------|------|
| `lenient` (기본) | 토큰이 없어도 서버 기동. `/health`에 `repository_configured: false` 표시. **코어 개발·테스트용** |
| `strict` | 선택한 프로바이더의 필수 env가 없으면 **서버 기동 불가**. **운영·실연동용** |

운영 배포 시:

```env
STARTUP_MODE=strict
REPOSITORY_PROVIDER=gitlab   # 또는 github
```

---

## 3. GitLab 설정

### 3-1. 필요한 환경 변수

| 변수 | 필수 | 예시 | 설명 |
|------|------|------|------|
| `REPOSITORY_PROVIDER` | ✅ | `gitlab` | 프로바이더 선택 |
| `GITLAB_URL` | ✅ | `https://gitlab.com` | SaaS 또는 Self-hosted URL |
| `GITLAB_TOKEN` | ✅ | `glpat-...` | Personal/Project Access Token |
| `WEBHOOK_SECRET` | 권장 | 임의 문자열 | 웹훅 검증용 |
| `GITLAB_DEFAULT_PROJECT_ID` | 선택 | `105` | 단일 프로젝트 고정 시 |

`.env` 예시:

```env
STARTUP_MODE=strict
REPOSITORY_PROVIDER=gitlab
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-xxxxxxxx
WEBHOOK_SECRET=my-secret-token
```

### 3-2. Access Token 발급

1. GitLab → **User Settings** → **Access Tokens** (또는 Project → Settings → Access Tokens)
2. Token name: `ai-agent-core`
3. Scopes: **`api`** (MR diff 조회, 코멘트 작성)
4. 생성된 토큰을 `GITLAB_TOKEN`에 저장

Self-hosted GitLab이면 `GITLAB_URL`을 사내 URL로 변경합니다.

### 3-3. Webhook 등록

1. Project → **Settings** → **Webhooks**
2. **URL**: `https://{your-server}/webhook/gateway`
3. **Secret token**: `WEBHOOK_SECRET`과 **동일한 값**
4. **Trigger events**: Merge request events, Push events
5. **Enable SSL verification**: HTTPS 사용 시 활성화

검증 헤더 (코어 1-A):

- GitLab 기본: `X-Gitlab-Token`
- 공통: `X-Webhook-Secret` (동일 secret 값)

### 3-4. 테스트 페이로드 (Merge Request)

```bash
curl -X POST http://localhost:8000/webhook/gateway \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: my-secret-token" \
  -d '{
    "object_kind": "merge_request",
    "project": { "id": 105, "path_with_namespace": "group/project" },
    "object_attributes": { "iid": 12, "source_branch": "feature/test" }
  }'
```

---

## 4. GitHub 설정

### 4-1. 필요한 환경 변수

| 변수 | 필수 | 예시 | 설명 |
|------|------|------|------|
| `REPOSITORY_PROVIDER` | ✅ | `github` | 프로바이더 선택 |
| `GITHUB_BASE_URL` | ✅ | `https://api.github.com` | SaaS 또는 Enterprise API URL |
| `GITHUB_ACCESS_TOKEN` | ✅ | `ghp_...` | Personal Access Token |
| `WEBHOOK_SECRET` | 권장 | 임의 문자열 | 웹훅 Secret |
| `GITHUB_DEFAULT_REPO` | 선택 | `owner/repo` | 기본 저장소 |

`.env` 예시:

```env
STARTUP_MODE=strict
REPOSITORY_PROVIDER=github
GITHUB_BASE_URL=https://api.github.com
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxx
WEBHOOK_SECRET=my-secret-token
GITHUB_DEFAULT_REPO=myorg/myrepo
```

### 4-2. Access Token 발급

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens**
2. Fine-grained 또는 Classic token 생성
3. 권한:
   - **Contents**: Read (diff 조회)
   - **Pull requests**: Read and write (리뷰 코멘트)
   - 또는 Classic: **`repo`** scope

GitHub Enterprise Server:

```env
GITHUB_BASE_URL=https://github.mycompany.com/api/v3
```

### 4-3. Webhook 등록

1. Repository → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://{your-server}/webhook/gateway`
3. **Content type**: `application/json`
4. **Secret**: `WEBHOOK_SECRET`과 **동일한 값**
5. **Events**: Pull requests, Pushes

> **참고**: GitHub `X-Hub-Signature-256` HMAC 검증은 **코어 3** 어댑터 단계에서 추가됩니다.  
> 현재는 `X-Webhook-Secret` 헤더로 검증할 수 있습니다.

### 4-4. 테스트 페이로드 (Pull Request)

```bash
curl -X POST http://localhost:8000/webhook/gateway \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: my-secret-token" \
  -d '{
    "action": "opened",
    "pull_request": { "number": 42, "head": { "ref": "feature/test" } },
    "repository": { "full_name": "owner/repo" }
  }'
```

---

## 5. 설정 확인

서버 기동 후:

```bash
curl http://localhost:8000/health
```

응답 예시 (설정 미완료):

```json
{
  "status": "healthy",
  "repository_provider": "gitlab",
  "repository_configured": false,
  "repository_missing_fields": ["GITLAB_TOKEN"],
  "startup_mode": "lenient",
  "setup_guide": "docs/setup/repository_provider_guide.md"
}
```

응답 예시 (설정 완료):

```json
{
  "repository_provider": "gitlab",
  "repository_configured": true,
  "repository_missing_fields": [],
  "startup_mode": "strict"
}
```

---

## 6. 자주 묻는 질문

### Q. GitLab과 GitHub를 동시에 쓸 수 있나요?

한 인스턴스당 **하나만** 선택합니다. 둘 다 필요하면 인스턴스를 분리하세요.

### Q. 토큰 없이 코어만 개발하려면?

```env
STARTUP_MODE=lenient
REPOSITORY_PROVIDER=gitlab
# GITLAB_TOKEN 비워 둠
```

서버는 기동되며, 저장소 API 호출은 코어 3 이후에만 동작합니다.

### Q. strict 모드에서 기동이 안 됩니다

로그에 `누락: GITLAB_TOKEN` 등이 표시됩니다. 위 체크리스트대로 `.env`를 채운 뒤 재시작하세요.

---

## 7. 다음 단계 (로드맵)

| 단계 | 내용 |
|------|------|
| 코어 1 ✅ | config 검증, `/health` 설정 상태 |
| 코어 2 ✅ | LLM 프로바이더 선택·API 키·모델명 |
| 코어 3 ✅ | GitLab/GitHub API 어댑터 + 페이로드 정규화 |
| 코어 4 | DB 감사 로그 |
| 이후 | services/plugins 실구현 확장 |
