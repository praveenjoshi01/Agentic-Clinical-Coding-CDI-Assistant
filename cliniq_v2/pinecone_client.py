"""
Singleton Pinecone client with runtime API key injection.

Provides a single shared Pinecone client instance across all cliniq_v2 modules.
The client must be configured with an API key before any module can make API calls.
Gracefully handles missing pinecone package -- importable even without pinecone installed.
"""

from typing import Optional

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None


class PineconeClient:
    """Singleton Pinecone client with runtime API key injection."""

    _instance: Optional["PineconeClient"] = None
    _client: Optional[object] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self, api_key: str) -> None:
        """Set API key and initialize Pinecone client. Called once at startup."""
        if Pinecone is None:
            raise ImportError(
                "pinecone package not installed. "
                "Install with: pip install 'pinecone>=8.0.0'"
            )
        self._client = Pinecone(api_key=api_key)

    @property
    def client(self):
        """Return the configured Pinecone client.

        Raises:
            RuntimeError: If configure() has not been called yet.
        """
        if self._client is None:
            raise RuntimeError(
                "Pinecone client not configured. Call configure(api_key) first."
            )
        return self._client

    def validate_key(self) -> bool:
        """Test API key validity with a lightweight list_indexes() call."""
        try:
            self.client.list_indexes()
            return True
        except Exception:
            return False

    @classmethod
    def clear(cls) -> None:
        """Reset singleton state. Useful for testing."""
        cls._instance = None
        cls._client = None
