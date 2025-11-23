"""
HMAC Webhook Signature Signer

Provides HMAC-SHA256 signature generation and verification for webhooks.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class WebhookSigner:
    """
    HMAC-SHA256 webhook signature generator and verifier.
    
    Usage (sender side):
    ```python
    signer = WebhookSigner(secret="webhook_secret_key")
    payload = {"event": "trade.created", "data": {...}}
    signature = signer.sign(payload)
    
    # Send to subscriber with header:
    # X-Webhook-Signature: sha256={signature}
    ```
    
    Usage (receiver side):
    ```python
    signer = WebhookSigner(secret="webhook_secret_key")
    received_signature = request.headers.get("X-Webhook-Signature")
    payload = request.json()
    
    if signer.verify(payload, received_signature):
        # Process webhook
    else:
        # Reject as invalid
    ```
    """
    
    def __init__(self, secret: str):
        self.secret = secret.encode("utf-8")
    
    def sign(self, payload: str | Dict) -> str:
        """
        Generate HMAC-SHA256 signature for payload.
        
        Args:
            payload: Payload to sign (string or dict)
            
        Returns:
            Hex signature
        """
        # Convert dict to string if needed
        if isinstance(payload, dict):
            import json
            payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        
        # Generate HMAC
        signature = hmac.new(
            self.secret,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        
        return signature
    
    def verify(self, payload: str | Dict, signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature.
        
        Args:
            payload: Payload to verify
            signature: Signature to verify (can include "sha256=" prefix)
            
        Returns:
            True if signature is valid
        """
        # Remove "sha256=" prefix if present
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        # Generate expected signature
        expected_signature = self.sign(payload)
        
        # Constant-time comparison (prevent timing attacks)
        return hmac.compare_digest(expected_signature, signature)
    
    def get_signature_header(self, payload: str | Dict) -> Dict[str, str]:
        """
        Get signature as HTTP header.
        
        Args:
            payload: Payload to sign
            
        Returns:
            Dict with X-Webhook-Signature header
        """
        signature = self.sign(payload)
        return {"X-Webhook-Signature": f"sha256={signature}"}
