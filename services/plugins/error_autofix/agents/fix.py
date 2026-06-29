from core.agent.base_agent import BaseAgent
from core.agent.context import AgentContext

class ErrorAnalysisAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentContext:
        await self.log_info(context, "Analyzing error trace...")
        context.set_output("error_root_cause", "NullPointerException in UserService")
        return context

class AutoFixAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentContext:
        cause = context.get_output("error_root_cause")
        await self.log_info(context, f"Applying fix for: {cause}")
        context.set_output("fix_status", "Success")
        return context
