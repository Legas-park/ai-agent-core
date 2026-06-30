# 코어 / 플러그인 경계

AI Agent Core는 **도메인에 무지(domain-agnostic)** 합니다.  
코드 리뷰, 문서화, 관제, Slack 알림 등 **비즈니스 의미**는 전부 `services/plugins/` 에만 존재합니다.

---

## 코어가 아는 것

| 영역 | 역할 | 대표 경로 |
|------|------|-----------|
| 웹훅 게이트웨이 | JSON 수신, 서명 검증, 플러그인 라우팅 | `routers/webhook.py` |
| 플러그인 SPI | `can_handle` → 파이프라인 조립 | `core/plugin.py`, `core/plugin_manager.py` |
| 오케스트레이터 | 에이전트 순차 실행, 타임아웃, 취소 | `core/workflow/orchestrator.py` |
| LLM 레지스트리 | 프로바이더 등록, fallback router | `core/provider/` |
| 저장소 레지스트리 | GitLab/GitHub MR·PR 공통 API | `core/services/` |
| 횡단 연동 | GitLab 클라이언트 등 **2개 이상**이 쓸 때만 | `core/integrations/` |
| 부트스트랩 설정 | DB URL, 암호화 키, strict/lenient | `config.py` |

코어는 **“어떤 웹훅이 어떤 플러그인으로 갈지”** 와 **“에이전트 파이프라인을 어떻게 실행할지”** 만 압니다.

---

## 코어가 모르는 것

- 특정 플러그인 이름 (`code_review`, `service_monitor` 등)
- MR diff 리뷰 규칙, 프롬프트, Slack 메시지 형식
- 모니터링 대상 URL, 로그 수집 방식
- 플러그인 전용 env (`MONITOR_*`, `CODE_REVIEW_*` 등)

---

## 플러그인 작성 규칙

1. **위치**: `services/plugins/{plugin_name}/`
2. **진입점**: `__init__.py` 에 `plugin = YourPlugin()` 전역 변수
3. **구현**: `ServicePlugin` 상속 — `name`, `can_handle`, `get_pipeline`
4. **에이전트**: `agents/` 하위, `BaseAgent.process` 구현
5. **외부 의존**:
   - LLM → `llm_registry.get_default()`
   - Git MR/PR → `service_registry.get("repository")`
   - 플러그인 전용 설정 → 플러그인 README 또는 플러그인 내부 config 모듈 (코어 `config.py` X)

### 디렉터리 예시

```
services/plugins/my_service/
├── __init__.py      # plugin = MyServicePlugin()
├── agents/
│   └── worker.py
└── README.md        # 플러그인 전용 env·웹훅 형식
```

`_` 로 시작하는 폴더(예: `_scratch`)는 **런타임 자동 로드에서 제외**됩니다.

---

## merge 전 체크리스트 (하드코딩 방지)

새 플러그인 또는 코어 변경 PR마다 확인:

- [ ] `config.py` / `main.py`에 **서비스 이름·도메인 env** 가 추가되지 않았는가?
- [ ] `core/` 변경 이유가 아래 중 하나인가?
  - (a) SPI·오케스트레이터·registry **버그 수정**
  - (b) **2개 이상** 플러그인이 쓰는 generic integration 추출
  - (c) 보안·안정성 (웹훅 서명, timeout 등)
- [ ] 비즈니스 로직이 `services/plugins/` 밖에 없는가?
- [ ] 2번째 이후 플러그인 추가 시 **`git diff main -- core/`** 가 비어 있거나, generic 추출 근거가 PR에 적혀 있는가?

---

## 검증 (자동)

- `tests/test_plugin_spi.py` — fixture 더미 플러그인으로 SPI end-to-end
- `tests/test_core_boundary.py` — `core/` 소스에 특정 플러그인명 하드코딩 없음

---

## 향후 plugins 후보 (계획 고정 아님)

아래는 **예시**이며, 구현 시점·내용은 불편이 생길 때 `services/plugins/` 에만 추가합니다.

| 후보 | 도메인 | 비고 |
|------|--------|------|
| code_review | GitLab MR / GitHub PR | 1번째 검증 플러그인 (이미 존재) |
| 경량 관제 | HTTP 헬스 + 장애 시 로그 요약 + Slack | Grafana 대체가 아닌 **필요 서비스 목록** 중심 |
| doc_organizer | main push 문서 갱신 | experimental 스텁 |
| error_autofix | CI 실패 분석 | experimental 스텁 |

---

## 관련 문서

- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [core_features_guide.md](../../core_features_guide.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
