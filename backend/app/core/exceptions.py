class AppException(Exception):
    """Base exception for all application-level errors."""
    pass

class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""
    pass

class ConflictError(AppException):
    """Raised when a resource conflict occurs (e.g., duplicate name)."""
    pass

class ValidationError(AppException):
    """Raised when input data fails business validation."""
    pass

class ConnectionError(AppException):
    """Raised when a connection to an external service fails."""
    pass

class ForbiddenError(AppException):
    """Raised when user lacks permission to perform an action."""
    pass

class ServiceUnavailableError(AppException):
    """Raised when an external service is unavailable."""
    pass