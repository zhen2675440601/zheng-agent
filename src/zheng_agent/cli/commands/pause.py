import click
from pathlib import Path
import tempfile

from zheng_agent.core.runtime.state_store import RunStateStore


@click.command()
@click.argument("run_id")
@click.option("--trace-dir", "-d", default=None, type=click.Path(),
              help="Directory where traces are stored")
def pause(run_id: str, trace_dir: str):
    """Signal a running run to pause at the next checkpoint.

    Creates a pause signal file that the engine will detect and honor
    at the next checkpoint boundary. This works across processes.
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

    if state.run_status != "running" and state.run_status != "waiting_action":
        click.echo(f"Error: Run {run_id} is not running (status: {state.run_status})", err=True)
        raise SystemExit(1)

    # Create pause signal file for cross-process pause
    signal_path = trace_root / f"{run_id}.pause_signal"
    signal_path.write_text("pause", encoding="utf-8")

    click.echo(f"Pause signal created for run {run_id}")
    click.echo(f"Current checkpoint: {state.checkpoint_kind}")
    click.echo("The run will pause at the next checkpoint boundary.")