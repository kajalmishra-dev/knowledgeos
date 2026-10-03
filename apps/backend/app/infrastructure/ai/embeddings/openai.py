from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        dimensions: int,
        timeout: float = 60.0,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        batch_size = 64
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            payload: dict[str, object] = {"model": self._model, "input": batch}
            if self._model.startswith("text-embedding-3"):
                payload["dimensions"] = self._dimensions
            response = await self._client.post("/embeddings", json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception("Embedding provider request failed")
                raise RuntimeError("Embedding provider request failed.") from exc
            data = response.json()["data"]
            data.sort(key=lambda item: item["index"])
            vectors.extend(item["embedding"] for item in data)
        return vectors

    async def aclose(self) -> None:
        await self._client.aclose()
