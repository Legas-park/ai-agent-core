# 회사 교체 Cutover 체크리스트

사내 code_review → OSS `ai-agent-core` 전환 시 사용합니다.

---

## Phase 0 — 준비

- [ ] GitHub E1 완료 (개인 PR 리뷰 코멘트 확인)
- [ ] [company-gap-analysis.md](./company-gap-analysis.md) 1차 작성
- [ ] `.env.gitlab.company.example` 기준 회사 `.env` 준비
- [ ] GitLab PAT (`api` scope) 발급
- [ ] webhook 수신 URL 확정 (HTTPS)

---

## Phase 1 — 병렬 운영 (권장)

- [ ] OSS 인스턴스 기동 (`strict` + `/health` OK)
- [ ] **테스트 프로젝트**에 GitLab webhook 등록 (운영 MR 전체 X)
- [ ] 테스트 MR 2~3건 — OSS vs 사내 버전 리뷰 품질 비교
- [ ] gap 항목 플러그인 수정 (`services/plugins/code_review/`)

---

## Phase 2 — 전환

- [ ] 운영 repo webhook URL을 OSS gateway로 변경 (또는 webhook 추가)
- [ ] 사내 구버전 webhook **비활성화** (중복 리뷰 방지)
- [ ] 첫 운영 MR 모니터링 (`logs/app.log`, GitLab 코멘트)

---

## Phase 3 — 롤백 조건 (즉시 사내 버전 복귀)

- [ ] webhook 5xx 지속
- [ ] LLM/API 장애로 코멘트 미게시 30분+
- [ ] 리뷰 품질 critical regression

롤백:

1. GitLab webhook → 사내 URL 복원
2. OSS 인스턴스 중지 또는 webhook disable
3. gap 문서에 incident 기록

---

## Phase 4 — 완료

- [ ] 1주일 운영 MR N건 정상 처리
- [ ] gap-analysis 결론 **go**
- [ ] (선택) 이력서 지표 갱신 — [resume-bullets.md](../resume/resume-bullets.md)
