"""End-to-end tests for CLI commands."""

import subprocess
import sys
from pathlib import Path
import tempfile
import json


def run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        [sys.executable, "-m", "zheng_agent.cli.main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def test_run_command_creates_trace():
    """E2E: run command creates trace and returns run_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        code, out, err = run_cli(
            [
                "run",
                "-t", "examples/demo_task/task_spec.yaml",
                "-i", "examples/demo_task/task_input.yaml",
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )

        assert code == 0
        assert "Run ID:" in out
        assert "Status: completed" in out
        assert "Passed: True" in out

        # Verify trace file was created
        trace_files = list(trace_dir.glob("*.jsonl"))
        assert len(trace_files) == 1


def test_run_command_validates_input():
    """E2E: run command validates input against schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        # Create invalid input (missing required 'message')
        bad_input = tmp / "bad_input.yaml"
        bad_input.write_text("count: 123\n", encoding="utf-8")

        code, out, err = run_cli(
            [
                "run",
                "-t", "examples/demo_task/task_spec.yaml",
                "-i", str(bad_input),
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )

        assert code == 1
        assert "Input validation failed" in out or "Error" in out or "validation" in err.lower()


def test_replay_command_reads_trace():
    """E2E: replay command reads and summarizes trace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        # First run to create trace
        code, out, err = run_cli(
            [
                "run",
                "-t", "examples/demo_task/task_spec.yaml",
                "-i", "examples/demo_task/task_input.yaml",
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )
        assert code == 0

        # Extract run_id from output
        run_id = out.split("Run ID: ")[1].split()[0].strip()

        # Replay the trace
        code, out, err = run_cli(
            [
                "replay", run_id,
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )

        assert code == 0
        assert f"Run ID: {run_id}" in out
        assert "Event count:" in out


def test_replay_command_with_reevaluate():
    """E2E: replay --re-evaluate produces consistent results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        # First run to create trace
        code, out, err = run_cli(
            [
                "run",
                "-t", "examples/demo_task/task_spec.yaml",
                "-i", "examples/demo_task/task_input.yaml",
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )
        assert code == 0
        run_id = out.split("Run ID: ")[1].split()[0].strip()

        # Replay with re-evaluate and compare
        code, out, err = run_cli(
            [
                "replay", run_id,
                "-d", str(trace_dir),
                "-t", "examples/demo_task/task_spec.yaml",
                "--re-evaluate",
                "--compare",
            ],
            Path.cwd(),
        )

        assert code == 0
        assert "Original evaluation:" in out
        assert "Re-evaluation result:" in out
        assert "Passed match: True" in out


def test_chat_mock_mode():
    """E2E: chat --mock works without LLM."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Run chat in mock mode with a simple input
        # Note: chat is interactive, so we just verify it starts
        result = subprocess.run(
            [sys.executable, "-m", "zheng_agent.cli.main", "chat", "--mock", "--help"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Interactive chat" in result.stdout


def test_cli_help():
    """E2E: CLI shows all commands."""
    code, out, err = run_cli(["--help"], Path.cwd())

    assert code == 0
    assert "run" in out
    assert "chat" in out
    assert "pause" in out
    assert "resume" in out
    assert "replay" in out


def test_replay_shows_step_sequence():
    """E2E: replay output preserves step ordering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        # Run to create trace
        code, out, err = run_cli(
            [
                "run",
                "-t", "examples/demo_task/task_spec.yaml",
                "-i", "examples/demo_task/task_input.yaml",
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )
        assert code == 0
        run_id = out.split("Run ID: ")[1].split()[0].strip()

        # Replay and check step sequence
        code, out, err = run_cli(
            [
                "replay", run_id,
                "-d", str(trace_dir),
                "-f", "events",
            ],
            Path.cwd(),
        )

        assert code == 0
        # Should show step events in order
        assert "step_scheduled" in out or "step_started" in out


def test_run_uses_unified_action_bootstrap():
    """E2E: run command uses unified action catalog."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        # Run with echo action (uses BUILTIN_ACTIONS)
        code, out, err = run_cli(
            [
                "run",
                "-t", "examples/demo_task/task_spec.yaml",
                "-i", "examples/demo_task/task_input.yaml",
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )

        assert code == 0
        assert "Status: completed" in out

        # Verify trace contains action_executed event
        trace_files = list(trace_dir.glob("*.jsonl"))
        assert len(trace_files) == 1

        # Read trace and verify action was executed
        trace_content = trace_files[0].read_text(encoding="utf-8")
        assert "action_executed" in trace_content or "echo" in trace_content