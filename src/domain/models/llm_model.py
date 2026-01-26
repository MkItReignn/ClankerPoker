from enum import StrEnum


class LlmModel(StrEnum):
    NONE = "none"
    OPENAI_GPT4O = "openai/gpt-4o"
    OPENAI_GPT4O_MINI = "openai/gpt-4o-mini"
    ANTHROPIC_CLAUDE_35_SONNET = "anthropic/claude-3.5-sonnet"
    ANTHROPIC_CLAUDE_3_OPUS = "anthropic/claude-3-opus"
    GOOGLE_GEMINI_2_5_PRO = "google/gemini-2.5-pro"
    GOOGLE_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
    DEEPSEEK_DEEPSEEK = "deepseek/deepseek"
    XAI_GROK_4_FAST = "x-ai/grok-4-fast"
    DEEPSEEK_DEEPSEEK_v3_2 = "deepseek/deepseek-v3.2"
    XAI_GROK_4_1_FAST = "x-ai/grok-4.1-fast"
    META_LLAMA_3_3_70B_INSTRUCT = "meta-llama/llama-3.3-70b-instruct"

    @property
    def display_name(self) -> str:
        display_names = {
            "none": "Bot",
            "openai/gpt-4o": "GPT-4o",
            "openai/gpt-4o-mini": "GPT-4o-mini",
            "anthropic/claude-3.5-sonnet": "Claude-3.5-Sonnet",
            "anthropic/claude-3-opus": "Claude-3-Opus",
            "google/gemini-2.5-pro": "Gemini-2.5-Pro",
            "google/gemini-2.5-flash": "Gemini-2.5-Flash",
            "deepseek/deepseek": "DeepSeek",
            "x-ai/grok-4-fast": "Grok-4-Fast",
            "deepseek/deepseek-v3.2": "DeepSeek-v3.2",
            "x-ai/grok-4.1-fast": "Grok-4.1-Fast",
            "meta-llama/llama-3.3-70b-instruct": "Llama-3.3-70B",
        }
        return display_names.get(self.value, self.value)
