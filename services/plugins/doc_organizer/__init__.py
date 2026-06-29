from typing import Dict, Any, List
from core.plugin import ServicePlugin
from core.agent.base_agent import BaseAgent
from .agents.doc import DocGeneratorAgent

class DocOrganizerPlugin(ServicePlugin):
    @property
    def name(self) -> str:
        return "doc_organizer_service"
        
    def can_handle(self, payload: Dict[str, Any]) -> bool:
        """Handles Push events to main/master branches for doc updates"""
        return payload.get("object_kind") == "push" and payload.get("ref") in ["refs/heads/main", "refs/heads/master"]

    def get_pipeline(self, payload: Dict[str, Any]) -> List[BaseAgent]:
        return [
            DocGeneratorAgent(name="DocGeneratorAgent")
        ]

plugin = DocOrganizerPlugin()
