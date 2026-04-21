import click
from pathlib import Path
import tempfile
import os

from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.runtime.state_store import RunStateStore
from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision
from zheng_agent.core.contracts.recovery import AgentType


@click.command()
@click.argument("run_id")
@click.option("--agent", "-a", default="mock",
              type=click.Choice(["mock", "openai"]),
              help="Agent type to use for resuming")
@click.option("--trace-dir", "-d", default=None, type=click.Path(),
              help="Directory where traces are stored")
def resume(run_id: str, agent: str, trace_dir: str):
    """Resume a paused run from its last checkpoint.

    Uses the persisted checkpoint to restore execution state and
    continues from where the run was paused.
    """
    if trace_dir:
        trace_root = Path(trace_dir)
    else:
        trace_root = Path(tempfile.gettempdir()) / "zheng_traces"

    state_store = RunStateStore(trace_root)
    state = state_store.load(run_id)

    if state is None:
        click.echo(f"Error: No checkpoint found for run {run_id}", err=True)
        raise SystemExit(1)

    if state.run_status != "paused":
        click.echo(f"Error: Run {run_id} is not paused (status: {state.run_status})", err=True)
        raise SystemExit(1)

    click.echo(f"Resuming from checkpoint: {state.checkpoint_kind}")
    click.echo(f"Step: {state.step_id} (index: {state.step_index})")

    # Setup action registry from task spec
    registry = ActionAdapterRegistry()
    for action in state.task_spec.allowed_actions:
        if action == "echo":
            registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})
        elif action == "log":
            registry.register("log", lambda payload: {"logged": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=trace_root, gateway=gateway, evaluator=evaluator)

    # Create agent based on checkpoint metadata or CLI override
    agent_type: AgentType = state.agent_recovery.agent_type if state.agent_recovery else "mock"
    if agent != "mock":
        agent_type = agent

    if agent_type == "mock":
        # Create mock agent with remaining decisions
        # Note: the agent's restore_from_metadata will set the correct position
        agent_instance = ScriptedMockAgent(
            decisions=[
                AgentDecision(decision_type="complete", final_result=state.task_input),
            ]
        )
    elif agent_type == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            click.echo("Error: OPENAI_API_KEY not set for openai agent", err=True)
            raise SystemExit(1)
        from zheng_agent.agents.llm.openai_agent import OpenAIAgent
        agent_instance = OpenAIAgent()
    else:
        click.echo(f"Error: Unknown agent type: {agent_type}", err=True)
        raise SystemExit(1)

    outcome = engine.resume(run_id, agent_instance)

    # Output result
    click.echo(f"Run ID: {outcome.run_id}")
    click.echo(f"Status: {outcome.run_result.status}")
    if outcome.eval_result:
        click.echo(f"Passed: {outcome.eval_result.passed}")
        if outcome.eval_result.reasons:
            click.echo(f"Reasons: {', '.join(outcome.eval_result.reasons)}")