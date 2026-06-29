# AI Agent 코어 프레임워크 핵심 기능 및 서비스 활용 가이드

본 가이드는 `ai-agent-core` 프로젝트의 **5대 핵심 기능(Core Features)**이 정확히 무엇인지 코드 레벨에서 명시하고, 우리가 분리하여 구현하는 **개별 비즈니스 서비스 플러그인(깃랩 코드 리뷰, 컨플루언스 자동화 등)**이 이 코어 기능들을 어떻게 활용(상속, 파이프 연동, 동적 바인딩)하는지 설명합니다.

---

## ⚙️ Part 1. 5대 핵심 코어 기능 정의

코어 엔진은 비즈니스 도메인(GitLab 주소, Gemini 프롬프트 내용 등)을 전혀 알지 못하며, 오직 **에이전트들의 생명 주기, 워크플로우 상태, 실행 흐름, 비동기 라우팅**만 통제합니다.

```
┌────────────────────────────────────────────────────────┐
│                   Unified Gateway                      │  1. 진입점 & 라우팅
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ (페이로드 분석)
┌────────────────────────────────────────────────────────┐
│                   Plugin Manager                       │  2. 동적 매칭 & 클래스 로딩
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ (에이전트 체인 조립)
┌────────────────────────────────────────────────────────┐
│                Workflow Orchestrator                   │  3. 순차/병렬 실행 엔진
└──────────────────────────┬─────────────────────────────┘
                           │
      ┌────────────────────┴────────────────────┐
      ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│  Base Agent  │ (4. 생명주기 통제)        │ AgentContext │ (5. 동적 변수 보관소)
└──────────────┘                          └──────────────┘
```

### 1. `BaseAgent` (에이전트의 공통 뼈대)
*   **파일 위치**: `core/agent/base_agent.py`
*   **정의**: 시스템 내의 모든 서비스에 탑재될 개별 에이전트 클래스들의 추상 조상입니다.
*   **제공하는 코어 기능**:
    *   **공통 실행 생명주기 관리**: 에이전트가 실행될 때 사전 캔슬 여부 체크, 실시간 로깅, 에러 예외처리를 하나의 래퍼 함수(`run()`)가 자동으로 처리하므로, 개발자는 `process()` 비즈니스 함수 내부 로직 개발에만 몰두하면 됩니다.
    *   **안전 비상 정지 (Cancellation)**: 사용자가 태스크 취소 신호를 보냈을 때 다음 동작을 진행하기 전에 이를 가로채 안전하게 실행 루프를 정지시킵니다.

### 2. `AgentContext` (유연한 상태 머신 데이터 캐리어)
*   **파일 위치**: `core/agent/context.py`
*   **정의**: 에이전트 파이프라인 전반을 거치며 흐르는 **동적 공유 변수 저장소**입니다.
*   **제공하는 코어 기능**:
    *   **도메인 독립적인 구조**: 특정 비즈니스 변수가 하드코딩되지 않고, 동적인 `metadata` 및 `outputs` 딕셔너리로 구성되어 어떤 형태의 입출력 데이터 규격도 즉시 탑재하고 전달할 수 있습니다.
    *   **실행 히스토리 트래킹**: 각 에이전트가 시작, 진행, 완료된 시간과 텍스트 요약을 자동으로 적재하여 나중에 실행 전체 과정을 한눈에 역추적할 수 있게 돕습니다.

### 3. `WorkflowOrchestrator` (순차/병렬 워크플로우 실행 엔진)
*   **파일 위치**: `core/workflow/orchestrator.py`
*   **정의**: 플러그인으로부터 주입받은 에이전트 리스트(Pipeline)를 기동하는 심장 엔진입니다.
*   **제공하는 코어 기능**:
    *   **제네릭 실행 루프**: 전달받은 에이전트 목록의 인스턴스를 하나씩 기동하며 `AgentContext` 상태를 앞쪽 에이전트에서 뒤쪽 에이전트로 차례대로 넘겨줍니다.
    *   **비동기 타임아웃 예외 제어**: 개별 에이전트의 무한 루프나 네트워크 락을 방지하기 위해 `asyncio.wait_for`로 감싸 특정 시간 초과 시 시스템이 안전하게 실패 처리를 하도록 돕습니다.
    *   **비동기 백그라운드 매니저**: 응답 시간을 단축하기 위해 메인 워크플로우를 방해하지 않고 백그라운드에서 별도로 돌아갈 서브 에이전트 실행을 제어합니다.

### 4. `PluginManager` & `ServicePlugin` (동적 로더 및 라우터)
*   **파일 위치**: `core/plugin.py`, `core/plugin_manager.py`
*   **정의**: 서비스 폴더를 자동 스캔하여 코어와 유기적으로 연결하는 접착 모듈입니다.
*   **제공하는 코어 기능**:
    *   **동적 로딩**: `importlib` 및 `pkgutil`을 사용하여 `services/plugins` 폴더의 모든 독립 플러그인을 자동으로 탐색하여 시스템 메모리에 탑재합니다.
    *   **다형성 조건 매칭**: 들어온 웹훅 페이로드를 가지고 각 플러그인에 `can_handle(payload)`를 질문하여 어떤 플러그인을 활성화할지 런타임에 최종 선별합니다.

### 5. `Unified Webhook Gateway` (단일 API 진입점)
*   **파일 위치**: `routers/webhook.py`, `main.py`
*   **정의**: 외부 서버(GitLab 등)로부터 들어오는 모든 요청을 받는 게이트웨이 컨트롤러입니다.
*   **제공하는 코어 기능**:
    *   **비동기 위임**: 페이로드를 해석해 적합한 플러그인을 골라낸 후, FastAPI의 `BackgroundTasks`에 오케스트레이터의 기동을 위임하여 웹훅 발송 측에 즉각 `HTTP 202 Accepted` 응답을 줍니다.

---

## 🧩 Part 2. 서비스 플러그인의 코어 기능 실무 활용 예시

우리가 설계한 **1) GitLab 코드 리뷰 서비스**와 **2) Confluence 문서화 서비스**가 위의 코어 기능들을 어떻게 상속받고 데이터를 흘려보내는지 예시 코드를 통해 설명합니다.

### 1. 코어 클래스 상속 (`BaseAgent` 활용)
에이전트 개발자는 생명주기 관리나 에러 처리를 따로 짤 필요가 없습니다. `BaseAgent`를 상속받은 뒤 `process` 비즈니스 실행 부문만 구현합니다.

```python
# [Confluence 위키 작성 에이전트의 예시]
from core.agent.base_agent import BaseAgent
from core.agent.context import AgentContext

class ConfluenceWikiAgent(BaseAgent):  # 1. 코어의 BaseAgent 상속
    async def process(self, context: AgentContext) -> AgentContext:
        # 2. 앞선 단계에서 만들어진 문서를 context에서 조회
        markdown_doc = context.get_output("document_markdown")
        doc_title = context.get_output("document_title")
        
        # 3. 코어가 제공하는 log_info로 로그 추적을 손쉽게 실행
        await self.log_info(context, f"Wiki 페이지 발행을 시작합니다: {doc_title}")
        
        # 4. 규격화된 Wiki API를 통해 컨플루언스 배포 (실구현 연동)
        wiki_url = await wiki_service.publish_page(doc_title, markdown_doc)
        
        # 5. 최종 발행 URL을 다시 컨텍스트에 담아 반환
        context.set_output("published_wiki_url", wiki_url)
        return context
```

### 2. 에이전트 간의 데이터 파이프 연동 (`AgentContext` 활용)
에이전트들이 서로 직접적으로 엉켜서 엮이지 않고, 오직 `AgentContext`의 `outputs`를 통해서만 데이터를 주고받습니다.

*   **깃랩 코드 리뷰 흐름 예시**:
    1.  `PlanningAgent`가 GitLab API를 통해 diff 데이터를 가져와 딕셔너리에 저장합니다.
        ```python
        context.set_output("git_diff", diff_data)
        ```
    2.  `CodeReviewAgent`가 다음 순서로 기동되면, 딕셔너리에서 키값을 읽어옵니다.
        ```python
        git_diff = context.get_output("git_diff")
        ```
에이전트끼리 상대방의 존재나 다음 단계 클래스명을 알 필요가 전혀 없으므로, 데이터 파이프라인의 조립과 순서 변경이 극도로 단순화됩니다.

### 3. 유연한 작업 결합 및 런타임 매칭 (`Orchestrator` & `PluginManager` 활용)
개발자가 코어 파일(`routers/webhook.py`나 `core/workflow/orchestrator.py` 등)을 전혀 손대지 않아도, 새 플러그인을 폴더에 배치하기만 하면 코어가 동적으로 감지하여 매핑합니다.

```text
1. GitLab에서 MR이 생성되어 웹훅 발송
2. 코어의 게이트웨이(/webhook/gateway)가 수신
3. 코어의 PluginManager가 전체 스캔 실행:
   - "code_review" 플러그인의 can_handle() 호출 ──> True 반환!
   - "doc_organizer" 플러그인의 can_handle() 호출 ──> False 반환!
4. 코어 게이트웨이가 GitLab 용 파이프라인 인스턴스 [PlanningAgent, CodeReviewAgent, GitLabReportAgent] 획득
5. 코어의 WorkflowOrchestrator가 에이전트 3개를 차례대로 비동기 실행 루프에 올림
```
