"""
PII Sanitization Filter

Masks PII (Personally Identifiable Information) in logs for compliance.
Critical for 15-year architecture - GDPR, privacy regulations.

Sanitizes:
- Email addresses
- Phone numbers
- Credit card numbers
- Aadhaar numbers  
- PAN numbers
- IP addresses (partial)
- API keys / tokens

NO business logic - pure logging filter.
"""

import re
import logging
from typing import Dict, Pattern


class PIISanitizer:
    """
    PII sanitization utility.
    
    Masks sensitive data in strings before logging.
    """
    
    # Regex patterns for PII detection
    PATTERNS: Dict[str, Pattern] = {
        # Email: user@example.com → u***@example.com
        'email': re.compile(r'\b([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'),
        
        # Phone: +91-9876543210 → +91-98******10
        'phone': re.compile(r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b'),
        
        # Credit Card: 4111-1111-1111-1111 → 4111-****-****-1111
        'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        
        # Aadhaar: 1234-5678-9012 → ****-****-9012
        'aadhaar': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        
        # PAN: ABCDE1234F → A****1234F
        'pan': re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
        
        # IP Address: 192.168.1.100 → 192.168.***.***
        'ip_address': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
        
        # API Keys: sk_test_abcd1234efgh5678 → sk_test_****
        'api_key': re.compile(r'\b(sk|pk|api)_[a-z]+_[a-zA-Z0-9]{16,}\b'),
        
        # JWT Tokens: eyJhbGciOi... → eyJ****
        'jwt': re.compile(r'\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b'),
        
        # Passwords in URLs: password=secret123 → password=***
        'password_in_url': re.compile(r'(password|pwd|pass)=([^&\s]+)', re.IGNORECASE),
    }
    
    @classmethod
    def sanitize_email(cls, match: re.Match) -> str:
        """Sanitize email address."""
        first_char = match.group(1)
        domain = match.group(2)
        return f"{first_char}***@{domain}"
    
    @classmethod
    def sanitize_phone(cls, match: re.Match) -> str:
        """Sanitize phone number."""
        phone = match.group(0)
        # Keep first 5 and last 2 digits
        if len(phone) > 7:
            return phone[:5] + '*' * (len(phone) - 7) + phone[-2:]
        return '***'
    
    @classmethod
    def sanitize_credit_card(cls, match: re.Match) -> str:
        """Sanitize credit card number."""
        card = match.group(0).replace('-', '').replace(' ', '')
        # Keep first 4 and last 4 digits
        return f"{card[:4]}-****-****-{card[-4:]}"
    
    @classmethod
    def sanitize_aadhaar(cls, match: re.Match) -> str:
        """Sanitize Aadhaar number."""
        aadhaar = match.group(0)
        # Only show last 4 digits
        return "****-****-" + aadhaar[-4:]
    
    @classmethod
    def sanitize_pan(cls, match: re.Match) -> str:
        """Sanitize PAN number."""
        pan = match.group(0)
        # A****1234F format
        return f"{pan[0]}****{pan[5:9]}{pan[-1]}"
    
    @classmethod
    def sanitize_ip(cls, match: re.Match) -> str:
        """Sanitize IP address."""
        ip_parts = match.group(0).split('.')
        # Show first two octets
        return f"{ip_parts[0]}.{ip_parts[1]}.***.***"
    
    @classmethod
    def sanitize_api_key(cls, match: re.Match) -> str:
        """Sanitize API keys."""
        key = match.group(0)
        prefix = key.split('_')[0] + '_' + key.split('_')[1]
        return f"{prefix}_****"
    
    @classmethod
    def sanitize_jwt(cls, match: re.Match) -> str:
        """Sanitize JWT tokens."""
        return "eyJ****"
    
    @classmethod
    def sanitize_password_url(cls, match: re.Match) -> str:
        """Sanitize password in URL."""
        param_name = match.group(1)
        return f"{param_name}=***"
    
    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Sanitize all PII in text.
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Sanitized text with PII masked
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Apply all patterns
        sanitized = text
        
        sanitized = cls.PATTERNS['email'].sub(cls.sanitize_email, sanitized)
        sanitized = cls.PATTERNS['phone'].sub(cls.sanitize_phone, sanitized)
        sanitized = cls.PATTERNS['credit_card'].sub(cls.sanitize_credit_card, sanitized)
        sanitized = cls.PATTERNS['aadhaar'].sub(cls.sanitize_aadhaar, sanitized)
        sanitized = cls.PATTERNS['pan'].sub(cls.sanitize_pan, sanitized)
        sanitized = cls.PATTERNS['ip_address'].sub(cls.sanitize_ip, sanitized)
        sanitized = cls.PATTERNS['api_key'].sub(cls.sanitize_api_key, sanitized)
        sanitized = cls.PATTERNS['jwt'].sub(cls.sanitize_jwt, sanitized)
        sanitized = cls.PATTERNS['password_in_url'].sub(cls.sanitize_password_url, sanitized)
        
        return sanitized


class PIIFilter(logging.Filter):
    """
    Logging filter that sanitizes PII.
    
    Add to logger handlers to automatically sanitize all log messages.
    
    Example:
        ```python
        import logging
        from backend.core.logging.pii_filter import PIIFilter
        
        logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.addFilter(PIIFilter())
        logger.addHandler(handler)
        
        # This will be sanitized automatically
        logger.info(f"User email: user@example.com")
        # Output: "User email: u***@example.com"
        ```
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by sanitizing PII.
        
        Args:
            record: Log record to filter
            
        Returns:
            Always True (doesn't block logging)
        """
        # Sanitize message
        if hasattr(record, 'msg') and record.msg:
            record.msg = PIISanitizer.sanitize(str(record.msg))
        
        # Sanitize args
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: PIISanitizer.sanitize(str(v))
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    PIISanitizer.sanitize(str(arg))
                    for arg in record.args
                )
        
        return True


def configure_pii_filtering():
    """
    Configure PII filtering for all loggers.
    
    Call this once at application startup.
    """
    # Add filter to root logger
    root_logger = logging.getLogger()
    pii_filter = PIIFilter()
    
    for handler in root_logger.handlers:
        handler.addFilter(pii_filter)
    
    logging.info("✓ PII sanitization configured for all logs")
