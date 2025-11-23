"""
Document Embedder

Handles document processing and embedding generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from backend.ai.embeddings.chromadb.store import ChromaDBStore

logger = logging.getLogger(__name__)


class DocumentEmbedder:
    """
    Document embedding and indexing.
    
    Features:
    - Text chunking
    - Embedding generation
    - Metadata extraction
    - Batch processing
    """
    
    def __init__(
        self,
        vector_store: ChromaDBStore,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    
    async def embed_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> List[str]:
        """
        Embed single document.
        
        Args:
            text: Document text
            metadata: Document metadata
            document_id: Optional document ID
            
        Returns:
            List of chunk IDs
        """
        # Split into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Generate metadata for each chunk
        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **(metadata or {}),
                "document_id": document_id or str(uuid4()),
                "chunk_index": i,
                "chunk_count": len(chunks),
                "chunk_size": len(chunk),
            }
            chunk_metadatas.append(chunk_metadata)
        
        # Add to vector store
        chunk_ids = await self.vector_store.add_documents(
            documents=chunks,
            metadatas=chunk_metadatas,
        )
        
        logger.info(f"Embedded document into {len(chunks)} chunks")
        return chunk_ids
    
    async def embed_contract(
        self,
        contract_id: UUID,
        contract_text: str,
        contract_metadata: Dict[str, Any],
    ) -> List[str]:
        """
        Embed contract document.
        
        Args:
            contract_id: Contract ID
            contract_text: Contract text
            contract_metadata: Contract metadata (parties, date, etc.)
            
        Returns:
            List of chunk IDs
        """
        metadata = {
            **contract_metadata,
            "document_type": "contract",
            "contract_id": str(contract_id),
        }
        
        return await self.embed_document(
            text=contract_text,
            metadata=metadata,
            document_id=str(contract_id),
        )
    
    async def embed_quality_report(
        self,
        report_id: UUID,
        report_text: str,
        report_metadata: Dict[str, Any],
    ) -> List[str]:
        """
        Embed quality report.
        
        Args:
            report_id: Report ID
            report_text: Report text
            report_metadata: Report metadata (grade, moisture, etc.)
            
        Returns:
            List of chunk IDs
        """
        metadata = {
            **report_metadata,
            "document_type": "quality_report",
            "report_id": str(report_id),
        }
        
        return await self.embed_document(
            text=report_text,
            metadata=metadata,
            document_id=str(report_id),
        )
    
    async def embed_invoice(
        self,
        invoice_id: UUID,
        invoice_text: str,
        invoice_metadata: Dict[str, Any],
    ) -> List[str]:
        """
        Embed invoice document.
        
        Args:
            invoice_id: Invoice ID
            invoice_text: Invoice text
            invoice_metadata: Invoice metadata (amount, date, etc.)
            
        Returns:
            List of chunk IDs
        """
        metadata = {
            **invoice_metadata,
            "document_type": "invoice",
            "invoice_id": str(invoice_id),
        }
        
        return await self.embed_document(
            text=invoice_text,
            metadata=metadata,
            document_id=str(invoice_id),
        )
    
    async def embed_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """
        Embed multiple documents.
        
        Args:
            documents: List of documents with 'text' and 'metadata' keys
            
        Returns:
            Dict mapping document IDs to chunk IDs
        """
        results = {}
        
        for doc in documents:
            doc_id = doc.get("id", str(uuid4()))
            chunk_ids = await self.embed_document(
                text=doc["text"],
                metadata=doc.get("metadata"),
                document_id=doc_id,
            )
            results[doc_id] = chunk_ids
        
        logger.info(f"Embedded {len(documents)} documents in batch")
        return results
    
    async def remove_document(self, document_id: str):
        """
        Remove document and all its chunks.
        
        Args:
            document_id: Document ID
        """
        # Query for all chunks of this document
        results = await self.vector_store.similarity_search(
            query="",  # Empty query to get all
            k=1000,
            filter={"document_id": document_id},
        )
        
        # Delete all chunks
        chunk_ids = [r["id"] for r in results]
        if chunk_ids:
            await self.vector_store.delete_documents(chunk_ids)
            logger.info(f"Removed document {document_id} ({len(chunk_ids)} chunks)")
