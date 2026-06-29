# 도메인을 모르는 코어로 멀티 에이전트 자동화를 짓다 — AI Agent Core 설계기

> GitLab MR 코드리뷰·문서화·에러 자동수정을 하나의 웹훅 게이트웨이 뒤에서 굴리는,
> 플러그인 기반 멀티 에이전트 오케스트레이션 프레임워크를 만들고 실제로 동작시키기까지.

---

## 1. 왜 또 프레임워크인가

사내 자동화는 보통 이렇게 자란다. 처음엔 "MR 올라오면 LLM이 코드리뷰 코멘트 달아주는 스크립트" 하나로 시작한다. 그다음 "main에 푸시되면 문서 갱신", "CI 깨지면 원인 분석" 같은 요구가 붙는다. 각각을 따로 만들면 **웹훅 수신·LLM 호출·재시도·로깅·타임아웃** 같은 뼈대 코드가 서비스마다 복붙된다. 도메인 로직(코드리뷰 규칙)과 인프라 로직(어떻게 안전하게 돌릴까)이 엉켜서, 새 기능 하나 추가할 때마다 전체를 건드리게 된다.

그래서 목표를 이렇게 잡았다.

> **코어는 비즈니스 도메인을 1도 몰라야 한다.** 코어가 아는 것은 오직 에이전트의 생명주기, 워크플로우 상태, 실행 흐름, 동적 라우팅뿐이다. "이게 GitLab 리뷰인지 위키 문서화인지"는 플러그인이 알아서 한다.

이 한 문장이 모든 설계 결정의 기준이 됐다.

---

## 2. 전체 구조 — 게이트웨이 / 코어 / 플러그인 3계층

```
외부 웹훅(GitLab, CI/CD)
        │
        ▼
┌───────────────────────────┐
│  Webhook Gateway          │  서명 검증 → 페이로드 분석 → 즉시 202 응답
└───────────────────────────┘
        │ can_handle() 매칭
        ▼
┌───────────────────────────┐
│  Agent Core (도메인 무지)  │  PluginManager · Orchestrator · BaseAgent
│                           │  AgentContext · LLM/Integration Registry
└───────────────────────────┘
        │ get_pipeline()
        ▼
┌───────────────────────────┐
│  Service Plugins          │  code_review · doc_organizer · error_autofix
│  (도메인 로직은 여기에만)  │
└───────────────────────────┘
```

핵심은 **의존성 방향이 항상 플러그인 → 코어 한 방향**이라는 것. 코어 코드에는 `import gitlab` 같은 게 단 한 줄도 없다. 새 서비스를 추가할 때 코어를 절대 수정하지 않는다 — 이게 깨지면 설계가 실패한 것이다.

---

## 3. 설계 결정과 트레이드오프

### 3.1 제네릭 컨텍스트 vs 타입 안전성

에이전트 사이에 데이터를 어떻게 넘길까? 처음엔 `mr_iid`, `git_diff` 같은 필드를 가진 구체 모델을 생각했지만, 그러면 코어가 도메인을 알게 된다. 그래서 `AgentContext`를 동적 딕셔너리(`metadata`, `outputs`) 기반으로 만들었다.

```python
context.set_output("review_files", files)   # 1번 에이전트가 쓰고
files = context.get_output("review_files")   # 2번 에이전트가 읽는다
```

- **얻은 것**: 코어의 완전한 도메인 무지. 어떤 플러그인이든 자유롭게 키를 정의.
- **잃은 것**: 컴파일 타임 타입 체크. `outputs`의 키 오타는 런타임에야 드러난다.
- **완화책**: 플러그인 단위로 키 상수를 모아두고, 단위 테스트로 데이터 흐름을 고정했다.

LangGraph가 상태 스키마를 강하게 잡는 것과는 반대 방향의 선택이다. 코어를 얇게 유지하는 대가로 타입 안전성을 플러그인 책임으로 내렸다.

### 3.2 템플릿 메서드 패턴 — 개발자는 `process()`만 짠다

모든 에이전트는 `BaseAgent`를 상속하고 `process()` 하나만 구현한다. 취소 체크, 시작/완료 로깅, 예외 버블링, 히스토리 적재는 `run()` 래퍼가 일괄 처리한다.

```python
async def run(self, context):
    if context.is_cancelled:           # 공통: 실행 전 취소 감지
        raise Exception("TaskCancelled")
    await self.log_start(context)      # 공통: 시작 기록
    try:
        ctx = await self.process(context)   # 개발자가 짠 부분만 호출
        await self.log_complete(ctx)
        return ctx
    except Exception as e:
        self.log_error(context, str(e)) # 공통: 에러 기록 후 상위 전파
        raise
```

새 에이전트의 인지 부하가 "비즈니스 로직 한 메서드"로 줄어든다. 멀티 에이전트 시스템에서 에이전트 수가 늘수록 이 일관성이 복리로 이득이 된다.

### 3.3 선형 파이프라인 vs 그래프

오케스트레이터는 에이전트 리스트를 **순차 실행**한다. LangGraph 같은 조건부 그래프/분기는 일부러 넣지 않았다. 코드리뷰·문서화·에러수정 모두 "계획 → 실행"의 짧은 선형 흐름이라, 그래프 런타임의 복잡도가 과했다. 대신 안전장치에 집중했다:

- 각 에이전트마다 `asyncio.wait_for` **개별 타임아웃**(기본 300초)
- 앞 단계 에러/취소 플래그를 매 스텝 전에 검사해 **조기 중단**
- 메인 흐름을 막지 않는 **백그라운드 서브에이전트**(회고/분석용)

> 트레이드오프: 분기·루프·휴먼인더루프가 필요해지면 이 선형 모델로는 부족하다. 그 시점에 "파이프라인" 추상을 그래프로 승격하는 게 다음 과제다.

---

## 4. 목(mock)에서 실제 동작까지 — AI/LLM 엔지니어링의 본론

설계가 예뻐도 LLM을 진짜로 부르지 못하면 데모일 뿐이다. 초기 에이전트는 `["src/main.py"]`를 하드코딩해 리턴하는 껍데기였다. 이걸 실제로 GitLab MR을 읽고 LLM으로 분석해 코멘트를 다는 데까지 끌어올린 과정이 핵심이다.

### 4.1 LLM 프로바이더 추상화

에이전트가 특정 벤더 SDK에 묶이면 안 된다. `BaseLLMProvider` 인터페이스 하나에 Gemini/OpenAI 구현을 꽂고, 레지스트리에서 꺼내 쓴다.

```python
provider = llm_registry.get_default()        # gemini or openai
result = await provider.complete_json(prompt, system=SYSTEM_PROMPT)
```

벤더 교체가 설정 한 줄(`DEFAULT_LLM_PROVIDER`)이 됐다.

### 4.2 동기 SDK를 비동기 루프에서 안전하게

`requests`는 블로킹이다. FastAPI 이벤트 루프에서 그냥 부르면 전체가 멈춘다. 그래서 동기 HTTP 호출을 `asyncio.to_thread`로 감쌌다.

```python
async def complete(self, prompt, **kw):
    return await asyncio.to_thread(self._complete_sync, prompt, ...)
```

무거운 의존성 없이 비동기성을 지키는 실용적 선택이다.

### 4.3 구조화 출력 파싱 방어

LLM에게 "JSON만 응답하라"고 해도 현실은 ```` ```json ... ``` ````로 감싸거나 앞뒤에 설명을 붙인다. 그래서 파서가 코드펜스를 벗기고, 실패하면 본문에서 첫 JSON 블록만 잘라 재시도한다. 이 한 겹이 프로덕션 안정성을 좌우한다.

```python
def test_parse_json_embedded_in_prose():
    raw = '리뷰 결과입니다:\n{"issues": [{"file": "a.py"}]}\n이상입니다.'
    assert BaseLLMProvider._parse_json(raw)["issues"][0]["file"] == "a.py"
```

### 4.4 일시 장애를 흡수하는 재시도

LLM·GitLab API는 429/5xx/순단이 일상이다. 지수 백오프 + 지터 데코레이터로 일시 장애를 흡수하되, 마지막 시도까지 실패하면 원본 예외를 그대로 전파해 파이프라인이 "조용히 잘못된 결과"를 내지 않게 했다.

```python
@async_retry(max_attempts=3, retry_on=(requests.RequestException, LLMError))
async def get_mr_changes(self, project_id, mr_iid): ...
```

### 4.5 프롬프트는 "정확도 > 노이즈"로

코드리뷰 LLM의 최대 적은 **노이즈**다. 스타일 잔소리가 많으면 개발자가 봇을 꺼버린다. 그래서 시스템 프롬프트를 "확신 없으면 지적하지 마라, 버그·보안·성능·설계 결함에만 집중하라"로 못 박고, `severity`(critical/major/minor)·`category`를 구조화해 받아 마크다운으로 렌더링했다. 이는 단일 에이전트 리뷰의 한계를 보완하려는 업계 흐름(멀티 에이전트·룰 강제)과 같은 문제의식이다.

### 4.6 점진적 저하(graceful degradation)

키가 없어도 서버는 떠야 한다. LLM/GitLab이 미구성이면 해당 단계를 **건너뛰되 파이프라인은 끝까지 통과**하는 드라이런으로 동작한다. 덕분에 로컬 개발·CI에서 실제 API 없이도 전체 흐름을 검증할 수 있다.

```python
provider = llm_registry.get_default()
if provider is None:
    await self.log_info(context, "LLM 미구성: 분석 건너뜀(드라이런)")
    return context
```

### 4.7 웹훅 보안

게이트웨이는 `WEBHOOK_SECRET`이 설정된 경우 `X-Webhook-Secret`/`X-Gitlab-Token`을 **상수 시간 비교**(`hmac.compare_digest`)로 검증한다. 타이밍 공격 방어와 로컬 개발 편의(시크릿 비면 생략)를 동시에 챙겼다.

---

## 5. 검증 — 외부 의존성 없이 end-to-end 테스트

LLM/GitLab을 호출하지 않고도 파이프라인 전체를 검증하려고 가짜 프로바이더/클라이언트를 주입했다. "디프 수집 → LLM 분석 → MR 코멘트 게시"가 한 흐름으로 도는지, 삭제 파일이 걸러지는지, 드라이런이 죽지 않는지를 고정했다.

```python
llm_registry.providers = {"gemini": FakeProvider(...)}
integration_registry._clients = {"gitlab": FakeGitLab(...)}
final = await plugin.build_orchestrator(payload).run(context)
assert "AI 코드 리뷰" in fake_gitlab.posted[0]["body"]
```

코어 오케스트레이션(정상/에러중단/취소/타임아웃) 4종 + 신규 10종, 총 14개 테스트가 통과한다.

---

## 6. 비슷한 것들과의 위치 — 그래서 이건 뭐가 다른가

- **CodeRabbit·Greptile·Qodo** 같은 SaaS: 코드리뷰 "품질" 자체에 올인한 완성품. 우리 프로젝트는 리뷰 품질에서 이들과 경쟁하지 않는다.
- **PR-Agent**(오픈소스): 명령 디스패처 + 도구 계층으로 PR 분석에 특화. 단일 도메인(PR) 중심.
- **LangGraph·CrewAI·AutoGen**: 범용 에이전트 오케스트레이션. 강력하지만 "웹훅 수신 → 자동 라우팅 → 사내 서비스 실행"이라는 우리 사용 맥락에는 무겁다.

이 프로젝트의 자리는 그 사이다. **여러 도메인 서비스(리뷰+문서+에러수정)를 하나의 웹훅 게이트웨이 뒤에서, 코어 수정 없이 플러그인으로 꽂는** 자가호스팅 자동화 허브. 차별점은 멀티 도메인 플러그인 SPI와 도메인 무지 코어다. 동시에 솔직한 한계도 있다 — 상태 영속화·체크포인트(LangGraph 대비), 조건부 그래프, 관측성(트레이싱), 휴먼인더루프가 아직 없다. 이게 다음 로드맵(코어 1~4: 리포지토리 프로바이더 추상화 → GitHub 어댑터 → DB 영속화)의 동기다.

---

## 7. 회고

가장 값졌던 결정은 **"코어는 도메인을 모른다"는 제약을 끝까지 지킨 것**이다. 제약이 오히려 설계를 단순하게 만들었다. 가장 어려웠던 부분은 예쁜 추상화가 아니라, LLM의 들쭉날쭉한 출력과 외부 API의 일시 장애를 **프로덕션에서 견디게** 만드는 잔근육 — JSON 파싱 방어, 재시도, 점진적 저하, 비동기 격리 — 이었다. 결국 AI 제품의 신뢰성은 모델이 아니라 그 주변 엔지니어링에서 나온다는 걸 다시 확인했다.
