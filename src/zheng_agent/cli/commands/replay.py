import click
from pathlib import Path
import tempfile
import json

from zheng_agent.core.replay.replayer import replay_trace, get_trace_events, reevaluate_trace
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.cli.config.loader import load_task_spec


@click.command()
@click.argument("run_id")
@click.option("--trace-dir", "-d", default=None, type=click.Path(),
              help="Directory where traces are stored")
@click.option("--task-spec", "-t", default=None, type=click.Path(exists=True),
              help="Path to original task spec YAML for re-evaluation")
@click.option("--format", "-f", default="summary",
              type=click.Choice(["summary", "json", "events"]),
              help="Output format")
@click.option("--re-evaluate", is_flag=True,
              help="Re-run evaluation on the trace")
def replay(run_id: str, trace_dir: str, task_spec: str, format: str, re_evaluate: bool):
    """Replay and analyze a historical run trace.

    Provides summary of the run, or detailed event list.
    With --task-spec and --re-evaluate, can re-run the evaluator.
    """
    if trace_dir:
        trace_root = Path(trace_dir)
    else:
        trace_root = Path(tempfile.gettempdir()) / "zheng_traces"

    trace_path = trace_root / f"{run_id}.jsonl"

    if not trace_path.exists():
        click.echo(f"Error: No trace found for run {run_id}", err=True)
        raise SystemExit(1)

    summary = replay_trace(trace_path)

    if format == "json":
        click.echo(json.dumps(summary, indent=2))
        return

    if format == "events":
        events = get_trace_events(trace_path)
        for event in events:
            click.echo(f"[{event.sequence_number}] {event.event_type} | step={event.step_id or '-'}")
            if event.payload:
                click.echo(f"    payload: {json.dumps(event.payload, ensure_ascii=False)}")
        return

    # Summary format
    click.echo(f"Run ID: {summary['run_id']}")
    click.echo(f"Event count: {summary['event_count']}")
    click.echo(f"Terminal event: {summary['terminal_event']}")
    click.echo(f"Step IDs: {', '.join(summary['step_ids']) or 'none'}")

    # Re-evaluate if requested
    if re_evaluate and task_spec:
        spec = load_task_spec(Path(task_spec))
        evaluator = BasicRunEvaluator()

        # Determine final status from trace
        final_status = "failed"
        final_output = None
        for event in get_trace_events(trace_path):
            if event.event_type == "run_completed":
                final_status = "completed"
            if event.event_type == "run_failed":
                final_status = "failed"

        result = reevaluate_trace(trace_path, evaluator, spec, final_status, final_output)

        click.echo("-" * 40)
        click.echo("Re-evaluation result:")
        click.echo(f"Passed: {result['passed']}")
        if result['score']:
            click.echo(f"Score: {result['score']}")
        if result['reasons']:
            click.echo(f"Reasons: {', '.join(result['reasons'])}")
        if result['metrics']:
            click.echo(f"Metrics: {json.dumps(result['metrics'])}")