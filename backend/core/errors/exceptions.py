from __future__ import annotations

class DomainError(Exception):
    code = "domain_error"

class AuthError(DomainError):
    code = "auth_error"

class AuthorizationException(DomainError):
    """Raised when user is not authorized to perform an action."""
    code = "authorization_error"

class BusinessRuleException(DomainError):
    """Raised when business rule is violated."""
    code = "business_rule_violation"

class ValidationError(DomainError):
    code = "validation_error"

class NotFoundError(DomainError):
    code = "not_found"

class BadRequestException(DomainError):
    code = "bad_request"

class NotFoundException(DomainError):
    code = "not_found"
