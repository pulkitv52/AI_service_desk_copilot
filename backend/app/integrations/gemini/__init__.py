from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.gemini.embeddings import (
    EmbeddingProvider,
    GeminiEmbeddingProvider,
    MockEmbeddingProvider,
)
from app.integrations.gemini.llm import (
    LLMProvider,
    GeminiLLMProvider,
    MockLLMProvider,
)

logger = get_logger("gemini_factory")

_singleton_embedding_provider: EmbeddingProvider | None = None
_singleton_llm_provider: LLMProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return active EmbeddingProvider based on Gemini API key availability."""
    global _singleton_embedding_provider
    if _singleton_embedding_provider is not None:
        return _singleton_embedding_provider

    cfg = get_settings()
    if cfg.gemini_api_key:
        logger.info("Initializing live GeminiEmbeddingProvider")
        _singleton_embedding_provider = GeminiEmbeddingProvider(
            api_key=cfg.gemini_api_key
        )
    else:
        logger.info("Gemini API key not configured; using MockEmbeddingProvider")
        _singleton_embedding_provider = MockEmbeddingProvider()

    return _singleton_embedding_provider


def reset_embedding_provider() -> None:
    """Reset singleton embedding provider for testing."""
    global _singleton_embedding_provider
    _singleton_embedding_provider = None


def get_llm_provider() -> LLMProvider:
    """Return active LLMProvider based on Gemini API key availability."""
    global _singleton_llm_provider
    if _singleton_llm_provider is not None:
        return _singleton_llm_provider

    cfg = get_settings()
    if cfg.gemini_api_key:
        logger.info("Initializing live GeminiLLMProvider")
        _singleton_llm_provider = GeminiLLMProvider(api_key=cfg.gemini_api_key)
    else:
        logger.info("Gemini API key not configured; using MockLLMProvider")
        _singleton_llm_provider = MockLLMProvider()

    return _singleton_llm_provider


def reset_llm_provider() -> None:
    """Reset singleton LLM provider for testing."""
    global _singleton_llm_provider
    _singleton_llm_provider = None


__all__ = [
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "MockEmbeddingProvider",
    "get_embedding_provider",
    "reset_embedding_provider",
    "LLMProvider",
    "GeminiLLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "reset_llm_provider",
]
