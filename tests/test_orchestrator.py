"""
Unit tests for the Orchestrator.
"""

def test_orchestrator_initialization():
    from src.orchestrator.main import Orchestrator
    orchestrator = Orchestrator()
    assert orchestrator is not None
