"""
LangChain Chains

Conversation and analysis chains for ERP workflows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from backend.ai.orchestrators.langchain.orchestrator import ERPPrompts

logger = logging.getLogger(__name__)


class ConversationChain:
    """
    Conversational AI chain for ERP chatbot.
    
    Features:
    - Multi-turn conversations
    - Context awareness
    - Memory management
    - Domain-specific responses
    """
    
    def __init__(
        self,
        llm: ChatOpenAI,
        memory: Optional[ConversationBufferMemory] = None,
        system_message: Optional[str] = None,
    ):
        self.llm = llm
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )
        
        # Default system message
        if system_message is None:
            system_message = """You are an AI assistant for a Commodity Trading ERP system.

You help users with:
- Trade management
- Contract processing
- Quality inspection
- Payment tracking
- Logistics coordination
- Dispute resolution

Be professional, concise, and helpful. Provide specific information when available.
If you need more context, ask clarifying questions."""
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{chat_history}\n\nHuman: {input}\nAssistant:"),
        ])
        
        # Create chain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=True,
        )
    
    async def run(self, user_input: str) -> str:
        """
        Run conversation turn.
        
        Args:
            user_input: User message
            
        Returns:
            Assistant response
        """
        try:
            response = await self.chain.arun(input=user_input)
            return response
        except Exception as e:
            logger.error(f"Conversation error: {e}")
            return "I apologize, but I encountered an error. Please try again."
    
    def clear_memory(self):
        """Clear conversation history"""
        self.memory.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Returns:
            List of messages
        """
        messages = self.memory.load_memory_variables({}).get("chat_history", [])
        return [
            {"role": "human" if i % 2 == 0 else "assistant", "content": msg.content}
            for i, msg in enumerate(messages)
        ]


class AnalysisChain:
    """
    Analysis chain for ERP data insights.
    
    Features:
    - Trade analysis
    - Contract review
    - Quality assessment
    - Market insights
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    async def analyze_trade(self, trade_data: Dict[str, Any]) -> str:
        """
        Analyze trade data.
        
        Args:
            trade_data: Trade information
            
        Returns:
            Analysis
        """
        prompt = ChatPromptTemplate.from_template(ERPPrompts.TRADE_ANALYSIS)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        try:
            response = await chain.arun(trade_data=str(trade_data))
            return response
        except Exception as e:
            logger.error(f"Trade analysis error: {e}")
            return "Analysis failed"
    
    async def review_contract(self, contract_text: str) -> str:
        """
        Review contract.
        
        Args:
            contract_text: Contract content
            
        Returns:
            Review
        """
        prompt = ChatPromptTemplate.from_template(ERPPrompts.CONTRACT_REVIEW)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        try:
            response = await chain.arun(contract_text=contract_text)
            return response
        except Exception as e:
            logger.error(f"Contract review error: {e}")
            return "Review failed"
    
    async def assess_quality(self, inspection_data: Dict[str, Any]) -> str:
        """
        Assess quality.
        
        Args:
            inspection_data: Inspection results
            
        Returns:
            Assessment
        """
        prompt = ChatPromptTemplate.from_template(ERPPrompts.QUALITY_ASSESSMENT)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        try:
            response = await chain.arun(inspection_data=str(inspection_data))
            return response
        except Exception as e:
            logger.error(f"Quality assessment error: {e}")
            return "Assessment failed"
    
    async def get_market_insights(self, market_data: Dict[str, Any]) -> str:
        """
        Get market insights.
        
        Args:
            market_data: Market information
            
        Returns:
            Insights
        """
        prompt = ChatPromptTemplate.from_template(ERPPrompts.MARKET_INSIGHTS)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        try:
            response = await chain.arun(market_data=str(market_data))
            return response
        except Exception as e:
            logger.error(f"Market insights error: {e}")
            return "Insights unavailable"
