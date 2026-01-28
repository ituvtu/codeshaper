class UpstreamServiceError(Exception):
    """Raised when Hugging Face API returns an error status."""


class UpstreamTimeoutError(Exception):
    """Raised when a request to Hugging Face exceeds the timeout."""
