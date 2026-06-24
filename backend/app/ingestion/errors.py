"""Ingestion error types."""


class IngestionError(Exception):
    """Base class for all ingestion failures."""


class UpstreamError(IngestionError):
    """An external provider could not be reached or returned a hard error."""

    def __init__(self, provider: str, message: str, status: int | None = None) -> None:
        self.provider = provider
        self.status = status
        super().__init__(f"[{provider}] {message}" + (f" (status={status})" if status else ""))


class CircuitOpenError(UpstreamError):
    """The circuit breaker is open and there is no cached data to fall back to."""
