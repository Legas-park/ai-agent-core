from core.agent.base_agent import BaseAgent
from core.agent.context import AgentContext

class DocGeneratorAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentContext:
        await self.log_info(context, "Generating updated documentation...")
        context.set_output("doc_url", "https://confluence.company.com/pages/12345")
        return context
