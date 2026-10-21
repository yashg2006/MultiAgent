"""
Global project configuration and settings loader.

Every field can be overridden by an environment variable of the same name in
upper case (pydantic-settings), or via a `.env` file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

# USD per million tokens (input, output). Haiku 5.5 is priced by prompt length;
# these are its rates for prompts up to 100k tokens, which covers every prompt
# this app sends. Source: https://platform.claude.com/docs/en/about-claude/pricing
# (checked 21/10/2026). Unknown models are costed at 0 and logged.
MODEL_PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MultiAgentAISystem"
    env: str = "development"

    # --- LLM ----------------------------------------------------------------
    # "mock" (default: offline, deterministic, free), "anthropic", or "openai".
    llm_provider: str = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60.0

    # Per-call retry for transient provider errors (NFR-03).
    llm_max_attempts: int = 3
    retry_base_delay_seconds: float = 0.5

    # Circuit breaker: after this many consecutive failed calls, fail fast for
    # `circuit_reset_seconds` instead of hammering a provider that is down.
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 30.0

    # --- Pipeline -------------------------------------------------------------
    # Research->Validate cycles before returning a partial result.
    max_retries: int = 3
    max_sub_tasks: int = 3
    max_parallel_research: int = 4
    # Minimum LLM-judge score (0-1) for the Validator to pass a result.
    judge_threshold: float = 0.6

    # "none" (default; no network) or "wikipedia" (free, no key).
    search_tool: str = "none"


settings = Settings()
