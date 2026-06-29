# 경쟁 분석 — AI Agent Core는 시장에서 어디에 있나

> 결론 먼저: **똑같은 제품은 없지만, 인접 영역은 두 갈래로 붐빈다.** (1) AI 코드리뷰 SaaS, (2) 범용 에이전트 오케스트레이션 프레임워크. 이 프로젝트는 그 사이의 빈 칸 — "멀티 도메인 서비스를 하나의 웹훅 게이트웨이 뒤에서 플러그인으로 꽂는 자가호스팅 자동화 허브" — 에 위치한다. 차별점도, 부족한 점도 거기서 나온다.

---

## 1. 비교군 A — AI 코드리뷰 제품 (가장 가까운 인접 시장)

| 제품 | 성격 | 강점 | 우리와의 관계 |
|------|------|------|--------------|
| **CodeRabbit** | 상용 SaaS | GitLab MR 1급 지원, 라인별 점진 리뷰, 대화형 UX. Lite $12 / Pro $24 per dev·월 | 리뷰 "품질·UX"의 완성품. 우리는 품질 경쟁 안 함 |
| **Greptile** | 상용 SaaS | 코드베이스 전체 맥락 이해, 아키텍처 영향 분석. 독립 벤치 버그 탐지율 82% | 정확도 기준점. 우리 리뷰 플러그인의 목표 상한 |
| **Qodo** (구 CodiumAI) | 상용 + OSS | 리뷰 + 테스트 생성 결합. Qodo 2.0(2026)에서 멀티 에이전트 리뷰 아키텍처 도입 | "멀티 에이전트 리뷰"라는 방향성이 우리와 같은 문제의식 |
| **PR-Agent** | 오픈소스 | 명령 디스패처(`/review`,`/improve`,`/ask`) + 도구 계층, GitHub/GitLab/Bitbucket 지원. PR 압축 전략 | 가장 구조적으로 닮은 OSS. 단, **단일 도메인(PR) 중심** |

**시사점**: 이들은 전부 "코드리뷰"라는 단일 도메인에 깊게 판다. 벤치마크(DORA 2025: 고성과 팀 버그탐지 42~48% 개선)도 코드리뷰 한정. 우리 프로젝트의 코드리뷰 플러그인은 이들과 품질로 정면승부하기 어렵고, 그럴 필요도 없다 — **리뷰는 여러 플러그인 중 하나**일 뿐이다.

---

## 2. 비교군 B — 에이전트 오케스트레이션 프레임워크

| 프레임워크 | 모델 | 강점 | 우리와의 관계 |
|-----------|------|------|--------------|
| **LangGraph** | 조건부 그래프(노드/엣지) | 체크포인트·타임트래블 상태 관리, 휴먼인더루프, 프로덕션 footprint 최대 | 우리가 의도적으로 안 쓴 무게. 상태 영속화는 우리의 부채 |
| **CrewAI** | 역할 기반 크루 | 프로토타이핑 진입장벽 최저 | 관측성·에러복구는 약함(우리와 비슷한 약점) |
| **AutoGen** | 대화형 에이전트(메시지 패싱) | 다자 토론·합의. 단, MS가 유지보수 모드로 전환 | 우리 사용 맥락(웹훅 자동화)과 결이 다름 |

**시사점**: 이들은 범용이라 강력하지만, "외부 웹훅을 받아 자동 라우팅하고 사내 서비스를 실행"하는 우리 시나리오엔 과하다. 우리는 그래프 런타임 대신 **얇은 선형 파이프라인 + 안전장치**를 택했다.

---

## 3. 그래서 뭐가 다른가 (차별점)

1. **멀티 도메인 플러그인 SPI**: 코드리뷰뿐 아니라 문서화·에러수정 등 이질적 서비스를 같은 코어로 굴린다. PR-Agent가 PR 한 도메인에 묶인 것과 대비.
2. **도메인 무지 코어 + 코어 수정 0줄 확장**: `pkgutil` 런타임 자동 탐색으로 폴더만 추가하면 새 서비스가 붙는다. 코어/도메인 결합도 제로.
3. **단일 웹훅 게이트웨이 + `can_handle()` 자동 라우팅**: 모든 이벤트가 한 엔드포인트로 들어와 적합 플러그인으로 분기.
4. **자가호스팅·벤더 중립**: LLM 프로바이더 추상화로 Gemini/OpenAI 교체가 설정 한 줄. 데이터가 외부 SaaS로 안 나간다(보안 민감 조직에 유리).

---

## 4. 솔직한 부족한 점 (Gap) — 다음 로드맵의 근거

| 부족한 점 | 누가 잘하나 | 우선순위 |
|----------|-----------|---------|
| **상태 영속화·체크포인트 부재** (지금은 인메모리, 서버 죽으면 진행 상태 소실) | LangGraph | 높음 (코어 4: DB 연동) |
| **조건부 분기/루프 없음** (선형 파이프라인만) | LangGraph | 중간 (파이프라인→그래프 승격) |
| **관측성·트레이싱 부재** (로그만 있고 분산 추적/대시보드 없음) | LangSmith류 | 중간 |
| **휴먼인더루프 없음** (승인·중간개입 흐름 미지원) | LangGraph/CrewAI | 중간 |
| **리뷰 품질 깊이** (코드베이스 전체 맥락·RAG 미적용) | Greptile/Qodo | 도메인 한정 |
| **단일 프로바이더 라우팅** (`can_handle` 첫 매칭만, 우선순위·복수 처리 없음) | — | 낮음 |
| **GitHub 등 멀티 SCM 미지원** (현재 GitLab 위주) | PR-Agent | 진행 예정 (코어 3: GitHub 어댑터) |

---

## 5. 한 줄 포지셔닝

> "코드리뷰 SaaS의 완성도"도 "LangGraph의 범용성"도 아닌, **사내 자동화를 코어 수정 없이 플러그인으로 늘려가는 자가호스팅 멀티 에이전트 허브.** 강점은 확장성과 벤더 중립, 부채는 상태 영속화와 관측성 — 둘 다 로드맵에 올라 있다.

---

## 출처 (Sources)

- [AI Code Review Tools for GitLab Merge Requests — Panto](https://www.getpanto.ai/blog/ai-code-review-tools-gitlab-merge-requests)
- [Best AI Code Review Tools 2026 — Greptile](https://www.greptile.com/content-library/best-ai-code-review-tools)
- [Qodo vs CodeRabbit (2026) — DEV](https://dev.to/rahulxsingh/qodo-vs-coderabbit-ai-code-review-tools-compared-2026-kdp)
- [Single-Agent vs Multi-Agent Code Review — Qodo](https://www.qodo.ai/blog/single-agent-vs-multi-agent-code-review/)
- [PR-Agent (오픈소스) — GitHub](https://github.com/The-PR-Agent/pr-agent)
- [PR-Agent Docs](https://docs.pr-agent.ai/)
- [LangGraph vs CrewAI vs AutoGen 2026 — DataCamp](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Multi-Agent Orchestration Frameworks 2026 — DEV](https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63)
