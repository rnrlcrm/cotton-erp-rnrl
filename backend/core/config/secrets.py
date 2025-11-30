"""
Google Cloud Secret Manager Integration

Replaces .env file with GCP Secret Manager for production.
Environment variable names stay EXACTLY the same (NO business logic changes).

Benefits for 15-year architecture:
- Automatic rotation
- Full audit trail
- IAM-based access control
- Versioning and rollback
- No secrets in code/env files

Usage:
    # Development (still uses .env)
    python -m uvicorn main:app --reload
    
    # Production (uses GCP Secret Manager)
    export USE_SECRET_MANAGER=true
    export GCP_PROJECT_ID=cotton-erp-prod
    python -m uvicorn main:app
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Lazy import GCP client (only needed in production)
_secret_client = None


def _get_secret_client():
    """Get or create Secret Manager client."""
    global _secret_client
    if _secret_client is None:
        try:
            from google.cloud import secretmanager
            _secret_client = secretmanager.SecretManagerServiceClient()
        except ImportError:
            logger.warning(
                "google-cloud-secret-manager not installed. "
                "Install with: pip install google-cloud-secret-manager"
            )
            raise
    return _secret_client


@lru_cache(maxsize=128)
def get_secret(
    secret_name: str,
    project_id: Optional[str] = None,
    version: str = "latest"
) -> str:
    """
    Get secret from GCP Secret Manager.
    
    Results are cached for performance (secrets don't change often).
    
    Args:
        secret_name: Name of the secret (e.g., "DATABASE_URL")
        project_id: GCP project ID (defaults to env var)
        version: Secret version (default: latest)
        
    Returns:
        Secret value as string
        
    Example:
        ```python
        database_url = get_secret("DATABASE_URL")
        ```
    """
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable required")
    
    client = _get_secret_client()
    
    # Build secret name
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to get secret {secret_name}: {e}")
        raise


def load_secrets_from_gcp(
    secret_names: list[str],
    project_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Load multiple secrets from GCP Secret Manager.
    
    Args:
        secret_names: List of secret names to load
        project_id: GCP project ID
        
    Returns:
        Dictionary of secret_name -> value
    """
    secrets = {}
    for name in secret_names:
        try:
            secrets[name] = get_secret(name, project_id)
        except Exception as e:
            logger.error(f"Failed to load secret {name}: {e}")
            # Don't fail - allow partial loading
    
    return secrets


def get_env_or_secret(
    var_name: str,
    default: Optional[str] = None,
    use_secret_manager: Optional[bool] = None
) -> Optional[str]:
    """
    Get value from environment variable OR GCP Secret Manager.
    
    This is the MAIN function to use - automatically handles dev vs prod.
    
    Args:
        var_name: Variable name (same for env and secret)
        default: Default value if not found
        use_secret_manager: Force SM usage (defaults to USE_SECRET_MANAGER env var)
        
    Returns:
        Value from env var or Secret Manager
        
    Example:
        ```python
        # In development: reads from .env
        # In production: reads from Secret Manager
        DATABASE_URL = get_env_or_secret("DATABASE_URL")
        ```
    """
    # Check if we should use Secret Manager
    if use_secret_manager is None:
        use_secret_manager = os.getenv("USE_SECRET_MANAGER", "false").lower() == "true"
    
    if use_secret_manager:
        # Production: use Secret Manager
        try:
            return get_secret(var_name)
        except Exception as e:
            logger.warning(f"Secret Manager failed for {var_name}, falling back to env: {e}")
            # Fallback to environment variable
            return os.getenv(var_name, default)
    else:
        # Development: use environment variable
        return os.getenv(var_name, default)


# Pre-defined secret mappings for Cotton ERP
REQUIRED_SECRETS = [
    "DATABASE_URL",
    "SECRET_KEY",
    "REDIS_URL",
    "OPENAI_API_KEY",
]

OPTIONAL_SECRETS = [
    "SENTRY_DSN",
    "SLACK_WEBHOOK_URL",
    "SMTP_PASSWORD",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
]


def initialize_secrets() -> Dict[str, Any]:
    """
    Initialize all secrets at application startup.
    
    This loads secrets into environment variables so existing code works unchanged.
    
    Returns:
        Dictionary of loaded secrets (for logging/debugging)
    """
    use_sm = os.getenv("USE_SECRET_MANAGER", "false").lower() == "true"
    
    if not use_sm:
        logger.info("Using environment variables (development mode)")
        return {"mode": "env_vars"}
    
    logger.info("Loading secrets from GCP Secret Manager")
    
    # Load all secrets
    all_secrets = REQUIRED_SECRETS + OPTIONAL_SECRETS
    loaded = load_secrets_from_gcp(all_secrets)
    
    # Set as environment variables (so existing code works)
    for name, value in loaded.items():
        os.environ[name] = value
    
    # Verify required secrets
    missing = [s for s in REQUIRED_SECRETS if s not in loaded]
    if missing:
        raise ValueError(f"Required secrets missing: {missing}")
    
    logger.info(f"Loaded {len(loaded)} secrets from Secret Manager")
    
    return {
        "mode": "secret_manager",
        "loaded_count": len(loaded),
        "required_secrets": len([s for s in REQUIRED_SECRETS if s in loaded]),
        "optional_secrets": len([s for s in OPTIONAL_SECRETS if s in loaded]),
    }


def rotate_secret(
    secret_name: str,
    new_value: str,
    project_id: Optional[str] = None
) -> str:
    """
    Rotate a secret (create new version).
    
    Args:
        secret_name: Name of secret to rotate
        new_value: New secret value
        project_id: GCP project ID
        
    Returns:
        Version ID of new secret
        
    Example:
        ```python
        # Rotate database password
        new_version = rotate_secret("DATABASE_PASSWORD", new_password)
        ```
    """
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT_ID")
    
    client = _get_secret_client()
    
    # Add new version
    parent = f"projects/{project_id}/secrets/{secret_name}"
    
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {"data": new_value.encode("UTF-8")},
        }
    )
    
    # Clear cache so next call gets new version
    get_secret.cache_clear()
    
    logger.info(f"Rotated secret {secret_name}: {response.name}")
    
    return response.name
