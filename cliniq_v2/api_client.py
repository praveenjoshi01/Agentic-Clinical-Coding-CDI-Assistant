"""
Singleton OpenAI client with runtime API key injection.

Provides a single shared OpenAI client instance across all cliniq_v2 modules.
The client must be configured with an API key before any module can make API calls.
"""

from typing import Optional

from openai import OpenAI


class OpenAIClient:
    """Singleton OpenAI client with runtime API key injection."""

    _instance: Optional["OpenAIClient"] = None
    _client: Optional[OpenAI] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self, api_key: str) -> None:
        """Set API key and initialize client. Called once at startup."""
        self._client = OpenAI(api_key=api_key)

    @property
    def client(self) -> OpenAI:
        """Return the configured OpenAI client.

        Raises:
            RuntimeError: If configure() has not been called yet.
        """
        if self._client is None:
            raise RuntimeError(
                "OpenAI client not configured. Call configure(api_key) first."
            )
        return self._client

    def validate_key(self) -> bool:
        """Test API key validity with a lightweight models.list() call."""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    @classmethod
    def clear(cls) -> None:
        """Reset singleton state. Useful for testing."""
        cls._instance = None
        cls._client = None
