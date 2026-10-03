import logging

from app.core.config import Settings
from app.infrastructure.ai.chat.base import ChatProvider
from app.infrastructure.ai.chat.extractive import ExtractiveChatProvider
from app.infrastructure.ai.chat.openai import OpenAIChatProvider
from app.infrastructure.ai.embeddings.base import EmbeddingProvider
from app.infrastructure.ai.embeddings.local import LocalEmbeddingProvider
from app.infrastructure.ai.embeddings.openai import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "openai" and settings.openai_api_key:
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    if settings.embedding_provider == "openai" and not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is empty; falling back to local embeddings")
    return LocalEmbeddingProvider(settings.embedding_dimensions)


def create_chat_provider(settings: Settings) -> ChatProvider:
    if settings.chat_provider == "openai" and settings.openai_api_key:
        return OpenAIChatProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.chat_model,
        )
    if settings.chat_provider == "openai" and not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is empty; falling back to extractive answers")
    return ExtractiveChatProvider()
