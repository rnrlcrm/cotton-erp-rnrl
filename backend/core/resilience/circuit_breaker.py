"""
Circuit Breaker Pattern

Implements circuit breaker for external API calls (15-year resilience).
Prevents cascade failures when external services are down.

Uses tenacity library for retries with exponential backoff.

NO business logic - pure infrastructure.
"""

from typing import Callable, Any, Optional
from functools import wraps
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Circuit breaker is open - service unavailable."""
    pass


def circuit_breaker(
    max_attempts: int = 3,
    wait_multiplier: int = 1,
    wait_max: int = 10,
    exceptions: tuple = (Exception,),
):
    """
    Circuit breaker decorator for external API calls.
    
    Automatically retries failed calls with exponential backoff.
    After max_attempts, raises CircuitBreakerError.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_multiplier: Exponential backoff multiplier (seconds)
        wait_max: Maximum wait time between retries (seconds)
        exceptions: Tuple of exceptions to retry on
        
    Returns:
        Decorator function
        
    Example:
        ```python
        from backend.core.resilience.circuit_breaker import circuit_breaker
        import httpx
        
        @circuit_breaker(max_attempts=3, exceptions=(httpx.HTTPError,))
        async def call_external_api():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com")
                return response.json()
        
        # If API fails, will retry 3 times with exponential backoff
        # If still fails, raises CircuitBreakerError
        ```
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_multiplier, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                logger.error(
                    f"Circuit breaker: {func.__name__} failed after {max_attempts} attempts",
                    exc_info=True
                )
                raise CircuitBreakerError(
                    f"Service unavailable: {func.__name__} failed after {max_attempts} attempts"
                ) from e
        
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_multiplier, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.error(
                    f"Circuit breaker: {func.__name__} failed after {max_attempts} attempts",
                    exc_info=True
                )
                raise CircuitBreakerError(
                    f"Service unavailable: {func.__name__} failed after {max_attempts} attempts"
                ) from e
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Pre-configured circuit breakers for common scenarios

def api_circuit_breaker(func: Callable) -> Callable:
    """
    Circuit breaker for external API calls.
    
    - 3 attempts
    - Exponential backoff: 1s, 2s, 4s
    - Retries on HTTP errors
    """
    import httpx
    return circuit_breaker(
        max_attempts=3,
        wait_multiplier=1,
        wait_max=10,
        exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )(func)


def database_circuit_breaker(func: Callable) -> Callable:
    """
    Circuit breaker for database calls.
    
    - 2 attempts (databases should be fast)
    - Short backoff: 0.5s, 1s
    - Retries on connection errors
    """
    from sqlalchemy.exc import OperationalError, DBAPIError
    return circuit_breaker(
        max_attempts=2,
        wait_multiplier=0.5,
        wait_max=2,
        exceptions=(OperationalError, DBAPIError),
    )(func)


def redis_circuit_breaker(func: Callable) -> Callable:
    """
    Circuit breaker for Redis calls.
    
    - 2 attempts
    - Fast backoff: 0.1s, 0.2s
    - Retries on connection errors
    """
    import redis.exceptions
    return circuit_breaker(
        max_attempts=2,
        wait_multiplier=0.1,
        wait_max=1,
        exceptions=(
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
        ),
    )(func)


def ai_circuit_breaker(func: Callable) -> Callable:
    """
    Circuit breaker for AI API calls (OpenAI, Anthropic, etc).
    
    - 5 attempts (AI APIs can be flaky)
    - Exponential backoff: 2s, 4s, 8s, 16s, 32s
    - Retries on rate limit and server errors
    """
    import httpx
    return circuit_breaker(
        max_attempts=5,
        wait_multiplier=2,
        wait_max=60,
        exceptions=(httpx.HTTPError,),
    )(func)
