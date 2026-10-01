from pydantic import ValidationError

from app.config import get_llm_settings
from app.schemas.remediations import GeneratedRemediationDraft

from .base import LLMProviderError


class GeminiLLMService:
    provider_name = "google-gemini"

    def __init__(self, *, api_key: str, model_id: str, timeout_ms: int) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._timeout_ms = timeout_ms
        self._types = None
        self._client = None

    @property
    def model_id(self) -> str:
        return self._model_id

    async def generate_remediation(self, prompt: str) -> GeneratedRemediationDraft:
        if not self._api_key:
            raise LLMProviderError(
                "llm_not_configured",
                "Gemini is not configured. Add GEMINI_API_KEY to backend/.env and restart the API.",
                retryable=False,
            )
        if self._client is None:
            from google import genai
            from google.genai import types

            self._types = types
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model_id,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=_gemini_json_schema(),
                    temperature=0.2,
                    max_output_tokens=2200,
                ),
            )
        except Exception as error:
            error_name = type(error).__name__.lower()
            if "timeout" in error_name:
                raise LLMProviderError(
                    "llm_timeout",
                    "Gemini did not respond before the generation timeout. Try again.",
                    retryable=True,
                ) from error
            raise LLMProviderError(
                "llm_provider_unavailable",
                "Gemini could not generate the intervention. Check the provider configuration and try again.",
                retryable=True,
            ) from error

        try:
            if isinstance(response.parsed, GeneratedRemediationDraft):
                return response.parsed
            if not response.text:
                raise ValueError("empty model output")
            return GeneratedRemediationDraft.model_validate_json(response.text)
        except (ValidationError, ValueError, TypeError) as error:
            raise LLMProviderError(
                "llm_malformed_output",
                "Gemini returned an invalid intervention structure. No remediation was saved.",
                retryable=True,
            ) from error


async def get_llm_service() -> GeminiLLMService:
    settings = get_llm_settings()
    return GeminiLLMService(
        api_key=settings.api_key,
        model_id=settings.model,
        timeout_ms=settings.timeout_ms,
    )


def _gemini_json_schema() -> dict:
    """Return Pydantic's schema without metadata rejected by Gemini's schema endpoint."""
    return _remove_unsupported_schema_fields(GeneratedRemediationDraft.model_json_schema())


def _remove_unsupported_schema_fields(value):
    if isinstance(value, dict):
        return {
            key: _remove_unsupported_schema_fields(item)
            for key, item in value.items()
            if key != "additionalProperties"
        }
    if isinstance(value, list):
        return [_remove_unsupported_schema_fields(item) for item in value]
    return value
