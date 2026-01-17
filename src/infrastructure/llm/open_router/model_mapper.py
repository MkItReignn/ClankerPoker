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
    def to_openrouter_model(cls, model: LlmModel) -> str:
        if model not in cls._MODEL_MAP:
            raise ValueError(
                f"Model {model.value} is not mapped to an OpenRouter model. "
                f"Please add it to OpenRouterModelMapper._MODEL_MAP"
            )

        return cls._MODEL_MAP[model]

    @classmethod
    def from_openrouter_model(cls, openrouter_model: str) -> LlmModel:
        # Create reverse mapping
        reverse_map: dict[str, LlmModel] = {v: k for k, v in cls._MODEL_MAP.items()}

        if openrouter_model not in reverse_map:
            valid_models = [model.value for model in LlmModel]
            raise ValueError(
                f"Unknown OpenRouter model: {openrouter_model}. "
                f"Supported models: {valid_models}"
            )

        return reverse_map[openrouter_model]

    @classmethod
    def is_valid_model(cls, model_id: str) -> bool:
        try:
            model = LlmModel(model_id)
            return model in cls._MODEL_MAP
        except ValueError:
            return False
