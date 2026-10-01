from typing import Protocol

from app.schemas.remediations import GeneratedRemediationDraft


class LLMProviderError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class LLMService(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    async def generate_remediation(self, prompt: str) -> GeneratedRemediationDraft: ...
