"""
Unit tests for shared Pydantic schemas, the logger utility, and Settings.

Maps to docs/test_plan.md: UT-S-*.
"""

import pytest
from pydantic import ValidationError

from src.shared.config import Settings
from src.shared.schemas import AgentRequest, AgentResponse
from src.shared.utils import setup_logger


def test_agent_request_validates_correct_data():
    """UT-S-01: AgentRequest validates correct data."""
    req = AgentRequest(task_id="t1", prompt="do something")
    assert req.task_id == "t1"
    assert req.metadata is None


def test_agent_request_rejects_missing_required_fields():
    """UT-S-02: AgentRequest rejects missing required fields."""
    with pytest.raises(ValidationError):
        AgentRequest(prompt="missing task_id")  # type: ignore[call-arg]


def test_agent_response_accepts_optional_fields_as_none():
    """UT-S-03: AgentResponse accepts optional fields as None when only required fields given."""
    resp = AgentResponse(task_id="t1", status="success")
    assert resp.result is None
    assert resp.error is None


def test_setup_logger_returns_logger_instance():
    """UT-S-04: setup_logger() returns a logging.Logger instance."""
    import logging

    logger = setup_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_setup_logger_does_not_duplicate_handlers_on_repeat_calls():
    logger1 = setup_logger("dup_test_logger")
    logger2 = setup_logger("dup_test_logger")
    assert logger1 is logger2
    assert len(logger1.handlers) == 1


def test_settings_loads_default_values():
    """UT-S-05: Settings loads default values when no overriding env/.env is present."""
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_name == "MultiAgentAISystem"
    assert settings.llm_provider in {"mock", "openai"}
    assert settings.max_retries >= 1
