from typing import Protocol


class ChatProvider(Protocol):
    name: str
    supports_generation: bool

    async def complete(self, *, system: str, user: str) -> str: ...
