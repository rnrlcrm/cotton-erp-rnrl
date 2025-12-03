"""
OCR Service using Tesseract

Production-ready OCR extraction for document processing.
Supports multiple document types with intelligent text extraction.
"""

import re
import logging
from typing import Dict, Optional, List
from io import BytesIO
import pytesseract
from PIL import Image
import tempfile
import os

logger = logging.getLogger(__name__)


class OCRService:
    """
    Tesseract-based OCR service for document extraction.
    
    Features:
    - Multi-language support
    - Confidence scoring
    - Document type-specific extraction
    - Image preprocessing for better accuracy
    """
    
    def __init__(self):
        """Initialize OCR service with Tesseract configuration."""
        self.config = r'--oem 3 --psm 6'  # LSTM OCR Engine, Assume uniform block of text
        
    def extract_text(self, image_bytes: bytes, lang: str = 'eng') -> Dict[str, any]:
        """
        Extract text from image using Tesseract OCR.
        
        Args:
            image_bytes: Raw image bytes
            lang: Language code (default: 'eng')
            
        Returns:
            Dict with extracted text and confidence
        """
        try:
            # Load image
            image = Image.open(BytesIO(image_bytes))
            
            # Preprocess image
            image = self._preprocess_image(image)
            
            # Extract text with confidence
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                config=self.config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Get full text
            text = pytesseract.image_to_string(image, lang=lang, config=self.config)
            
            return {
                "text": text.strip(),
                "confidence": round(avg_confidence / 100, 2),  # Convert to 0-1 scale
                "word_count": len(text.split()),
                "details": data
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        - Convert to grayscale
        - Increase contrast
        - Remove noise
        """
        # Convert to grayscale
        image = image.convert('L')
        
        # TODO: Add more preprocessing if needed:
        # - Deskewing
        # - Noise removal
        # - Thresholding
        
        return image
    
    def extract_gst_certificate(self, image_bytes: bytes) -> Dict:
        """
        Extract GSTIN and business details from GST certificate.
        
        Args:
            image_bytes: GST certificate image
            
        Returns:
            Dict with extracted GST data
        """
        result = self.extract_text(image_bytes)
        text = result.get("text", "")
        
        extracted_data = {
            "confidence": result.get("confidence", 0.0)
        }
        
        # Extract GSTIN (15 characters: 2 digit state code + 10 digit PAN + 1 digit entity number + Z + checksum)
        gstin_pattern = r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b'
        gstin_match = re.search(gstin_pattern, text)
        if gstin_match:
            extracted_data["gstin"] = gstin_match.group(0)
            
            # Extract PAN from GSTIN (characters 3-12)
            extracted_data["pan"] = gstin_match.group(0)[2:12]
        
        # Look for legal name (usually after "Legal Name" or "Name of Business")
        legal_name_patterns = [
            r'Legal Name[:\s]+([A-Z][A-Z\s&.,()]+?)(?:\n|$)',
            r'Name of Business[:\s]+([A-Z][A-Z\s&.,()]+?)(?:\n|$)',
            r'Trade Name[:\s]+([A-Z][A-Z\s&.,()]+?)(?:\n|$)'
        ]
        
        for pattern in legal_name_patterns:
            name_match = re.search(pattern, text, re.MULTILINE)
            if name_match:
                extracted_data["legal_name"] = name_match.group(1).strip()
                break
        
        # Extract date (registration date)
        date_pattern = r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b'
        date_match = re.search(date_pattern, text)
        if date_match:
            extracted_data["registration_date"] = date_match.group(1)
        
        return extracted_data
    
    def extract_pan_card(self, image_bytes: bytes) -> Dict:
        """
        Extract PAN number and name from PAN card.
        
        Args:
            image_bytes: PAN card image
            
        Returns:
            Dict with extracted PAN data
        """
        result = self.extract_text(image_bytes)
        text = result.get("text", "")
        
        extracted_data = {
            "confidence": result.get("confidence", 0.0)
        }
        
        # Extract PAN (10 characters: 5 letters + 4 digits + 1 letter)
        pan_pattern = r'\b[A-Z]{5}\d{4}[A-Z]{1}\b'
        pan_match = re.search(pan_pattern, text)
        if pan_match:
            extracted_data["pan"] = pan_match.group(0)
        
        # Extract name (usually in capital letters before PAN)
        # Look for lines with all caps that aren't the PAN itself
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Check if line is mostly uppercase and not the PAN
            if line and line.isupper() and len(line) > 5 and not re.match(pan_pattern, line):
                if "name" not in extracted_data:
                    extracted_data["name"] = line
                    break
        
        return extracted_data
    
    def extract_bank_proof(self, image_bytes: bytes) -> Dict:
        """
        Extract account number and IFSC from bank document.
        
        Args:
            image_bytes: Bank proof image (cancelled cheque/statement)
            
        Returns:
            Dict with extracted bank data
        """
        result = self.extract_text(image_bytes)
        text = result.get("text", "")
        
        extracted_data = {
            "confidence": result.get("confidence", 0.0)
        }
        
        # Extract IFSC (11 characters: 4 letters + 0 + 6 alphanumeric)
        ifsc_pattern = r'\b[A-Z]{4}0[A-Z0-9]{6}\b'
        ifsc_match = re.search(ifsc_pattern, text)
        if ifsc_match:
            extracted_data["ifsc"] = ifsc_match.group(0)
        
        # Extract account number (usually 9-18 digits)
        account_patterns = [
            r'Account No[.:\s]+(\d{9,18})',
            r'A/C No[.:\s]+(\d{9,18})',
            r'\b(\d{9,18})\b'  # Fallback: any 9-18 digit number
        ]
        
        for pattern in account_patterns:
            acc_match = re.search(pattern, text)
            if acc_match:
                extracted_data["account_number"] = acc_match.group(1)
                break
        
        # Extract bank name
        common_banks = [
            'STATE BANK OF INDIA', 'HDFC BANK', 'ICICI BANK', 'AXIS BANK',
            'PUNJAB NATIONAL BANK', 'BANK OF BARODA', 'CANARA BANK',
            'UNION BANK', 'BANK OF INDIA', 'KOTAK MAHINDRA'
        ]
        
        for bank in common_banks:
            if bank in text.upper():
                extracted_data["bank_name"] = bank
                break
        
        return extracted_data
    
    def extract_vehicle_rc(self, image_bytes: bytes) -> Dict:
        """
        Extract registration number from vehicle RC.
        
        Args:
            image_bytes: Vehicle RC image
            
        Returns:
            Dict with extracted vehicle data
        """
        result = self.extract_text(image_bytes)
        text = result.get("text", "")
        
        extracted_data = {
            "confidence": result.get("confidence", 0.0)
        }
        
        # Extract registration number (e.g., MH12AB1234, DL1CAA1234)
        reg_patterns = [
            r'\b[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}\b',  # Standard format
            r'\b[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4}\b'  # With spaces
        ]
        
        for pattern in reg_patterns:
            reg_match = re.search(pattern, text)
            if reg_match:
                # Remove spaces
                reg_no = reg_match.group(0).replace(' ', '')
                extracted_data["registration_number"] = reg_no
                break
        
        # Extract owner name
        owner_patterns = [
            r'Owner[:\s]+([A-Z][A-Z\s]+?)(?:\n|$)',
            r'Name[:\s]+([A-Z][A-Z\s]+?)(?:\n|$)'
        ]
        
        for pattern in owner_patterns:
            owner_match = re.search(pattern, text, re.MULTILINE)
            if owner_match:
                extracted_data["owner_name"] = owner_match.group(1).strip()
                break
        
        return extracted_data


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get singleton OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
