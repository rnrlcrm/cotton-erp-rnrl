"""
AI Agents using LangChain

Intelligent agents for ERP workflows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

from backend.ai.embeddings.chromadb.search import SemanticSearch
from backend.ai.orchestrators.langchain.orchestrator import LangChainOrchestrator

logger = logging.getLogger(__name__)


class ERPAgent:
    """
    Base ERP agent with tool access.
    
    Features:
    - Tool integration
    - Multi-step reasoning
    - Context management
    - Error handling
    """
    
    def __init__(
        self,
        orchestrator: LangChainOrchestrator,
        semantic_search: Optional[SemanticSearch] = None,
        tools: Optional[List[Tool]] = None,
    ):
        self.orchestrator = orchestrator
        self.semantic_search = semantic_search
        self.tools = tools or []
        
        # Initialize LLM
        self.llm = orchestrator.get_chat_model()
        
        # Create agent
        self.agent = None
        self.agent_executor = None
    
    def add_tool(self, tool: Tool):
        """Add tool to agent"""
        self.tools.append(tool)
    
    def _create_agent(self):
        """Create agent with tools"""
        if not self.agent:
            from langchain import hub
            
            # Get prompt from hub
            prompt = hub.pull("hwchase17/openai-functions-agent")
            
            # Create agent
            self.agent = create_openai_functions_agent(
                self.llm,
                self.tools,
                prompt,
            )
            
            # Create executor
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
            )
    
    async def execute(self, input: str) -> str:
        """
        Execute agent with input.
        
        Args:
            input: User input
            
        Returns:
            Agent response
        """
        self._create_agent()
        
        result = await self.agent_executor.ainvoke({"input": input})
        
        return result["output"]


class TradeAssistant(ERPAgent):
    """
    Trade assistant agent.
    
    Helps with:
    - Trade creation
    - Price negotiation
    - Trade status
    - Trade search
    """
    
    def __init__(
        self,
        orchestrator: LangChainOrchestrator,
        semantic_search: SemanticSearch,
    ):
        super().__init__(orchestrator, semantic_search)
        
        # Add trade-specific tools
        self._add_trade_tools()
    
    def _add_trade_tools(self):
        """Add trade-specific tools"""
        
        # Search trades tool
        search_trades_tool = Tool(
            name="search_trades",
            description="Search for trades using natural language. Input should be a search query.",
            func=self._search_trades,
        )
        self.add_tool(search_trades_tool)
        
        # Get trade details tool
        get_trade_tool = Tool(
            name="get_trade_details",
            description="Get details of a specific trade. Input should be trade ID.",
            func=self._get_trade_details,
        )
        self.add_tool(get_trade_tool)
    
    async def _search_trades(self, query: str) -> str:
        """Search trades"""
        results = await self.semantic_search.search(
            query=query,
            k=5,
            filter={"document_type": "trade"},
        )
        
        if not results:
            return "No trades found matching your query."
        
        # Format results
        output = f"Found {len(results)} trades:\n\n"
        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            output += f"{i}. Trade {metadata.get('trade_id', 'Unknown')}\n"
            output += f"   {r['document'][:200]}...\n\n"
        
        return output
    
    async def _get_trade_details(self, trade_id: str) -> str:
        """Get trade details"""
        # This would query the actual database
        # For now, search in vector store
        results = await self.semantic_search.search(
            query=f"trade {trade_id}",
            k=1,
            filter={"trade_id": trade_id},
        )
        
        if not results:
            return f"Trade {trade_id} not found."
        
        return results[0]["document"]


class ContractAssistant(ERPAgent):
    """
    Contract assistant agent.
    
    Helps with:
    - Contract search
    - Contract analysis
    - Clause extraction
    - Compliance checking
    """
    
    def __init__(
        self,
        orchestrator: LangChainOrchestrator,
        semantic_search: SemanticSearch,
    ):
        super().__init__(orchestrator, semantic_search)
        self._add_contract_tools()
    
    def _add_contract_tools(self):
        """Add contract-specific tools"""
        
        search_contracts_tool = Tool(
            name="search_contracts",
            description="Search for contracts using natural language. Input should be a search query.",
            func=self._search_contracts,
        )
        self.add_tool(search_contracts_tool)
        
        analyze_contract_tool = Tool(
            name="analyze_contract",
            description="Analyze contract for key terms, risks, and compliance. Input should be contract ID.",
            func=self._analyze_contract,
        )
        self.add_tool(analyze_contract_tool)
    
    async def _search_contracts(self, query: str) -> str:
        """Search contracts"""
        results = await self.semantic_search.search_contracts(query=query, k=5)
        
        if not results:
            return "No contracts found matching your query."
        
        output = f"Found {len(results)} contracts:\n\n"
        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            output += f"{i}. Contract {metadata.get('contract_id', 'Unknown')}\n"
            output += f"   Party: {metadata.get('party_name', 'Unknown')}\n"
            output += f"   {r['document'][:150]}...\n\n"
        
        return output
    
    async def _analyze_contract(self, contract_id: str) -> str:
        """Analyze contract"""
        # Get contract context
        context = await self.semantic_search.get_document_context(
            query="key terms payment delivery obligations risks",
            document_id=contract_id,
            k=5,
        )
        
        if not context:
            return f"Contract {contract_id} not found."
        
        # Use LLM to analyze
        analysis_prompt = f"""Analyze this contract and provide:
1. Key terms and conditions
2. Payment terms
3. Delivery obligations
4. Potential risks
5. Compliance issues

Contract text:
{context}
"""
        
        response = await self.llm.ainvoke(analysis_prompt)
        return response.content


class QualityAssistant(ERPAgent):
    """
    Quality assistant agent.
    
    Helps with:
    - Quality report search
    - Grade analysis
    - Quality trends
    - Defect identification
    """
    
    def __init__(
        self,
        orchestrator: LangChainOrchestrator,
        semantic_search: SemanticSearch,
    ):
        super().__init__(orchestrator, semantic_search)
        self._add_quality_tools()
    
    def _add_quality_tools(self):
        """Add quality-specific tools"""
        
        search_reports_tool = Tool(
            name="search_quality_reports",
            description="Search quality reports. Input should be search query.",
            func=self._search_reports,
        )
        self.add_tool(search_reports_tool)
        
        analyze_quality_tool = Tool(
            name="analyze_quality_trends",
            description="Analyze quality trends for a commodity. Input should be commodity name.",
            func=self._analyze_trends,
        )
        self.add_tool(analyze_quality_tool)
    
    async def _search_reports(self, query: str) -> str:
        """Search quality reports"""
        results = await self.semantic_search.search_quality_reports(query=query, k=5)
        
        if not results:
            return "No quality reports found."
        
        output = f"Found {len(results)} quality reports:\n\n"
        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            output += f"{i}. Report {metadata.get('report_id', 'Unknown')}\n"
            output += f"   Grade: {metadata.get('grade', 'Unknown')}\n"
            output += f"   {r['document'][:150]}...\n\n"
        
        return output
    
    async def _analyze_trends(self, commodity: str) -> str:
        """Analyze quality trends"""
        # Search for reports of this commodity
        results = await self.semantic_search.search_quality_reports(
            query=f"{commodity} quality grade moisture",
            commodity=commodity,
            k=10,
        )
        
        if not results:
            return f"No quality data found for {commodity}."
        
        # Aggregate data
        context = "\n".join([r["document"] for r in results])
        
        # Analyze trends
        trend_prompt = f"""Analyze quality trends for {commodity} based on these reports:

{context}

Provide:
1. Average quality grade
2. Common defects
3. Quality trends (improving/declining)
4. Recommendations
"""
        
        response = await self.llm.ainvoke(trend_prompt)
        return response.content
