import click
from pathlib import Path

from zheng_agent.cli.config.loader import ValidationError, load_and_validate_task_input, load_task_spec
from zheng_agent.cli.runtime import build_engine, build_mock_run_agent


@click.command()
@click.option("--task-spec", "-t", required=True, type=click.Path(exists=True), help="Path to task spec YAML file")
@click.option("--task-input", "-i", required=True, type=click.Path(exists=True), help="Path to task input YAML/JSON file")
@click.option("--agent", "-a", default="mock", type=click.Choice(["mock", "openai"]), help="Agent type to use")
@click.option("--trace-dir", "-d", default="./traces", type=click.Path(), help="Directory to store trace files")
@click.option("--output-format", "-o", default="text", type=click.Choice(["text", "json"]), help="Output format")
def run(task_spec: str, task_input: str, agent: str, trace_dir: str, output_format: str):
    """Run a task with specified agent."""
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

        agent_instance = OpenAIAgent()

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
