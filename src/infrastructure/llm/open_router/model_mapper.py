from typing import ClassVar

from src.domain.models.llm_model import LlmModel


class OpenRouterModelMapper:
    _MODEL_MAP: ClassVar[dict[LlmModel, str]] = {
        LlmModel.OPENAI_GPT4O: "openai/gpt-4o",
        LlmModel.OPENAI_GPT4O_MINI: "openai/gpt-4o-mini",
        LlmModel.ANTHROPIC_CLAUDE_35_SONNET: "anthropic/claude-3.5-sonnet",
        LlmModel.ANTHROPIC_CLAUDE_3_OPUS: "anthropic/claude-3-opus",
        LlmModel.GOOGLE_GEMINI_2_5_PRO: "google/gemini-2.5-pro",
        LlmModel.GOOGLE_GEMINI_2_5_FLASH: "google/gemini-2.5-flash",
        LlmModel.XAI_GROK_4_FAST: "x-ai/grok-4-fast",
        LlmModel.DEEPSEEK_DEEPSEEK_v3_2: "deepseek/deepseek-v3.2",
        LlmModel.XAI_GROK_4_1_FAST: "x-ai/grok-4.1-fast",
        LlmModel.META_LLAMA_3_3_70B_INSTRUCT: "meta-llama/llama-3.3-70b-instruct",
    }

    @classmethod
    def to_openrouter_model(cls, llm_model: LlmModel) -> str:
        if llm_model == LlmModel.NONE:
            raise ValueError(
                f"Cannot map LlmModel.NONE to OpenRouter model. "
                f"Use a valid LLM model or a non-LLM provider."
            )
        if llm_model not in cls._MODEL_MAP:
            raise ValueError(
                f"Model {llm_model.value} is not mapped to an OpenRouter model. "
                f"Please add it to OpenRouterModelMapper._MODEL_MAP"
            )

        return cls._MODEL_MAP[llm_model]

    @classmethod
    def from_openrouter_model(cls, openrouter_model: str) -> LlmModel:
        # Create reverse mapping
        reverse_map: dict[str, LlmModel] = {
            v: k for k, v in cls._MODEL_MAP.items()
        }

        if openrouter_model not in reverse_map:
            valid_models = [model.value for model in LlmModel]
            raise ValueError(
                f"Unknown OpenRouter model: {openrouter_model}. "
                f"Supported models: {valid_models}"
            )

        return reverse_map[openrouter_model]

    @classmethod
    def is_valid_model(cls, llm_model_str: str) -> bool:
        try:
            llm_model = LlmModel(llm_model_str)
            return llm_model != LlmModel.NONE and llm_model in cls._MODEL_MAP
        except ValueError:
            return False
