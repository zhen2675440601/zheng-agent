from pathlib import Path

from zheng_agent.core.action_gateway import ActionGatewayExecutor, create_registry_for_task
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision, TaskSpec
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.runtime.engine import HarnessEngine


def build_engine(task_spec: TaskSpec, trace_root: Path) -> HarnessEngine:
    registry = create_registry_for_task(task_spec)
    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    return HarnessEngine(trace_root=trace_root, gateway=gateway, evaluator=evaluator)



def build_mock_run_agent(task_input: dict) -> ScriptedMockAgent:
    return ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input=task_input,
            ),
            AgentDecision(
                decision_type="complete",
                final_result=task_input,
            ),
        ]
    )



def build_mock_chat_agent(message: str) -> ScriptedMockAgent:
    return ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": message},
            ),
            AgentDecision(
                decision_type="complete",
                final_result={"response": f"[Mock] You said: {message}"},
            ),
        ]
    )
