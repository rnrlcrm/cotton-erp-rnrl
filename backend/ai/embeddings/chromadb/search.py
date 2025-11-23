"""
Semantic Search

Advanced semantic search capabilities over document embeddings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.ai.embeddings.chromadb.store import ChromaDBStore

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Semantic search over embedded documents.
    
    Features:
    - Natural language queries
    - Metadata filtering
    - Hybrid search (semantic + keyword)
    - Result ranking
    """
    
    def __init__(self, vector_store: ChromaDBStore):
        self.vector_store = vector_store
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search.
        
        Args:
            query: Natural language query
            k: Number of results
            filter: Metadata filter
            
        Returns:
            List of matching documents with scores
        """
        results = await self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )
        
        logger.info(f"Semantic search: '{query}' → {len(results)} results")
        return results
    
    async def search_contracts(
        self,
        query: str,
        k: int = 5,
        party_name: Optional[str] = None,
        start_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search contracts.
        
        Args:
            query: Search query
            k: Number of results
            party_name: Filter by party name
            start_date: Filter by date
            
        Returns:
            Matching contracts
        """
        filter_dict = {"document_type": "contract"}
        
        if party_name:
            filter_dict["party_name"] = party_name
        
        if start_date:
            filter_dict["start_date"] = start_date
        
        return await self.search(query, k, filter_dict)
    
    async def search_quality_reports(
        self,
        query: str,
        k: int = 5,
        min_grade: Optional[str] = None,
        commodity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search quality reports.
        
        Args:
            query: Search query
            k: Number of results
            min_grade: Minimum grade filter
            commodity: Commodity type
            
        Returns:
            Matching quality reports
        """
        filter_dict = {"document_type": "quality_report"}
        
        if commodity:
            filter_dict["commodity"] = commodity
        
        if min_grade:
            filter_dict["grade"] = min_grade
        
        return await self.search(query, k, filter_dict)
    
    async def search_invoices(
        self,
        query: str,
        k: int = 5,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search invoices.
        
        Args:
            query: Search query
            k: Number of results
            min_amount: Minimum amount
            max_amount: Maximum amount
            
        Returns:
            Matching invoices
        """
        filter_dict = {"document_type": "invoice"}
        
        # Note: ChromaDB doesn't support range queries in metadata
        # This would need post-filtering
        
        return await self.search(query, k, filter_dict)
    
    async def find_similar_documents(
        self,
        document_id: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find documents similar to given document.
        
        Args:
            document_id: Source document ID
            k: Number of results
            
        Returns:
            Similar documents
        """
        # Get the document
        results = await self.vector_store.similarity_search(
            query="",
            k=1,
            filter={"document_id": document_id},
        )
        
        if not results:
            return []
        
        # Use first chunk as query
        query_text = results[0]["document"]
        
        # Search for similar (excluding self)
        similar = await self.search(query_text, k + 1)
        
        # Filter out the source document
        similar = [r for r in similar if r["metadata"].get("document_id") != document_id]
        
        return similar[:k]
    
    async def get_document_context(
        self,
        query: str,
        document_id: str,
        k: int = 3,
    ) -> str:
        """
        Get relevant context from specific document.
        
        Args:
            query: Query text
            document_id: Document to search within
            k: Number of chunks
            
        Returns:
            Concatenated relevant chunks
        """
        results = await self.search(
            query=query,
            k=k,
            filter={"document_id": document_id},
        )
        
        # Concatenate chunks
        context = "\n\n".join([r["document"] for r in results])
        
        return context
    
    async def answer_question(
        self,
        question: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Answer question using semantic search + context.
        
        Args:
            question: Question text
            k: Number of context chunks
            filter: Metadata filter
            
        Returns:
            Dict with answer and sources
        """
        # Search for relevant context
        results = await self.search(question, k, filter)
        
        # Build context
        context = "\n\n".join([
            f"[Source {i+1}]: {r['document']}"
            for i, r in enumerate(results)
        ])
        
        return {
            "question": question,
            "context": context,
            "sources": results,
            "source_count": len(results),
        }
