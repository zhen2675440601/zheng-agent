import os
import tempfile
from pathlib import Path

import click

from zheng_agent.core.action_gateway import ActionGatewayExecutor, create_registry_for_task
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts.recovery import AgentRecoveryMetadata, RecoveryError
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.runtime.state_store import RunStateStore


def _build_resume_agent(agent_type: str, recovery_data: dict | None):
    """Construct agent from checkpoint recovery data with validation."""
    if recovery_data is None:
        recovery_data = {}

    metadata = AgentRecoveryMetadata(agent_type=agent_type, recovery_data=recovery_data)

    if agent_type == "mock":
        try:
            metadata.validate_for_restore()
        except RecoveryError as exc:
            raise click.ClickException(f"Invalid checkpoint: {exc.reason}")

        agent = ScriptedMockAgent(decisions=[])
        agent.restore_from_metadata(metadata)
        return agent

    if agent_type == "openai":
        try:
            metadata.validate_for_restore()
        except RecoveryError as exc:
            raise click.ClickException(f"Invalid checkpoint: {exc.reason}")

        if not os.environ.get("OPENAI_API_KEY"):
            raise click.ClickException("OPENAI_API_KEY not set for openai agent")
        from zheng_agent.agents.llm.openai_agent import OpenAIAgent

        model = recovery_data.get("model", "gpt-4o")
        temperature = recovery_data.get("temperature", 0.0)
        agent = OpenAIAgent(model=model, temperature=temperature)
        agent.restore_from_metadata(metadata)
        return agent

    raise click.ClickException(f"Unknown agent type: {agent_type}")


@click.command()
@click.argument("run_id")
@click.option(
    "--agent",
    "-a",
    default=None,
    type=click.Choice(["mock", "openai"]),
    help="Override the checkpoint agent type for resuming",
)
@click.option("--trace-dir", "-d", default=None, type=click.Path(), help="Directory where traces are stored")
def resume(run_id: str, agent: str | None, trace_dir: str):
    """Resume a paused run from its last checkpoint."""
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

    registry = create_registry_for_task(state.task_spec)
    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=trace_root, gateway=gateway, evaluator=evaluator)

    checkpoint_agent_type = state.agent_recovery.agent_type if state.agent_recovery else "mock"
    recovery_data = state.agent_recovery.recovery_data if state.agent_recovery else {}
    agent_type = agent or checkpoint_agent_type

    try:
        agent_instance = _build_resume_agent(agent_type, recovery_data)
    except click.ClickException as exc:
        click.echo(f"Error: {exc.message}", err=True)
        raise SystemExit(1)

    outcome = engine.resume(run_id, agent_instance)

    click.echo(f"Run ID: {outcome.run_id}")
    click.echo(f"Status: {outcome.run_result.status}")
    if outcome.eval_result:
        click.echo(f"Passed: {outcome.eval_result.passed}")
        if outcome.eval_result.reasons:
            click.echo(f"Reasons: {', '.join(outcome.eval_result.reasons)}")
