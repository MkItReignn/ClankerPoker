from enum import StrEnum


class LlmModel(StrEnum):
    NONE = "none"
    OPENAI_GPT4O = "openai/gpt-4o"
    OPENAI_GPT4O_MINI = "openai/gpt-4o-mini"
    ANTHROPIC_CLAUDE_35_SONNET = "anthropic/claude-3.5-sonnet"
    ANTHROPIC_CLAUDE_3_OPUS = "anthropic/claude-3-opus"
    GOOGLE_GEMINI_2_5_PRO = "google/gemini-2.5-pro"
    GOOGLE_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
    GOOGLE_GEMINI_3_FLASH = "google/gemini-3-flash"
    GOOGLE_GEMINI_3_PRO = "google/gemini-3-pro"
    DEEPSEEK_DEEPSEEK = "deepseek/deepseek"
    XAI_GROK_4 = "x-ai/grok-4"
    XAI_GROK_4_FAST = "x-ai/grok-4-fast"
    DEEPSEEK_DEEPSEEK_v3_2 = "deepseek/deepseek-v3.2"
    XAI_GROK_4_1_FAST = "x-ai/grok-4.1-fast"
    META_LLAMA_3_3_70B_INSTRUCT = "meta-llama/llama-3.3-70b-instruct"

    @property
    def display_name(self) -> str:
        display_names = {
            LlmModel.NONE: "Bot",
            LlmModel.OPENAI_GPT4O: "GPT-4o",
            LlmModel.OPENAI_GPT4O_MINI: "GPT-4o-mini",
            LlmModel.ANTHROPIC_CLAUDE_35_SONNET: "Claude-3.5-Sonnet",
            LlmModel.ANTHROPIC_CLAUDE_3_OPUS: "Claude-3-Opus",
            LlmModel.GOOGLE_GEMINI_2_5_PRO: "Gemini-2.5-Pro",
            LlmModel.GOOGLE_GEMINI_2_5_FLASH: "Gemini-2.5-Flash",
            LlmModel.GOOGLE_GEMINI_3_FLASH: "Gemini-3-Flash",
            LlmModel.GOOGLE_GEMINI_3_PRO: "Gemini-3-Pro",
            LlmModel.DEEPSEEK_DEEPSEEK: "DeepSeek",
            LlmModel.XAI_GROK_4: "Grok-4",
            LlmModel.XAI_GROK_4_FAST: "Grok-4-Fast",
            LlmModel.DEEPSEEK_DEEPSEEK_v3_2: "DeepSeek-v3.2",
            LlmModel.XAI_GROK_4_1_FAST: "Grok-4.1-Fast",
            LlmModel.META_LLAMA_3_3_70B_INSTRUCT: "Llama-3.3-70B",
        }
        return display_names[self]
