from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

from src.application.protocols.llm import (LlmApiError, LlmRequest,
                                           LlmResponse, LlmTimeoutError)
from src.config.llm.config import OpenRouterConfig
from src.infrastructure.llm.open_router.model_mapper import \
    OpenRouterModelMapper
from src.infrastructure.llm.open_router.requests import (
    MessageRole, OpenRouterApiRequest, OpenRouterRequestHeaders,
    OpenRouterRequestMessage, ResponseFormat)
from src.infrastructure.llm.open_router.response_parser import \
    OpenRouterResponseParser
from src.logger.factories import get_generic_logger


class OpenRouterClient:
    _logger = get_generic_logger(__name__.removeprefix("src."))
    _config: OpenRouterConfig
    _http_client: httpx.AsyncClient | None
    _is_connected: bool
    _max_reconnect_attempts: int
    _reconnect_delay_seconds: float
    _response_format: ResponseFormat | None

    def __init__(
        self,
        config: OpenRouterConfig,
        max_reconnect_attempts: int = 3,
        reconnect_delay_seconds: float = 1.0,
        response_format: ResponseFormat | None = None,
    ) -> None:
        self._config = config
        self._http_client = None
        self._is_connected = False
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self._response_format = response_format

    async def connect(self) -> None:
        if self._is_connected:
            return

        try:
            import httpx
        except ImportError as e:
            raise ImportError(
                "httpx is required for OpenRouterClient. Install with: pip install httpx"
            ) from e

        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout),
        )
        self._is_connected = True
        self._logger.debug("OpenRouter client connected")

    async def disconnect(self) -> None:
        if not self._is_connected or self._http_client is None:
            return

        try:
            await self._http_client.aclose()
        except Exception as e:
            self._logger.warning(f"Error closing HTTP client: {e}")
        finally:
            self._http_client = None
            self._is_connected = False
            self._logger.debug("OpenRouter client disconnected")

    async def _ensure_connected(self) -> httpx.AsyncClient:
        if not self._is_connected or self._http_client is None:
            await self.connect()

        assert self._http_client is not None
        return self._http_client

    async def _reconnect(self) -> httpx.AsyncClient:
        self._logger.warning("Reconnecting OpenRouter client")
        await self.disconnect()

        for attempt in range(1, self._max_reconnect_attempts + 1):
            try:
                await self.connect()
                assert self._http_client is not None
                return self._http_client
            except Exception as e:
                if attempt == self._max_reconnect_attempts:
                    raise LlmApiError(
                        f"Failed to reconnect after {self._max_reconnect_attempts} attempts: {e}"
                    ) from e
                self._logger.warning(
                    f"Reconnection attempt {attempt}/{self._max_reconnect_attempts} failed: {e}"
                )
                await asyncio.sleep(self._reconnect_delay_seconds * attempt)

        raise LlmApiError("Reconnection failed")

    def _is_transient_error(self, error: Exception) -> bool:
        import httpx

        if isinstance(error, httpx.NetworkError):
            return True
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            return 500 <= status_code < 600 or status_code == 429
        if isinstance(error, httpx.TimeoutException):
            return True
        return False

    def _is_retryable_error(self, error: Exception) -> bool:
        if isinstance(error, LlmTimeoutError):
            return True
        if isinstance(error, LlmApiError):
            if error.status_code is not None:
                return 500 <= error.status_code < 600 or error.status_code == 429
            return False
        return self._is_transient_error(error)

    def _parse_response(self, data: dict[str, object], request: LlmRequest) -> LlmResponse:
        api_response = OpenRouterResponseParser.parse(data)
        return OpenRouterResponseParser.to_llm_response(api_response, request)

    async def _handle_timeout_error(
        self, error: httpx.TimeoutException, attempt: int
    ) -> tuple[httpx.AsyncClient, Exception]:
        timeout_error = LlmTimeoutError(f"Request timed out: {error}")
        if attempt < self._max_reconnect_attempts:
            self._logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
            await asyncio.sleep(self._reconnect_delay_seconds * (attempt + 1))
            return await self._reconnect(), timeout_error
        raise timeout_error from error

    async def _handle_http_error(
        self, error: httpx.HTTPStatusError, attempt: int
    ) -> tuple[httpx.AsyncClient, Exception]:
        if self._is_retryable_error(error) and attempt < self._max_reconnect_attempts:
            self._logger.warning(
                f"HTTP error {error.response.status_code} on attempt {attempt + 1}, retrying..."
            )
            await asyncio.sleep(self._reconnect_delay_seconds * (attempt + 1))
            return await self._reconnect(), error
        raise LlmApiError(str(error), error.response.status_code) from error

    async def _handle_network_error(
        self, error: httpx.NetworkError, attempt: int
    ) -> tuple[httpx.AsyncClient, Exception]:
        if attempt < self._max_reconnect_attempts:
            self._logger.warning(f"Network error on attempt {attempt + 1}, reconnecting...")
            await asyncio.sleep(self._reconnect_delay_seconds * (attempt + 1))
            return await self._reconnect(), error
        raise LlmApiError(
            f"Network error after {self._max_reconnect_attempts} attempts: {error}"
        ) from error

    async def complete(self, request: LlmRequest) -> LlmResponse:
        import httpx

        client = await self._ensure_connected()

        openrouter_model = OpenRouterModelMapper.to_openrouter_model(request.model_id)

        headers = OpenRouterRequestHeaders(api_key=self._config.api_key)

        messages = [
            OpenRouterRequestMessage(role=MessageRole.SYSTEM, content=request.system_prompt),
            OpenRouterRequestMessage(role=MessageRole.USER, content=request.user_prompt),
        ]

        payload = OpenRouterApiRequest(
            model=openrouter_model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            response_format=self._response_format,
        )

        last_error: Exception | None = None

        for attempt in range(self._max_reconnect_attempts + 1):
            try:
                response = await client.post(
                    f"{self._config.base_url}/chat/completions",
                    headers=headers.to_dict(),
                    json=payload.to_dict(),
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get(
                        "message", f"HTTP {response.status_code}"
                    )
                    api_error = LlmApiError(error_message, response.status_code)

                    if (
                        self._is_retryable_error(api_error)
                        and attempt < self._max_reconnect_attempts
                    ):
                        self._logger.warning(
                            f"Transient error {response.status_code} on attempt {attempt + 1}, retrying..."
                        )
                        await asyncio.sleep(self._reconnect_delay_seconds * (attempt + 1))
                        client = await self._reconnect()
                        last_error = api_error
                        continue

                    raise api_error

                data = response.json()
                return self._parse_response(data, request)

            except httpx.TimeoutException as e:
                client, last_error = await self._handle_timeout_error(e, attempt)
                continue

            except httpx.HTTPStatusError as e:
                client, last_error = await self._handle_http_error(e, attempt)
                continue

            except httpx.NetworkError as e:
                client, last_error = await self._handle_network_error(e, attempt)
                continue

            except Exception as e:
                if isinstance(e, LlmApiError | LlmTimeoutError):
                    raise
                raise LlmApiError(f"Request failed: {e}") from e

        if last_error:
            raise LlmApiError(
                f"Request failed after {self._max_reconnect_attempts} attempts"
            ) from last_error
        raise LlmApiError("Request failed")

    async def close(self) -> None:
        await self.disconnect()

    async def __aenter__(self) -> OpenRouterClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        await self.close()
