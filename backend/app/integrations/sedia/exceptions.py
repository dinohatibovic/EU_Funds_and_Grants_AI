"""Domain exceptions for the SEDIA integration."""

from __future__ import annotations


class SediaError(RuntimeError):
    """Base exception for the SEDIA integration."""


class SediaHTTPError(SediaError):
    """Raised after an unsuccessful HTTP operation."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)

        self.status_code = status_code
        self.retryable = retryable


class SediaResponseError(SediaError):
    """Raised when a response violates the contract."""
