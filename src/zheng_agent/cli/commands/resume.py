import click
from pathlib import Path
import tempfile
import os

from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.runtime.state_store import RunStateStore
from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.agent.mock import ScriptedMockAgent


@click.command()
@click.argument("run_id")
@click.option("--agent", "-a", default="mock",
              type=click.Choice(["mock"]),
              help="Agent type to use for resuming")
@click.option("--trace-dir", "-d", default=None, type=click.Path(),
              help="Directory where traces are stored")
def resume(run_id: str, agent: str, trace_dir: str):
    """Resume a paused run."""
    if trace_dir:
        trace_root = Path(trace_dir)
    else:
        trace_root = Path(tempfile.gettempdir()) / "zheng_traces"

    state_store = RunStateStore(trace_root)
    state = state_store.load(run_id)

    if state is None:
        click.echo(f"Error: No paused state found for run {run_id}", err=True)
        raise SystemExit(1)

    if state.run_status != "paused":
        click.echo(f"Error: Run {run_id} is not paused (status: {state.run_status})", err=True)
        raise SystemExit(1)

    # Setup engine
    registry = ActionAdapterRegistry()
    # Register actions from the original spec
    for action in state.task_spec.allowed_actions:
        if action == "echo":
            registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=trace_root, gateway=gateway, evaluator=evaluator)

    # Create agent based on type
    if agent == "mock":
        # For mock, we need decisions that match the original plan
        # Since we don't have the original decisions stored, we create a simple one
        click.echo("Warning: Mock agent may not follow original decision sequence")
        agent_instance = ScriptedMockAgent(
            decisions=[
                # Simple decision to complete
            ]
        )

    outcome = engine.resume(run_id, agent_instance)

    # Output result
    click.echo(f"Run ID: {outcome.run_id}")
    click.echo(f"Status: {outcome.run_result.status}")
    if outcome.eval_result:
        click.echo(f"Passed: {outcome.eval_result.passed}")
        if outcome.eval_result.reasons:
            click.echo(f"Reasons: {', '.join(outcome.eval_result.reasons)}")