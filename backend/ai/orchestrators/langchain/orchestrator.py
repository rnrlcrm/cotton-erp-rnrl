"""
LangChain Orchestrator

Main orchestrator for LangChain-based AI workflows.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI, OpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, PromptTemplate

logger = logging.getLogger(__name__)


class LangChainOrchestrator:
    """
    LangChain orchestrator for ERP AI workflows.
    
    Features:
    - Model management (GPT-4, GPT-3.5, embeddings)
    - Prompt templates
    - Chain execution
    - Memory management
    - Tool integration
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize models
        self._chat_model: Optional[ChatOpenAI] = None
        self._llm: Optional[OpenAI] = None
        self._embeddings: Optional[OpenAIEmbeddings] = None
    
    def get_chat_model(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ChatOpenAI:
        """
        Get chat model (GPT-4, GPT-3.5).
        
        Args:
            model_name: Override default model
            temperature: Override default temperature
            
        Returns:
            ChatOpenAI instance
        """
        if self._chat_model is None or model_name or temperature is not None:
            self._chat_model = ChatOpenAI(
                api_key=self.api_key,
                model_name=model_name or self.model_name,
                temperature=temperature if temperature is not None else self.temperature,
            )
        
        return self._chat_model
    
    def get_llm(
        self,
        model_name: str = "gpt-3.5-turbo-instruct",
        temperature: Optional[float] = None,
    ) -> OpenAI:
        """
        Get completion model.
        
        Args:
            model_name: Model name
            temperature: Temperature
            
        Returns:
            OpenAI instance
        """
        if self._llm is None or temperature is not None:
            self._llm = OpenAI(
                api_key=self.api_key,
                model_name=model_name,
                temperature=temperature if temperature is not None else self.temperature,
            )
        
        return self._llm
    
    def get_embeddings(self) -> OpenAIEmbeddings:
        """
        Get embeddings model.
        
        Returns:
            OpenAIEmbeddings instance
        """
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                api_key=self.api_key,
                model="text-embedding-3-small",
            )
        
        return self._embeddings
    
    def create_prompt_template(
        self,
        template: str,
        input_variables: List[str],
    ) -> PromptTemplate:
        """
        Create prompt template.
        
        Args:
            template: Template string with {variables}
            input_variables: List of variable names
            
        Returns:
            PromptTemplate
        """
        return PromptTemplate(
            template=template,
            input_variables=input_variables,
        )
    
    def create_chat_prompt_template(
        self,
        system_message: str,
        human_message: str,
    ) -> ChatPromptTemplate:
        """
        Create chat prompt template.
        
        Args:
            system_message: System message template
            human_message: Human message template
            
        Returns:
            ChatPromptTemplate
        """
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message),
        ])


# Predefined prompts for ERP use cases
class ERPPrompts:
    """Common ERP prompt templates"""
    
    TRADE_ANALYSIS = """
You are an AI assistant for a cotton trading ERP system.

Analyze the following trade data and provide insights:
{trade_data}

Focus on:
1. Price trends
2. Risk factors
3. Recommendations

Provide a concise analysis.
"""
    
    CONTRACT_REVIEW = """
You are a legal AI assistant reviewing cotton trading contracts.

Review this contract:
{contract_text}

Check for:
1. Missing clauses
2. Risk factors
3. Compliance issues

Provide recommendations.
"""
    
    QUALITY_ASSESSMENT = """
You are a quality assessment AI for cotton inspection.

Based on these inspection results:
{inspection_data}

Determine:
1. Quality grade
2. Acceptance/rejection
3. Price adjustment

Provide assessment.
"""
    
    MARKET_INSIGHTS = """
You are a market analyst AI for the cotton industry.

Analyze these market conditions:
{market_data}

Provide:
1. Price forecast
2. Supply/demand analysis
3. Trading recommendations

Be specific and data-driven.
"""
