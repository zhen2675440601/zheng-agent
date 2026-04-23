import os
import click
from pathlib import Path

from zheng_agent.cli.config.loader import ValidationError, load_and_validate_task_input, load_task_spec
from zheng_agent.cli.runtime import build_engine, build_mock_run_agent
from zheng_agent.core.contracts import TaskSpec


@click.command()
@click.option("--task-spec", "-t", required=False, type=click.Path(exists=True), help="Path to task spec YAML file")
@click.option("--task-input", "-i", required=False, type=click.Path(exists=True), help="Path to task input YAML/JSON file")
@click.option("--agent", "-a", default="mock", type=click.Choice(["mock", "openai"]), help="Agent type to use")
@click.option("--model", "-m", default=None, help="Model name for LLM agent")
@click.option("--trace-dir", "-d", default="./traces", type=click.Path(), help="Directory to store trace files")
@click.option("--output-format", "-o", default="text", type=click.Choice(["text", "json"]), help="Output format")
@click.option("--quick", "-q", is_flag=True, help="Quick test mode: simple echo task with --message")
@click.option("--message", default="Hello", help="Message for quick test mode")
def run(task_spec: str | None, task_input: str | None, agent: str, model: str | None, trace_dir: str, output_format: str, quick: bool, message: str):
    """Run a task with specified agent."""
    if quick:
        # Quick test mode - simple echo task
        spec = TaskSpec(
            task_type="quick_echo",
            title="Quick Echo Test",
            description="Simple echo test",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
            output_schema={"type": "object", "required_keys": ["echoed"]},
            allowed_actions=["echo"],
            max_steps=2,
            timeout_seconds=60,
        )
        input_data = {"message": message}
    else:
        # File mode
        if not task_spec or not task_input:
            click.echo("Error: --task-spec and --task-input required (or use --quick for quick test)", err=True)
            raise SystemExit(1)
        spec = load_task_spec(Path(task_spec))
        try:
            input_data = load_and_validate_task_input(spec, Path(task_input))
        except ValidationError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

    if agent == "mock":
        agent_instance = build_mock_run_agent(input_data)
    else:
        from zheng_agent.agents.llm.openai_agent import OpenAIAgent

        if not os.environ.get("OPENAI_API_KEY"):
            click.echo("Error: OPENAI_API_KEY not set", err=True)
            raise SystemExit(1)

        model_name = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
        agent_instance = OpenAIAgent(model=model_name)

    engine = build_engine(spec, Path(trace_dir))
    outcome = engine.run(task_spec=spec, task_input=input_data, agent=agent_instance)

    if output_format == "json":
        click.echo(
            f'{{"run_id": "{outcome.run_id}", "status": "{outcome.run_result.status}", "passed": {outcome.eval_result.passed}}}'
        )
    else:
        click.echo(f"Run ID: {outcome.run_id}")
        click.echo(f"Status: {outcome.run_result.status}")
        click.echo(f"Passed: {outcome.eval_result.passed}")
        if outcome.eval_result.reasons:
            click.echo(f"Reasons: {', '.join(outcome.eval_result.reasons)}")
