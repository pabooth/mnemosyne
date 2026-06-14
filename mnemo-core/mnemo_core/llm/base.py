from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        """Send a system + user prompt and return the text response."""
        ...
