"""Domain exceptions for the SEDIA integration."""


class SediaError(RuntimeError):
    """Base exception for the SEDIA integration."""


class SediaHTTPError(SediaError):
    """Raised after an unsuccessful HTTP response."""


class SediaResponseError(SediaError):
    """Raised when a response violates the contract."""
