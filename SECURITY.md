# 보안 정책

## 지원 버전

| 버전   | 지원      |
|--------|-----------|
| latest | ✅        |

## 취약점 제보

보안 취약점은 **공개 Issue 대신** 아래로 연락해 주세요.

- GitHub Security Advisories (저장소 활성화 후 **Report a vulnerability**)
- 또는 저장소 Maintainer에게 비공개 연락

제보 시 포함해 주세요:

- 재현 방법
- 영향 범위
- 가능하면 PoC

## 시크릿 처리 원칙

| 항목 | 규칙 |
|------|------|
| `.env` | **절대 커밋 금지** (`.gitignore` 적용됨) |
| API 키 / GitLab·GitHub 토큰 | 환경 변수 또는 (향후) Setup API + DB 암호화 저장 |
| `WEBHOOK_SECRET` | 운영 환경에서 반드시 설정 |
| 로그 | API 키·토큰이 로그에 출력되지 않도록 주의 |

## 운영 권장 사항

- `STARTUP_MODE=strict`로 기동 — 저장소·LLM 설정 없이 서비스가 뜨지 않게
- 웹훅 URL은 HTTPS 사용
- CORS: 프로덕션에서는 `allow_origins=["*"]` 대신 허용 도메인만 지정 (향후 env 분리 예정)
- Docker 배포 시 `CONFIG_ENCRYPTION_KEY` 백업 (DB 암호화 키 — Phase 2 이후)

## 알려진 제한

- 현재 설정은 주로 `.env` 기반입니다. DB·Setup API 기반 설정은 로드맵에 포함되어 있습니다.
- `WEBHOOK_SECRET`이 비어 있으면 웹훅 서명 검증이 **비활성화**됩니다 (로컬 개발용).
