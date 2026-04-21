import click

from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision, TaskSpec
from pathlib import Path
import tempfile
import os


@click.command()
@click.option("--mock", is_flag=True, help="Use mock agent for testing (no LLM calls)")
@click.option("--model", default="gpt-4o", help="Model to use for LLM agent")
@click.option("--trace-dir", "-d", default=None, type=click.Path(),
              help="Directory to store trace files (default: temp)")
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

    # Setup
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()

    if trace_dir:
        trace_root = Path(trace_dir)
        trace_root.mkdir(parents=True, exist_ok=True)
    else:
        trace_root = Path(tempfile.gettempdir()) / "zheng_traces"

    engine = HarnessEngine(trace_root=trace_root, gateway=gateway, evaluator=evaluator)

    # Chat task spec
    spec = TaskSpec(
        task_type="chat",
        title="Interactive Chat",
        description="Conversational interaction with user",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object", "required_keys": ["response"]},
        allowed_actions=["echo"],
        max_steps=3,
    )

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
            # Mock agent: echo back the message
            agent = ScriptedMockAgent(
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
        else:
            # Real LLM agent
            from zheng_agent.agents.chat_agent import ChatAgent
            agent = ChatAgent(model=model)

        outcome = engine.run(task_spec=spec, task_input=input_data, agent=agent)

        if outcome.run_result.status == "completed":
            response = outcome.run_result.output.get("response", "")
            click.echo(f"Agent: {response}")
        else:
            click.echo(f"Error: {outcome.run_result.error}")

        click.echo(f"[Run ID: {outcome.run_id}]")