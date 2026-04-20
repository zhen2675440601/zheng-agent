import click
from pathlib import Path

from zheng_agent.cli.config.loader import load_and_validate_task_input, load_task_spec, ValidationError
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.agent.mock import ScriptedMockAgent


@click.command()
@click.option("--task-spec", "-t", required=True, type=click.Path(exists=True),
              help="Path to task spec YAML file")
@click.option("--task-input", "-i", required=True, type=click.Path(exists=True),
              help="Path to task input YAML/JSON file")
@click.option("--agent", "-a", default="mock",
              type=click.Choice(["mock", "openai"]),
              help="Agent type to use")
@click.option("--trace-dir", "-d", default="./traces", type=click.Path(),
              help="Directory to store trace files")
@click.option("--output-format", "-o", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format")
def run(task_spec: str, task_input: str, agent: str, trace_dir: str, output_format: str):
    """Run a task with specified agent."""
    # 加载配置
    spec = load_task_spec(Path(task_spec))
    try:
        input_data = load_and_validate_task_input(spec, Path(task_input))
    except ValidationError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # 构建 action registry (内置 echo 动作)
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})
    registry.register("log", lambda payload: {"logged": payload.get("message", "")})

    # 创建 agent
    if agent == "mock":
        # Mock agent: 先 echo 然后 complete
        from zheng_agent.core.contracts import AgentDecision
        agent_instance = ScriptedMockAgent(
            decisions=[
                AgentDecision(
                    decision_type="request_action",
                    action_name="echo",
                    action_input=input_data,
                ),
                AgentDecision(
                    decision_type="complete",
                    final_result=input_data,
                ),
            ]
        )
    elif agent == "openai":
        from zheng_agent.agents.llm.openai_agent import OpenAIAgent
        agent_instance = OpenAIAgent()

    # 执行
    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=Path(trace_dir), gateway=gateway, evaluator=evaluator)

    outcome = engine.run(task_spec=spec, task_input=input_data, agent=agent_instance)

    # 输出结果
    if output_format == "json":
        click.echo(f'{{"run_id": "{outcome.run_id}", "status": "{outcome.run_result.status}", "passed": {outcome.eval_result.passed}}}')
    else:
        click.echo(f"Run ID: {outcome.run_id}")
        click.echo(f"Status: {outcome.run_result.status}")
        click.echo(f"Passed: {outcome.eval_result.passed}")
        if outcome.eval_result.reasons:
            click.echo(f"Reasons: {', '.join(outcome.eval_result.reasons)}")