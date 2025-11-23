"""
ChromaDB Vector Store

Manages vector storage and retrieval using ChromaDB.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class ChromaDBStore:
    """
    ChromaDB vector store for semantic search.
    
    Features:
    - Document embedding storage
    - Semantic similarity search
    - Multi-collection support
    - Metadata filtering
    """
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "erp_documents",
        embedding_model: Optional[OpenAIEmbeddings] = None,
    ):
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIR",
            "/tmp/chromadb",
        )
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory,
            )
        )
        
        # Initialize embedding model
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        logger.info(f"Initialized ChromaDB store: {collection_name}")
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to vector store.
        
        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for documents (auto-generated if None)
            
        Returns:
            List of document IDs
        """
        # Generate embeddings
        embeddings = await self.embedding_model.aembed_documents(documents)
        
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        
        logger.info(f"Added {len(documents)} documents to {self.collection_name}")
        return ids
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Query text
            k: Number of results
            filter: Metadata filter
            
        Returns:
            List of results with document, metadata, distance
        """
        # Generate query embedding
        query_embedding = await self.embedding_model.aembed_query(query)
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter,
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })
        
        return formatted_results
    
    async def delete_documents(self, ids: List[str]):
        """
        Delete documents by IDs.
        
        Args:
            ids: Document IDs to delete
        """
        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} documents from {self.collection_name}")
    
    async def update_document(
        self,
        id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Update document and/or metadata.
        
        Args:
            id: Document ID
            document: New document text
            metadata: New metadata
        """
        update_data = {"ids": [id]}
        
        if document:
            embedding = await self.embedding_model.aembed_query(document)
            update_data["embeddings"] = [embedding]
            update_data["documents"] = [document]
        
        if metadata:
            update_data["metadatas"] = [metadata]
        
        self.collection.update(**update_data)
        logger.info(f"Updated document {id}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_directory": self.persist_directory,
        }
    
    def clear_collection(self):
        """Clear all documents from collection"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.warning(f"Cleared collection {self.collection_name}")


# Predefined collections for different document types
class Collections:
    """Common ChromaDB collections"""
    
    CONTRACTS = "contracts"
    INVOICES = "invoices"
    QUALITY_REPORTS = "quality_reports"
    TRADE_DOCUMENTS = "trade_documents"
    USER_MANUALS = "user_manuals"
    MARKET_REPORTS = "market_reports"
    COMPLIANCE_DOCS = "compliance_documents"
