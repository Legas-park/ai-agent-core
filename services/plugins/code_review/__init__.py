from typing import Dict, Any, List
from core.plugin import ServicePlugin
from core.agent.base_agent import BaseAgent
from .agents.review import CodeReviewAgent
from .agents.planning import PlanningAgent

class CodeReviewPlugin(ServicePlugin):
    @property
    def name(self) -> str:
        return "code_review_service"
        
    def can_handle(self, payload: Dict[str, Any]) -> bool:
        """GitLab MR 또는 GitHub PR 웹훅을 처리합니다."""
        if payload.get("object_kind") == "merge_request":
            return True
        if "pull_request" in payload:
            action = payload.get("action")
            if action is None:
                return True
            return action in {
                "opened", "synchronize", "reopened", "ready_for_review", "edited",
            }
        return False

    def get_pipeline(self, payload: Dict[str, Any]) -> List[BaseAgent]:
        """Returns the specific agent pipeline for Code Review"""
        return [
            PlanningAgent(name="PlanningAgent"),
            CodeReviewAgent(name="CodeReviewAgent")
        ]

# Export the plugin instance
plugin = CodeReviewPlugin()
