class ExtractiveChatProvider:
    """Non-generative fallback used when no chat API is configured."""

    name = "extractive"
    supports_generation = False

    async def complete(self, *, system: str, user: str) -> str:
        del system, user
        raise RuntimeError("Extractive provider does not generate completions.")
