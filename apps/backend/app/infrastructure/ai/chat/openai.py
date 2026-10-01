from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OpenAIChatProvider:
    name = "openai"
    supports_generation = True

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def complete(self, *, system: str, user: str) -> str:
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.exception("Chat provider request failed")
            raise RuntimeError("Chat provider request failed.") from exc
        content = response.json()["choices"][0]["message"]["content"]
        return (content or "").strip()

    async def aclose(self) -> None:
        await self._client.aclose()
