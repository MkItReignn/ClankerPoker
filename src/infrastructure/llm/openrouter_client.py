"""OpenRouter LLM client implementation."""

from __future__ import annotations

import logging

from src.application.protocols.llm import (LlmApiError, LlmRequest,
                                           LlmResponse, LlmTimeoutError)
from src.config.llm.config import OpenRouterConfig

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """OpenRouter API client for LLM completions.

    Implements the LlmClient protocol using OpenRouter's API.
    """

    def __init__(self, config: OpenRouterConfig) -> None:
        """Initialize the OpenRouter client.

        Args:
            config: Client configuration.
        """
        self._config = config
        self._http_client: object | None = None

    async def _ensure_client(self) -> object:
        """Ensure HTTP client is initialized.

        Returns the httpx client, creating it if needed.
        """
        if self._http_client is None:
            try:
                import httpx

                self._http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self._config.timeout),
                )
            except ImportError:
                raise ImportError(
                    "httpx is required for OpenRouterClient. " "Install with: pip install httpx"
                )
        return self._http_client

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Send a completion request to OpenRouter.

        Args:
            request: The LLM request.

        Returns:
            The LLM response.

        Raises:
            LlmApiError: If the API returns an error.
            LlmTimeoutError: If the request times out.
        """
        import httpx

        client = await self._ensure_client()
        assert isinstance(client, httpx.AsyncClient)

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": request.model_id,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        try:
            response = await client.post(
                f"{self._config.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("error", {}).get(
                    "message", f"HTTP {response.status_code}"
                )
                raise LlmApiError(error_message, response.status_code)

            data = response.json()

            # Extract response content
            choices = data.get("choices", [])
            if not choices:
                raise LlmApiError("No choices in response")

            content = choices[0].get("message", {}).get("content", "")
            finish_reason = choices[0].get("finish_reason", "unknown")

            # Extract usage
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            return LlmResponse(
                content=content,
                model_id=data.get("model", request.model_id),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                finish_reason=finish_reason,
                raw_response=data,
            )

        except httpx.TimeoutException as e:
            raise LlmTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise LlmApiError(str(e), e.response.status_code)
        except Exception as e:
            if isinstance(e, (LlmApiError, LlmTimeoutError)):
                raise
            raise LlmApiError(f"Request failed: {e}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            import httpx

            if isinstance(self._http_client, httpx.AsyncClient):
                await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> OpenRouterClient:
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()
