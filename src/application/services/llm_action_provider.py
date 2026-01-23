"""Generic LLM-based action provider with retry logic."""

from __future__ import annotations

from typing import Callable, Generic, Self, TypeVar, cast

from src.application.protocols.llm import LlmClient, LlmError, LlmRequest
from src.application.protocols.player import ActionResponse, PlayerConfig
from src.application.protocols.response import ParseError, ParseFailure, ParseResult, ParseSuccess
from src.config.poker.action_provider import ActionProviderConfig
from src.config.poker.prompt import PokerPromptConfig
from src.domain.models.llm_model import LlmModel
from src.logger.factories import get_generic_logger

# Generic type variables
TContext = TypeVar("TContext")
TAvailableActions = TypeVar("TAvailableActions")
TAction = TypeVar("TAction")
TNarration = TypeVar("TNarration")
TPlayerInfo = TypeVar("TPlayerInfo", bound=PlayerConfig, default=PlayerConfig)


class LlmActionProvider(Generic[TContext, TAvailableActions, TAction, TNarration, TPlayerInfo]):
    """Generic LLM-based action provider.

    Composes a prompt formatter, LLM client, and response parser to
    generate actions from LLM responses. Includes retry logic for
    handling parse failures.

    Type Parameters:
        TContext: The context type for decisions.
        TAvailableActions: The available actions type.
        TAction: The action type to return.
        TNarration: The narration type for structured output.
        TPlayerInfo: The player info type for prompt formatting (typically PlayerConfig).
    """

    _logger = get_generic_logger(__name__.removeprefix("src."))

    def __init__(
        self,
        llm_client: LlmClient,
        prompt_formatter: Callable[[TContext, TAvailableActions, TPlayerInfo], tuple[str, str]],
        response_parser: Callable[[str, TAvailableActions], ParseResult[TAction, TNarration]],
        fallback_selector: Callable[[TAvailableActions], TAction | None] | None = None,
        *,
        config: ActionProviderConfig,
        prompt_config: PokerPromptConfig | None = None,
    ) -> None:
        """Initialize the LLM action provider.

        Args:
            llm_client: The LLM client for making API calls.
            prompt_formatter: Function that takes (context, available_actions, player_config)
                and returns (system_prompt, user_prompt) tuple.
            response_parser: Function to parse LLM responses.
            fallback_selector: Optional function to select fallback action on failure.
            config: Configuration for the action provider.
            prompt_config: Optional prompt config for retry templates.
        """
        self._llm_client = llm_client
        self._prompt_formatter = prompt_formatter
        self._response_parser = response_parser
        self._fallback_selector = fallback_selector
        self._config = config
        self._prompt_config = prompt_config

    async def __aenter__(self) -> Self:
        await self._llm_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self._llm_client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_action(
        self,
        context: TContext,
        available_actions: TAvailableActions,
        config: PlayerConfig,
    ) -> ActionResponse[TAction, TNarration]:
        """Get an action from the LLM.

        Formats the prompt, calls the LLM, parses the response,
        and retries on failure up to max_retries times.

        Args:
            context: The decision context.
            available_actions: The available actions.
            config: The player configuration (includes model_id).

        Returns:
            ActionResponse with the chosen action.

        Raises:
            LlmError: If all retries fail and no fallback available.
            ValueError: If config.model_id is LlmModel.NONE.
        """
        # Validate that a valid LLM model is configured
        if config.model_id == LlmModel.NONE:
            raise ValueError(
                f"LlmActionProvider requires a valid LLM model, but player {config.player_id} "
                f"has model_id={LlmModel.NONE}. Use a non-LLM provider for this player."
            )

        # Get both prompts from the formatter, passing PlayerConfig directly
        # Type cast is needed because TPlayerInfo is generic but we know it's PlayerConfig
        system_prompt, user_prompt = self._prompt_formatter(
            context, available_actions, cast(TPlayerInfo, config)
        )

        last_error: str | None = None
        last_response: str | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                # Build request with retry context if needed
                if attempt > 0 and last_error:
                    retry_prompt = self._build_retry_prompt(
                        user_prompt,
                        last_response,
                        last_error,
                    )
                else:
                    retry_prompt = user_prompt

                # Use model_id from config (already LlmModel enum)
                model = config.model_id

                request = LlmRequest(
                    system_prompt=system_prompt,
                    user_prompt=retry_prompt,
                    model_id=model,
                    max_tokens=self._config.max_output_tokens,
                    temperature=self._config.temperature,
                )

                response = await self._llm_client.complete(request)
                last_response = response.content

                # Parse the response
                result = self._response_parser(response.content, available_actions)

                # Check if action parsing succeeded
                if isinstance(result, ParseFailure):
                    self._logger.warning(
                        "Parse attempt failed",
                        player_id=config.player_id,
                        attempt=attempt + 1,
                        error_type=result.error.error_type,
                        error_message=result.error.message,
                        error_context=result.error.context,
                        last_response=last_response,
                    )
                    last_error = result.error.message
                    continue  # Retry

                # Type checker knows result is ParseSuccess here
                action = result.action

                # Handle narration with logging
                narration: TNarration | None = None
                if isinstance(result.narration, ParseError):
                    self._logger.warning(
                        f"Narration parse failed for player {config.player_id}: "
                        f"[{result.narration.error_type}] {result.narration.message}",
                        context=result.narration.context
                    )
                else:
                    narration = result.narration

                return ActionResponse(action=action, narration=narration)

            except LlmError as e:
                last_error = str(e)
                self._logger.warning(
                    "LLM request failed",
                    player_id=config.player_id,
                    attempt=attempt + 1,
                    error_type=type(e).__name__,
                    error_message=last_error,
                )

        # All retries exhausted, try fallback
        self._logger.warning(
            f"All {self._config.max_retries + 1} attempts failed for player {config.player_id}"
        )

        if self._fallback_selector is not None:
            fallback = self._fallback_selector(available_actions)
            if fallback is not None:
                self._logger.warning(f"Using fallback action for player {config.player_id}")
                return ActionResponse(action=fallback)

        raise LlmError(
            f"Failed to get valid action after {self._config.max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def _build_retry_prompt(
        self,
        original_prompt: str,
        last_response: str | None,
        error: str | None,
    ) -> str:
        """Build a retry prompt with error context.

        Composes retry prompt from structured components if available,
        otherwise falls back to hardcoded behavior.

        Args:
            original_prompt: The original user prompt.
            last_response: The previous LLM response (if any).
            error: Error message from parsing (if any).

        Returns:
            Composed retry prompt string.
        """
        if not self._prompt_config:
            # Fallback to original hardcoded behavior for backward compatibility
            retry_context = [original_prompt, "", "---", "RETRY: Your previous response was invalid."]

            if error:
                retry_context.append(f"Error: {error}")

            if last_response:
                snippet = last_response[:200] + "..." if len(last_response) > 200 else last_response
                retry_context.append(f"Your response was: {snippet}")

            retry_context.append("")
            retry_context.append("Please provide a valid action in the correct format.")

            return "\n".join(retry_context)
        
        # Use structured components from config
        components = self._prompt_config.retry_prompt
        
        # Compose retry prompt from components
        parts = [original_prompt, "", components.header]
        
        if error:
            parts.append(components.error_section.format(error_message=error))
        
        if last_response:
            snippet = (
                last_response[:200] + "..." 
                if len(last_response) > 200 
                else last_response
            )
            parts.append(components.response_section.format(last_response_snippet=snippet))
        
        parts.append(components.footer)
        
        return "\n".join(parts)
