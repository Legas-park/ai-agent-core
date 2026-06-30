# 사내 버전 vs OSS gap 분석 (초안)

> GitHub 개인 E1 검증 / 회사 GitLab 교체 전에 채워 넣는 체크리스트입니다.  
> 실제 MR·PR 테스트 후 항목별로 ✅ / ❌ / 메모를 기록하세요.

**작성일:** 2026-06-30  
**검증 환경:** GitHub `Legas-park/ai-agent-core` / GitLab (회사, 예정)  
**OSS 버전:** main @ E1 브랜치

### E1 자동 검증 (로컬, secret/API 없음)

| 항목 | 결과 |
|------|------|
| `/health` 기동 (lenient) | OK — plugins 3개 로드 |
| GitHub PR webhook 시뮬레이터 | OK — `code_review_service` accepted |
| pytest webhook HMAC | OK — 61 passed |

> **사용자 액션 남음:** `.env.github.example` → `.env` + PAT/LLM + ngrok + GitHub webhook + 실 PR

---

## 1. 기능 parity

| 항목 | 사내 버전 | OSS (ai-agent-core) | gap / 메모 |
|------|-----------|---------------------|------------|
| MR/PR webhook 트리거 | | | |
| diff 수집 | | | |
| LLM 구조화 리뷰 | | | |
| 코멘트 게시 형식 | | | |
| 대형 diff 처리 | | | |
| 파일 필터 (lock, binary 등) | | | |
| fallback LLM | | | |
| webhook secret 검증 | | | |

---

## 2. 리뷰 품질 (실측)

| PR/MR # | 노이즈 (과잉 지적) | 놓친 이슈 | 총평 |
|---------|-------------------|-----------|------|
| | | | |

---

## 3. 운영·배포

| 항목 | 사내 | OSS | gap |
|------|------|-----|-----|
| 기동 방식 (docker / uvicorn) | | | |
| env 관리 | | | |
| 로그 위치 | | | |
| 공개 URL / VPN | | | |

---

## 4. OSS에서만 수정할 파일 (코어 X)

gap 해결 시 우선 수정 위치:

- [`services/plugins/code_review/prompts.py`](../../services/plugins/code_review/prompts.py)
- [`services/plugins/code_review/agents/`](../../services/plugins/code_review/agents/)

---

## 5. 결론

- [ ] GitHub E1 통과 — PR 코멘트 자동 게시 확인
- [ ] GitLab E1-b 통과 — 회사 MR 동일
- [ ] 교체 go / no-go: ___________

**다음 액션:**

1. 
2. 
