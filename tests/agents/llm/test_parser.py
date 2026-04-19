import pytest

from zheng_agent.agents.llm.parser import DecisionParseError, parse_decision
from zheng_agent.core.contracts import AgentDecision


def test_parse_valid_request_action():
    raw_response = '{"decision_type": "request_action", "reasoning": "test", "action_name": "echo", "action_input": {"message": "hello"}}'

    decision = parse_decision(raw_response, ["echo", "log"])

    assert decision.decision_type == "request_action"
    assert decision.action_name == "echo"
    assert decision.action_input == {"message": "hello"}


def test_parse_valid_complete():
    raw_response = '{"decision_type": "complete", "reasoning": "done", "final_result": {"message": "hello"}}'

    decision = parse_decision(raw_response, ["echo"])

    assert decision.decision_type == "complete"
    assert decision.final_result == {"message": "hello"}


def test_parse_valid_fail():
    raw_response = '{"decision_type": "fail", "reasoning": "error", "failure_reason": "something went wrong"}'

    decision = parse_decision(raw_response, ["echo"])

    assert decision.decision_type == "fail"
    assert decision.failure_reason == "something went wrong"


def test_parse_invalid_json():
    raw_response = "not a json"

    with pytest.raises(DecisionParseError, match="No JSON object"):
        parse_decision(raw_response, ["echo"])


def test_parse_missing_decision_type():
    raw_response = '{"action_name": "echo"}'

    with pytest.raises(DecisionParseError, match="Invalid decision_type"):
        parse_decision(raw_response, ["echo"])


def test_parse_invalid_action():
    raw_response = '{"decision_type": "request_action", "reasoning": "test", "action_name": "invalid", "action_input": {}}'

    with pytest.raises(DecisionParseError, match="not allowed"):
        parse_decision(raw_response, ["echo"])


def test_parse_json_in_markdown():
    raw_response = '```json\n{"decision_type": "complete", "final_result": {"message": "hello"}}\n```'

    decision = parse_decision(raw_response, ["echo"])

    assert decision.decision_type == "complete"