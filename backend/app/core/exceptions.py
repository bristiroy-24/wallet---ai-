"""
app/core/exceptions.py
───────────────────────
Domain-level exception hierarchy.

Raising these anywhere in the service/repo layer lets the global
FastAPI exception handler convert them to proper HTTP responses
without scattering HTTPException imports throughout business logic.
"""

from typing import Any, Optional


class AppError(Exception):
    """Base application error."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: Optional[str] = None, **kwargs: Any) -> None:
        self.detail = detail or self.__class__.detail
        self.extra = kwargs
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    detail = "Resource already exists."


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action."


class ValidationError(AppError):
    status_code = 422
    detail = "Validation failed."


class AIServiceError(AppError):
    status_code = 502
    detail = "AI service request failed."
