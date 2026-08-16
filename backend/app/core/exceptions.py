class AppException(Exception):
    """Base exception for all application-level errors."""


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""


class ConflictError(AppException):
    """Raised when a resource conflict occurs (e.g., duplicate name)."""


class ValidationError(AppException):
    """Raised when input data fails business validation."""


class ConnectionError(AppException):
    """Raised when a connection to an external service fails."""


class ForbiddenError(AppException):
    """Raised when user lacks permission to perform an action."""


class ServiceUnavailableError(AppException):
    """Raised when an external service is unavailable."""
