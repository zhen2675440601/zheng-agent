import os
import tempfile
from pathlib import Path

import click

from zheng_agent.cli.runtime import build_engine, build_mock_chat_agent
from zheng_agent.core.contracts import TaskSpec


@click.command()
@click.option("--mock", is_flag=True, help="Use mock agent for testing (no LLM calls)")
@click.option("--model", default="gpt-4o", help="Model to use for LLM agent")
@click.option("--trace-dir", "-d", default=None, type=click.Path(), help="Directory to store trace files (default: temp)")
def chat(mock: bool, model: str, trace_dir: str):
    """Interactive chat with agent.

    By default uses OpenAI LLM. Use --mock for testing without API calls.
    """
    if not mock and not os.environ.get("OPENAI_API_KEY"):
        click.echo("Error: OPENAI_API_KEY not set. Use --mock for testing.", err=True)
        raise SystemExit(1)

    mode = "mock" if mock else "LLM"
    click.echo(f"zheng-agent interactive mode ({mode})")
    click.echo("Type your message and press Enter. Type 'exit' to quit.")
    click.echo("-" * 40)

    if trace_dir:
        trace_root = Path(trace_dir)
        trace_root.mkdir(parents=True, exist_ok=True)
    else:
        trace_root = Path(tempfile.gettempdir()) / "zheng_traces"

    spec = TaskSpec(
        task_type="chat",
        title="Interactive Chat",
        description="Conversational interaction with user",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object", "required_keys": ["response"]},
        allowed_actions=["echo"],
        max_steps=3,
    )
    engine = build_engine(spec, trace_root)

    while True:
        try:
            message = click.prompt("", prompt_suffix="> ", show_default=False)
        except (click.exceptions.Exit, KeyboardInterrupt, EOFError):
            click.echo("\nGoodbye!")
            break

        if message.strip().lower() in ["exit", "quit", "q"]:
            click.echo("Goodbye!")
            break

        if not message.strip():
            continue

        input_data = {"message": message}

        if mock:
            agent = build_mock_chat_agent(message)
        else:
            from zheng_agent.agents.chat_agent import ChatAgent

            agent = ChatAgent(model=model)

        outcome = engine.run(task_spec=spec, task_input=input_data, agent=agent)

        if outcome.run_result.status == "completed":
            response = outcome.run_result.output.get("response", "")
            click.echo(f"Agent: {response}")
        else:
            click.echo(f"Error: {outcome.run_result.error}")

        click.echo(f"[Run ID: {outcome.run_id}]")
