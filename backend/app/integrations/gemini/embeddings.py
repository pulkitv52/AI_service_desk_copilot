import hashlib
import math
from typing import Optional, Protocol, runtime_checkable
import httpx

from app.core.logging import get_logger
from app.models.knowledge import EMBEDDING_DIMENSION

logger = get_logger("embeddings")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for vector embedding generation."""

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single string."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple strings."""
        ...


class MockEmbeddingProvider:
    """Deterministic mock embedding provider generating normalized vectors."""

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        # Hash individual tokens so matching keywords activate identical dimensions
        vec = [0.0] * self.dimension
        tokens = text.lower().split()
        if not tokens:
            tokens = ["empty"]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for byte_idx, val in enumerate(digest):
                idx = (byte_idx * 31 + digest[0]) % self.dimension
                vec[idx] += (val - 128) / 128.0

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return [1.0 / math.sqrt(self.dimension)] * self.dimension

    async def embed_text(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]


class GeminiEmbeddingProvider:
    """Generates embeddings using Google Gemini gemini-embedding-001 REST API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimension: int = EMBEDDING_DIMENSION,
        timeout_seconds: float = 15.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.timeout = timeout_seconds
        self._external_client = client
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=self.timeout)

    async def embed_text(self, text: str) -> list[float]:
        url = f"{self.base_url}/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self.dimension,
        }

        client = self._get_client()
        should_close = self._external_client is None
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", {}).get("values", [])
            return embedding
        except Exception as exc:
            logger.error("Gemini embedding API error: %s", exc)
            raise RuntimeError(f"Gemini embedding API failed: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        sem = asyncio.Semaphore(10)

        async def _bounded_embed(t: str) -> list[float]:
            async with sem:
                return await self.embed_text(t)

        return await asyncio.gather(*[_bounded_embed(t) for t in texts])
