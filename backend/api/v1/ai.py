"""
AI Orchestration API
Endpoints for AI chat, semantic search, and document analysis
"""
from typing import Optional, List, Dict
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth.dependencies import get_current_user
from backend.core.settings.base import Settings, get_settings
from backend.ai.embeddings.chromadb.store import ChromaDBStore, Collections
from backend.ai.embeddings.chromadb.search import SemanticSearch
from backend.ai.orchestrators.langchain.orchestrator import LangChainOrchestrator
from backend.ai.orchestrators.langchain.agents import (
    TradeAssistant,
    ContractAssistant,
    QualityAssistant,
)


router = APIRouter(prefix="/ai", tags=["ai"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class ChatRequest(BaseModel):
    """Chat request"""
    message: str = Field(..., description="User message")
    assistant_type: str = Field(
        default="general",
        description="Assistant type: trade, contract, quality, general"
    )
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous messages for context"
    )


class ChatResponse(BaseModel):
    """Chat response"""
    response: str = Field(..., description="Assistant response")
    sources: List[Dict] = Field(default_factory=list, description="Source documents")
    confidence: Optional[float] = Field(None, description="Response confidence score")


class SearchRequest(BaseModel):
    """Semantic search request"""
    query: str = Field(..., description="Search query")
    collection_type: str = Field(
        default="all",
        description="Collection: contracts, quality_reports, invoices, all"
    )
    k: int = Field(default=5, description="Number of results", ge=1, le=50)
    filter: Optional[Dict] = Field(None, description="Metadata filter")


class SearchResult(BaseModel):
    """Search result"""
    id: str
    document: str
    metadata: Dict
    distance: float


class SearchResponse(BaseModel):
    """Search response"""
    results: List[SearchResult]
    total: int


class AnalyzeDocumentRequest(BaseModel):
    """Document analysis request"""
    document_text: str = Field(..., description="Document text to analyze")
    document_type: str = Field(
        default="contract",
        description="Document type: contract, invoice, quality_report"
    )
    analysis_type: str = Field(
        default="summary",
        description="Analysis type: summary, risks, compliance, trends"
    )


class AnalyzeDocumentResponse(BaseModel):
    """Document analysis response"""
    analysis: str = Field(..., description="Analysis result")
    insights: List[str] = Field(default_factory=list, description="Key insights")
    metadata: Dict = Field(default_factory=dict, description="Extracted metadata")


# ============================================================================
# Dependency Injection
# ============================================================================


def get_vector_store(settings: Settings = Depends(get_settings)) -> ChromaDBStore:
    """Get ChromaDB vector store instance"""
    return ChromaDBStore(
        collection_name=Collections.TRADE_DOCUMENTS,
        persist_directory=settings.CHROMADB_PERSIST_DIR
    )


def get_semantic_search(
    vector_store: ChromaDBStore = Depends(get_vector_store)
) -> SemanticSearch:
    """Get semantic search instance"""
    return SemanticSearch(vector_store=vector_store)


def get_orchestrator(settings: Settings = Depends(get_settings)) -> LangChainOrchestrator:
    """Get LangChain orchestrator"""
    return LangChainOrchestrator(
        model_name="gpt-4-turbo-preview",
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    orchestrator: LangChainOrchestrator = Depends(get_orchestrator),
    semantic_search: SemanticSearch = Depends(get_semantic_search),
) -> ChatResponse:
    """
    AI Chat endpoint
    
    Executes specialized AI assistants for different domains:
    - trade: Trade operations, market analysis
    - contract: Contract review, risk analysis
    - quality: Quality reports, trend analysis
    - general: General ERP queries
    """
    try:
        # Select appropriate assistant
        if request.assistant_type == "trade":
            assistant = TradeAssistant(orchestrator, semantic_search)
        elif request.assistant_type == "contract":
            assistant = ContractAssistant(orchestrator, semantic_search)
        elif request.assistant_type == "quality":
            assistant = QualityAssistant(orchestrator, semantic_search)
        else:
            # General assistant - use base orchestrator
            assistant = orchestrator
        
        # Execute agent
        if hasattr(assistant, "execute"):
            response_text = await assistant.execute(request.message)
        else:
            # Fallback to direct orchestrator call
            response_text = await orchestrator.run(
                prompt=request.message,
                conversation_history=request.conversation_history
            )
        
        # Extract sources if available (from agent tools)
        sources = []
        if hasattr(assistant, "last_sources"):
            sources = assistant.last_sources
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            confidence=0.85  # Placeholder - implement confidence scoring
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user = Depends(get_current_user),
    semantic_search: SemanticSearch = Depends(get_semantic_search),
) -> SearchResponse:
    """
    Semantic Search endpoint
    
    Natural language search across ERP documents:
    - Contracts
    - Quality Reports
    - Invoices
    - Trade Documents
    """
    try:
        # Route to appropriate search method
        if request.collection_type == "contracts":
            results = await semantic_search.search_contracts(
                query=request.query,
                k=request.k,
                **request.filter or {}
            )
        elif request.collection_type == "quality_reports":
            results = await semantic_search.search_quality_reports(
                query=request.query,
                k=request.k,
                **request.filter or {}
            )
        elif request.collection_type == "invoices":
            results = await semantic_search.search_invoices(
                query=request.query,
                k=request.k,
                **request.filter or {}
            )
        else:
            # Search all collections
            results = await semantic_search.search(
                query=request.query,
                k=request.k,
                filter=request.filter
            )
        
        search_results = [
            SearchResult(
                id=r.get("id", str(uuid4())),
                document=r.get("document", ""),
                metadata=r.get("metadata", {}),
                distance=r.get("distance", 1.0)
            )
            for r in results
        ]
        
        return SearchResponse(
            results=search_results,
            total=len(search_results)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/analyze", response_model=AnalyzeDocumentResponse)
async def analyze_document(
    request: AnalyzeDocumentRequest,
    current_user = Depends(get_current_user),
    orchestrator: LangChainOrchestrator = Depends(get_orchestrator),
    semantic_search: SemanticSearch = Depends(get_semantic_search),
) -> AnalyzeDocumentResponse:
    """
    Document Analysis endpoint
    
    AI-powered document analysis:
    - Summarization
    - Risk identification
    - Compliance checking
    - Trend analysis
    """
    try:
        # Select appropriate assistant
        if request.document_type == "contract":
            assistant = ContractAssistant(orchestrator, semantic_search)
            prompt = f"Analyze this contract for {request.analysis_type}:\n\n{request.document_text}"
        elif request.document_type == "quality_report":
            assistant = QualityAssistant(orchestrator, semantic_search)
            prompt = f"Analyze this quality report for {request.analysis_type}:\n\n{request.document_text}"
        else:
            assistant = orchestrator
            prompt = f"Analyze this {request.document_type} document for {request.analysis_type}:\n\n{request.document_text}"
        
        # Execute analysis
        if hasattr(assistant, "execute"):
            analysis_text = await assistant.execute(prompt)
        else:
            analysis_text = await orchestrator.run(prompt=prompt)
        
        # Extract structured insights (simple split for now)
        insights = [
            line.strip("- ")
            for line in analysis_text.split("\n")
            if line.strip().startswith("-")
        ][:5]  # Top 5 insights
        
        return AnalyzeDocumentResponse(
            analysis=analysis_text,
            insights=insights,
            metadata={
                "document_type": request.document_type,
                "analysis_type": request.analysis_type,
                "word_count": len(request.document_text.split())
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document analysis failed: {str(e)}"
        )


@router.get("/health")
async def health_check(
    current_user = Depends(get_current_user),
    vector_store: ChromaDBStore = Depends(get_vector_store),
) -> Dict:
    """
    Health check endpoint
    
    Returns status of AI services
    """
    try:
        stats = await vector_store.get_collection_stats()
        
        return {
            "status": "healthy",
            "vector_store": {
                "collection": vector_store.collection_name,
                "document_count": stats.get("count", 0),
            },
            "models": {
                "llm": "gpt-4-turbo-preview",
                "embeddings": "text-embedding-3-small"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
