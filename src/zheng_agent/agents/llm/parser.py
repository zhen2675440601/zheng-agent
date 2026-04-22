import json
import re

from pydantic import ValidationError

from zheng_agent.core.contracts import AgentDecision


class DecisionParseError(Exception):
    """决策解析错误"""


def parse_decision(raw_response: str, allowed_actions: list[str]) -> AgentDecision:
    """解析 LLM 响应为 AgentDecision"""
    json_match = re.search(r"\{[\s\S]*\}", raw_response)
    if not json_match:
        raise DecisionParseError("No JSON object found in response")

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise DecisionParseError(f"Invalid JSON: {e}") from e

    decision_type = data.get("decision_type")
    allowed_decision_types = {"request_action", "respond", "advance_step", "complete", "fail"}
    if decision_type not in allowed_decision_types:
        raise DecisionParseError(f"Invalid decision_type: {decision_type}")

    if decision_type == "request_action":
        action_name = data.get("action_name")
        if action_name not in allowed_actions:
            raise DecisionParseError(
                f"Action '{action_name}' not allowed. Allowed: {allowed_actions}"
            )

    try:
        return AgentDecision.model_validate(data)
    except ValidationError as e:
        raise DecisionParseError(f"Invalid decision structure: {e}") from e
