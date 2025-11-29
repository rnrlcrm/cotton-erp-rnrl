"""
Idempotency middleware for preventing duplicate requests.

This is INFRASTRUCTURE ONLY - no business logic changes.
Validates idempotency keys and caches responses in Redis.

Usage:
    Add header: Idempotency-Key: <unique-uuid>
    
    First request: Executes normally, caches response
    Duplicate request: Returns cached response immediately
"""

from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json
import hashlib
import redis.asyncio as aioredis
from datetime import timedelta

from backend.core.settings.config import settings


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle idempotent requests using Redis cache.
    
    Safe HTTP methods (GET, HEAD, OPTIONS) are always idempotent.
    Unsafe methods (POST, PUT, PATCH, DELETE) require Idempotency-Key header.
    """
    
    # Methods that require idempotency keys
    IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    # Safe methods that don't need idempotency keys
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    # How long to cache idempotency responses (24 hours)
    CACHE_TTL = timedelta(hours=24)
    
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
    
    async def get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    def _generate_cache_key(self, idempotency_key: str, request: Request) -> str:
        """
        Generate cache key from idempotency key and request details.
        
        Include method + path to prevent key reuse across different endpoints.
        """
        # Hash the combination to keep keys consistent length
        key_data = f"{request.method}:{request.url.path}:{idempotency_key}"
        hash_suffix = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"idempotency:{hash_suffix}"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with idempotency checking.
        
        NO BUSINESS LOGIC - pure caching layer.
        """
        # Skip idempotency for safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)
        
        # Get idempotency key from header
        idempotency_key = request.headers.get("Idempotency-Key")
        
        # For unsafe methods, idempotency key is optional but recommended
        # We won't enforce it to avoid breaking existing clients
        if not idempotency_key:
            # No key provided - process normally without caching
            return await call_next(request)
        
        # Check cache for existing response
        redis = await self.get_redis()
        cache_key = self._generate_cache_key(idempotency_key, request)
        
        cached_response = await redis.get(cache_key)
        
        if cached_response:
            # Return cached response - this is a duplicate request
            cached_data = json.loads(cached_response)
            return JSONResponse(
                content=cached_data["body"],
                status_code=cached_data["status_code"],
                headers={
                    **cached_data.get("headers", {}),
                    "X-Idempotency-Cache": "HIT"
                }
            )
        
        # Process request normally
        response = await call_next(request)
        
        # Cache successful responses only (2xx and 3xx)
        if 200 <= response.status_code < 400:
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Parse JSON body
            try:
                body_json = json.loads(response_body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Can't cache non-JSON responses
                body_json = None
            
            if body_json is not None:
                # Cache response
                cache_data = {
                    "status_code": response.status_code,
                    "body": body_json,
                    "headers": dict(response.headers)
                }
                
                await redis.setex(
                    cache_key,
                    int(self.CACHE_TTL.total_seconds()),
                    json.dumps(cache_data)
                )
            
            # Recreate response with consumed body
            return JSONResponse(
                content=body_json if body_json is not None else response_body.decode(),
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    "X-Idempotency-Cache": "MISS"
                }
            )
        
        # Don't cache error responses
        return response
    
    async def cleanup(self):
        """Close Redis connection on shutdown."""
        if self._redis:
            await self._redis.close()


async def get_idempotency_middleware(app):
    """Factory function to create idempotency middleware."""
    return IdempotencyMiddleware(app)
