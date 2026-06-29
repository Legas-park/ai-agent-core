# AI Agent Core 외부 서비스 연동 및 입출력 규격서 (Standard Interfaces Spec)

본 규격서는 에이전트 코어 프레임워크와 외부 연동 서비스(GitLab, Slack, Confluence 등)가 서로 약속된 규칙에 따라 데이터와 연동을 처리할 수 있도록 보장하는 **입출력 데이터 모델** 및 **추상 서비스 인터페이스(Protocol)** 명세입니다.

---

## 🔌 1. 외부 연동 서비스의 추상 인터페이스화 (Interface Contracts)

에이전트는 깃랩 API나 슬랙 SDK를 직접 호출하지 않고, 코어가 등록한 아래의 추상 규격을 통해서만 외부와 연동합니다. 이를 통해 실제 연동 업체가 변경되어도 에이전트 코드는 전혀 수정할 필요가 없습니다.

```
                  ┌──────────────────────────────┐
                  │      서비스 에이전트 코드     │
                  └──────────────┬───────────────┘
                                 │ (추상 규격 호출)
                                 ▼
         ┌────────────────────────────────────────────────┐
         │     Core Service Registry (서비스 등록소)       │
         ├────────────────────────────────────────────────┤
         │  - RepositoryService (Base)                    │
         │  - WikiService (Base)                          │
         │  - NotificationService (Base)                  │
         └───────────────────────┬────────────────────────┘
                                 │ (런타임 구현체 주입)
                                 ▼
                  ┌──────────────────────────────┐
                  │    실제 연동 모듈 (어댑터)    │
                  ├──────────────────────────────┤
                  │  - GitLabService / GitHub    │
                  │  - Confluence / Notion       │
                  │  - SlackService / MS Teams   │
                  └──────────────────────────────┘
```

### 1) 저장소 연동 규격 (`BaseRepositoryService`)
*   **역할**: 코드 형상 관리 시스템(GitLab, GitHub 등)과의 diff 조회 및 코멘트 작성 규격입니다.

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseRepositoryService(ABC):
    @abstractmethod
    async def get_merge_request_diff(self, project_id: str, mr_iid: int) -> str:
        """
        Merge Request(또는 PR)의 변경 diff 전체 데이터를 획득합니다.
        
        Args:
            project_id: 프로젝트 경로 혹은 고유 ID
            mr_iid: 대상 MR의 일련번호
        Returns:
            Unified Diff 포맷의 텍스트 데이터
        """
        pass

    @abstractmethod
    async def post_mr_comment(self, project_id: str, mr_iid: int, comment: str) -> bool:
        """
        Merge Request의 특정 라인 혹은 전체 쓰레드에 리뷰 코멘트를 작성합니다.
        """
        pass
```

### 2) 위키/문서 연동 규격 (`BaseWikiService`)
*   **역할**: 사내 기술문서 보관소(Confluence, Notion 등)에 결과 보고서를 배포하는 규격입니다.

```python
class BaseWikiService(ABC):
    @abstractmethod
    async def publish_page(self, title: str, content_markdown: str, space_key: str, parent_page_id: str = None) -> str:
        """
        신규 Markdown 기반 테크 문서를 지정 공간에 위키 문서로 발행합니다.
        
        Args:
            title: 문서 제목
            content_markdown: 마크다운 형태의 문서 내용
            space_key: 위키 스페이스 키 (예: 'ESIGN')
        Returns:
            발행 완료된 위키 문서의 상세 URL 주소
        """
        pass
```

### 3) 알림 연동 규격 (`BaseNotificationService`)
*   **역할**: 메신저 채널(Slack, MS Teams, 잔디 등)로 에이전트 결과 혹은 시스템 장애 알림을 발송하는 규격입니다.

```python
class BaseNotificationService(ABC):
    @abstractmethod
    async def send_status_alert(self, title: str, message: str, level: str = "info") -> bool:
        """
        메신저의 지정 채널로 실시간 알림을 발송합니다.
        
        Args:
            title: 알림 제목
            message: 알림 상세 내용
            level: 알림 등급 ('info' | 'warning' | 'critical')
        """
        pass
```

---

## 📝 2. 에이전트 간 공유 데이터 규격화 (Context I/O Schema)

에이전트들이 `AgentContext`를 매개로 소통할 때, 데이터가 깨지지 않도록 아래의 정형화된 JSON 형식을 보장합니다.

### 1) 깃랩 코드 리뷰 플러그인 (`code_review`)

#### [PlanningAgent]
*   **요구 입력 (`context.metadata`)**:
    ```json
    {
      "payload": {
        "object_kind": "merge_request",
        "project": {
          "id": 105,
          "path_with_namespace": "esign2/backend"
        },
        "object_attributes": {
          "iid": 12,
          "source_branch": "feature/user-api"
        }
      }
    }
    ```
*   **보장 출력 (`context.outputs`)**:
    *   Key: `"git_diff"`
    *   Value: `str` (Git diff 포맷 문자열)

#### [CodeReviewAgent]
*   **요구 입력 (`context.outputs`)**:
    *   Key: `"git_diff"`
*   **보장 출력 (`context.outputs`)**:
    *   Key: `"review_results"`
    *   Value: `List[Dict[str, Any]]`
    *   상세 스키마:
        ```json
        [
          {
            "file_path": "src/main/java/com/esign/UserController.java",
            "line_number": 45,
            "severity": "warning",
            "issue_desc": "NullPointerException 위험이 있습니다. Optional을 도입해 보세요.",
            "rule_id": "SEC-005"
          }
        ]
        ```

---

### 2) 문서화 및 컨플루언스 플러그인 (`doc_organizer`)

#### [DocGeneratorAgent]
*   **요구 입력 (`context.metadata`)**:
    ```json
    {
      "payload": {
        "object_kind": "push",
        "ref": "refs/heads/main",
        "commits": [
          { "message": "feat: add user join API" }
        ],
        "changed_files": [
          "src/main/java/com/esign/UserJoinController.java"
        ]
      }
    }
    ```
*   **보장 출력 (`context.outputs`)**:
    *   Key: `"document_markdown"` / Value: `str` (작성된 Markdown 문자열)
    *   Key: `"document_title"` / Value: `str` (문서 제목 문자열)

#### [ConfluenceWikiAgent]
*   **요구 입력 (`context.outputs`)**:
    *   Key: `"document_markdown"`, `"document_title"`
*   **보장 출력 (`context.outputs`)**:
    *   Key: `"published_wiki_url"`
    *   Value: `str` ("https://confluence.company.com/pages/1234")

---

## 🔌 3. 코어 서비스 레지스트리 (ServiceRegistry) 구조

각 서비스 플러그인이 실행될 때, 에이전트들은 다음과 같이 코어에 등록된 표준 서비스 싱글톤을 획득하여 깃랩이나 슬랙과 소통합니다.

```python
# 서비스 플러그인 내부의 에이전트 실행부 예시
class GitLabReportAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentContext:
        # 코어의 서비스 레지스트리에서 '표준 리포지토리 연동 객체'를 획득
        repo_service: BaseRepositoryService = service_registry.get("repository")
        
        project_id = context.metadata["payload"]["project"]["id"]
        mr_iid = context.metadata["payload"]["object_attributes"]["iid"]
        
        # 실제 API 클라이언트 사용법을 몰라도, 약속된 규격의 메소드를 통해 호출 가능!
        await repo_service.post_mr_comment(
            project_id=project_id,
            mr_iid=mr_iid,
            comment="에이전트 분석 완료: 이상 없습니다."
        )
        
        return context
```
