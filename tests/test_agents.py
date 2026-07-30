"""
Unit tests for individual agents.
"""

def test_research_agent():
    from src.agents.research_agent.agent import ResearchAgent
    agent = ResearchAgent()
    result = agent.execute("test query")
    assert "status" in result

def test_planner_agent():
    from src.agents.planner_agent.agent import PlannerAgent
    agent = PlannerAgent()
    plan = agent.create_plan("test objective")
    assert isinstance(plan, list)

def test_validator_agent():
    from src.agents.validator_agent.agent import ValidatorAgent
    agent = ValidatorAgent()
    is_valid = agent.validate({})
    assert is_valid is True
