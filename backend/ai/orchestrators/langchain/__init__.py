"""
LangChain AI Orchestration

Integrates LangChain for AI workflows in the ERP system.

Exports:
- LangChainOrchestrator: Main orchestrator
- ConversationChain: Conversational AI
- AgentExecutor: AI agents with tools
- MemoryManager: Conversation memory
"""

from backend.ai/orchestrators/langchain/orchestrator import LangChainOrchestrator
from backend.ai.orchestrators.langchain.chains import ConversationChain, AnalysisChain
from backend.ai.orchestrators.langchain.agents import AgentExecutor, ERPAgent
from backend.ai.orchestrators.langchain.memory import MemoryManager

__all__ = [
    "LangChainOrchestrator",
    "ConversationChain",
    "AnalysisChain",
    "AgentExecutor",
    "ERPAgent",
    "MemoryManager",
]
