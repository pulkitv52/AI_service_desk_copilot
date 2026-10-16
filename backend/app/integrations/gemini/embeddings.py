import asyncio
import hashlib
import math
from typing import Literal, Optional, Protocol, runtime_checkable
import httpx

from app.core.logging import get_logger
from app.models.knowledge import EMBEDDING_DIMENSION

logger = get_logger("embeddings")
EmbeddingTask = Literal["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]


def normalize_embedding(values: list[float], dimension: int) -> list[float]:
    if len(values) != dimension or not all(math.isfinite(v) for v in values):
        raise ValueError("Invalid embedding dimensions or values")
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("Invalid embedding norm")
    return [v / norm for v in values]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for vector embedding generation."""

    @property
    def profile(self) -> str: ...

    async def embed_text(
        self, text: str, *, task_type: EmbeddingTask = "RETRIEVAL_QUERY"
    ) -> list[float]:
        """Generate embedding vector for a single string."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple strings."""
        ...


class MockEmbeddingProvider:
    """Deterministic mock embedding provider generating normalized vectors."""

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension

    @property
    def profile(self) -> str:
        return f"mock-hash-v1:{self.dimension}"

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

    async def embed_text(
        self, text: str, *, task_type: EmbeddingTask = "RETRIEVAL_QUERY"
    ) -> list[float]:
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

    @property
    def profile(self) -> str:
        return f"gemini:{self.model}:{self.dimension}:retrieval-v1"

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=self.timeout)

    async def embed_text(
        self, text: str, *, task_type: EmbeddingTask = "RETRIEVAL_QUERY"
    ) -> list[float]:
        url = f"{self.base_url}/models/{self.model}:embedContent"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self.dimension,
            "taskType": task_type,
        }

        client = self._get_client()
        should_close = self._external_client is None
        try:
            for attempt in range(2):
                try:
                    response = await client.post(
                        url, json=payload, headers={"x-goog-api-key": self.api_key}
                    )
                    if (
                        response.status_code in {429, 500, 502, 503, 504}
                        and attempt == 0
                    ):
                        await asyncio.sleep(0.75)
                        continue
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 1:
                        raise
                    await asyncio.sleep(0.75)
            data = response.json()
            embedding = data.get("embedding", {}).get("values", [])
            return normalize_embedding(embedding, self.dimension)
        except Exception:
            logger.error("Gemini embedding request failed")
            raise RuntimeError("Gemini embedding request failed") from None
        finally:
            if should_close:
                await client.aclose()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        sem = asyncio.Semaphore(10)

        async def _bounded_embed(t: str) -> list[float]:
            async with sem:
                return await self.embed_text(t, task_type="RETRIEVAL_DOCUMENT")

        return await asyncio.gather(*[_bounded_embed(t) for t in texts])
