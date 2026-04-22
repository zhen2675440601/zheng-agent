"""End-to-end tests for CLI commands."""

import subprocess
import sys
from pathlib import Path
import tempfile


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

        trace_files = list(trace_dir.glob("*.jsonl"))
        assert len(trace_files) == 1



def test_run_command_validates_input():
    """E2E: run command validates input against schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

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



def test_cli_version_matches_package():
    """E2E: CLI version reflects package version."""
    code, out, err = run_cli(["--version"], Path.cwd())

    assert code == 0
    assert "0.5.0" in out



def test_replay_shows_step_sequence():
    """E2E: replay output preserves step ordering."""
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
        run_id = out.split("Run ID: ")[1].split()[0].strip()

        code, out, err = run_cli(
            [
                "replay", run_id,
                "-d", str(trace_dir),
                "-f", "events",
            ],
            Path.cwd(),
        )

        assert code == 0
        assert "step_scheduled" in out or "step_started" in out



def test_run_uses_unified_action_bootstrap():
    """E2E: run command uses unified action catalog."""
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
        assert "Status: completed" in out

        trace_files = list(trace_dir.glob("*.jsonl"))
        assert len(trace_files) == 1

        trace_content = trace_files[0].read_text(encoding="utf-8")
        assert "action_executed" in trace_content or "echo" in trace_content



def test_run_pause_resume_replay_lifecycle():
    """E2E: run/pause/resume/replay lifecycle preserves successful evaluation."""
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
        run_id = out.split("Run ID: ")[1].split()[0].strip()

        pause_code, pause_out, pause_err = run_cli(
            ["pause", run_id, "-d", str(trace_dir)],
            Path.cwd(),
        )
        assert pause_code == 1
        assert "No checkpoint found" in pause_err or "No checkpoint found" in pause_out

        resume_code, resume_out, resume_err = run_cli(
            ["resume", run_id, "-d", str(trace_dir)],
            Path.cwd(),
        )
        assert resume_code == 1
        assert "No checkpoint found" in resume_err or "No checkpoint found" in resume_out

        replay_code, replay_out, replay_err = run_cli(
            [
                "replay", run_id,
                "-d", str(trace_dir),
                "-t", "examples/demo_task/task_spec.yaml",
                "--re-evaluate",
                "--compare",
            ],
            Path.cwd(),
        )
        assert replay_code == 0
        assert "Passed match: True" in replay_out



def test_run_respects_max_steps_guardrail():
    """E2E: runtime guardrails fail runs that exceed declared limits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        trace_dir = tmp / "traces"
        trace_dir.mkdir()

        limited_spec = tmp / "limited_task.yaml"
        limited_spec.write_text(
            "task_type: limited_demo\n"
            "title: Limited Demo\n"
            "description: Demo task with tight step budget\n"
            "input_schema:\n"
            "  type: object\n"
            "output_schema:\n"
            "  type: object\n"
            "allowed_actions:\n"
            "  - echo\n"
            "max_steps: 0\n"
            "timeout_seconds: 300\n",
            encoding="utf-8",
        )

        input_file = tmp / "input.yaml"
        input_file.write_text("{}\n", encoding="utf-8")

        code, out, err = run_cli(
            [
                "run",
                "-t", str(limited_spec),
                "-i", str(input_file),
                "-a", "mock",
                "-d", str(trace_dir),
            ],
            Path.cwd(),
        )

        assert code == 0
        assert "Status: failed" in out
        assert "Passed: False" in out
        assert "run_status_failed" in out
