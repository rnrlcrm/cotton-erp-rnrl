"""
OCR Module

Optical Character Recognition services for document processing.
"""

from backend.core.ocr.ocr_service import OCRService, get_ocr_service

__all__ = [
    "OCRService",
    "get_ocr_service",
]
