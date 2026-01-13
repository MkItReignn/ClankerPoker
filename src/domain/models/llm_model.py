from __future__ import annotations

from enum import StrEnum


class LlmModel(StrEnum):
    OPENAI_GPT4O = "openai/gpt-4o"
    OPENAI_GPT4O_MINI = "openai/gpt-4o-mini"
    ANTHROPIC_CLAUDE_35_SONNET = "anthropic/claude-3.5-sonnet"
    ANTHROPIC_CLAUDE_3_OPUS = "anthropic/claude-3-opus"
    GOOGLE_GEMINI_PRO = "google/gemini-pro"
    GOOGLE_GEMINI_ULTRA = "google/gemini-ultra"
    DEEPSEEK_DEEPSEEK = "deepseek/deepseek"
    XAI_GROK = "x-ai/grok"
