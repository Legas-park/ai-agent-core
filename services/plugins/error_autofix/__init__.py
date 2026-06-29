from typing import Dict, Any, List
from core.plugin import ServicePlugin
from core.agent.base_agent import BaseAgent
from .agents.fix import ErrorAnalysisAgent, AutoFixAgent

class ErrorAutoFixPlugin(ServicePlugin):
    @property
    def name(self) -> str:
        return "error_autofix_service"
        
    def can_handle(self, payload: Dict[str, Any]) -> bool:
        """Handles CI/CD or DB error triggers"""
        return payload.get("event_type") == "error_trigger"

    def get_pipeline(self, payload: Dict[str, Any]) -> List[BaseAgent]:
        return [
            ErrorAnalysisAgent(name="ErrorAnalysisAgent"),
            AutoFixAgent(name="AutoFixAgent")
        ]

plugin = ErrorAutoFixPlugin()
