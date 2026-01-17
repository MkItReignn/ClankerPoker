from __future__ import annotations

from typing import ClassVar

from src.domain.models.llm_model import LlmModel


class OpenRouterModelMapper:
    _MODEL_MAP: ClassVar[dict[LlmModel, str]] = {
        LlmModel.OPENAI_GPT4O: "openai/gpt-4o",
        LlmModel.OPENAI_GPT4O_MINI: "openai/gpt-4o-mini",
        LlmModel.ANTHROPIC_CLAUDE_35_SONNET: "anthropic/claude-3.5-sonnet",
        LlmModel.ANTHROPIC_CLAUDE_3_OPUS: "anthropic/claude-3-opus",
        LlmModel.GOOGLE_GEMINI_PRO: "google/gemini-pro",
        LlmModel.GOOGLE_GEMINI_ULTRA: "google/gemini-ultra",
        LlmModel.DEEPSEEK_DEEPSEEK: "deepseek/deepseek",
        LlmModel.XAI_GROK: "x-ai/grok",
    }

    @classmethod
    def to_openrouter_model(cls, model_id: str) -> str:
        try:
            internal_model = LlmModel(model_id)
        except ValueError as e:
            valid_models = [model.value for model in LlmModel]
            raise ValueError(
                f"Unknown model_id: {model_id}. Supported models: {valid_models}"
            ) from e

        if internal_model not in cls._MODEL_MAP:
            raise ValueError(
                f"Model {internal_model.value} is not mapped to an OpenRouter model. "
                f"Please add it to OpenRouterModelMapper._MODEL_MAP"
            )

        return cls._MODEL_MAP[internal_model]

    @classmethod
    def is_valid_model(cls, model_id: str) -> bool:
        try:
            cls.to_openrouter_model(model_id)
            return True
        except ValueError:
            return False
