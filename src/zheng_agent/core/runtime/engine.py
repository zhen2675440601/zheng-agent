from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from zheng_agent.core.action_gateway import ActionGatewayExecutor
from zheng_agent.core.agent.base import AgentProtocol
from zheng_agent.core.contracts import ActionRequest, RunContext, RunResult, TaskSpec
from zheng_agent.core.evaluation.base import RunEvaluator
from zheng_agent.core.runtime.state_store import RunState, RunStateStore
from zheng_agent.core.state_machine import apply_run_event, apply_step_event
from zheng_agent.core.tracing import JsonlTraceStore, build_trace_event, read_trace_events


@dataclass
class EngineOutcome:
    run_id: str
    run_result: RunResult
    eval_result: object


class HarnessEngine:
    def __init__(self, trace_root: Path, gateway: ActionGatewayExecutor, evaluator: RunEvaluator):
        self.trace_root = trace_root
        self.gateway = gateway
        self.evaluator = evaluator
        self._pause_requested = False
        self._state_store = RunStateStore(trace_root)

    def _pause_signal_path(self, run_id: str) -> Path:
        return self.trace_root / f"{run_id}.pause_signal"

    def _check_pause_signal(self, run_id: str) -> bool:
        return self._pause_signal_path(run_id).exists()

    def _clear_pause_signal(self, run_id: str) -> None:
        signal_path = self._pause_signal_path(run_id)
        if signal_path.exists():
            signal_path.unlink()

    def _make_step_id(self, step_index: int) -> str:
        return f"step-{step_index + 1}"

    def _save_checkpoint(
        self,
        run_id: str,
        run_status: str,
        step_id: str | None,
        step_status: str,
        step_index: int,
        sequence: int,
        task_spec: TaskSpec,
        task_input: dict,
        agent: AgentProtocol,
        checkpoint_kind: str,
        started_at: str,
        checkpoint_reason: str | None = None,
    ) -> None:
        state = RunState(
            run_id=run_id,
            run_status=run_status,
            step_id=step_id,
            step_status=step_status,
            step_index=step_index,
            sequence=sequence,
            started_at=started_at,
            task_spec=task_spec,
            task_input=task_input,
            agent_recovery=agent.get_recovery_metadata(),
            checkpoint_kind=checkpoint_kind,
            checkpoint_reason=checkpoint_reason,
        )
        self._state_store.save(state)

    def request_pause(self) -> None:
        self._pause_requested = True

    def request_pause_external(self, run_id: str) -> None:
        self._pause_signal_path(run_id).write_text("pause", encoding="utf-8")

    def run(
        self,
        task_spec: TaskSpec,
        task_input: dict,
        agent: AgentProtocol,
        run_id: str | None = None,
        initial_state: RunState | None = None,
    ) -> EngineOutcome:
        if run_id is None:
            run_id = str(uuid4())

        trace_store = JsonlTraceStore(self.trace_root / f"{run_id}.jsonl")
        trace_path = self.trace_root / f"{run_id}.jsonl"

        if initial_state:
            run_status = initial_state.run_status
            step_status = initial_state.step_status
            sequence = initial_state.sequence
            step_id = initial_state.step_id
            step_index = initial_state.step_index
            started_at = initial_state.started_at or datetime.now(UTC).isoformat()
            if initial_state.agent_recovery:
                agent.restore_from_metadata(initial_state.agent_recovery)
        else:
            run_status = "created"
            step_status = "pending"
            sequence = 0
            step_id = None
            step_index = 0
            started_at = datetime.now(UTC).isoformat()

        def current_trace() -> list:
            return read_trace_events(trace_path)

        def refresh_context() -> None:
            run_context.visible_trace = [
                event.model_dump(mode="json")
                for event in current_trace()
            ]
            run_context.step_index = step_index

        def emit(event_type: str, payload: dict, step_id: str | None = None):
            nonlocal sequence
            sequence += 1
            trace_store.append(
                build_trace_event(
                    run_id=run_id,
                    step_id=step_id,
                    event_type=event_type,
                    payload=payload,
                    sequence_number=sequence,
                )
            )

        def fail_run(error: str, *, reason: str, include_step_failure: bool = True) -> EngineOutcome:
            nonlocal run_status, step_status
            if include_step_failure and step_id is not None and step_status not in {"completed", "failed"}:
                emit(
                    "step_failed",
                    {"step_id": step_id, "step_index": step_index, "reason": reason},
                    step_id=step_id,
                )
                step_status = "failed"
            if run_status != "failed":
                run_status = apply_run_event(run_status, "run_failed")
            emit("run_failed", {"error": error, "step_id": step_id})
            run_result = RunResult(
                run_id=run_id,
                task_type=task_spec.task_type,
                status="failed",
                error=error,
            )
            trace = current_trace()
            eval_result = self.evaluator.evaluate(task_spec, trace, run_result)
            emit(
                "evaluation_completed",
                {
                    "passed": eval_result.passed,
                    "score": eval_result.score,
                    "reasons": eval_result.reasons,
                    "metrics": eval_result.metrics,
                },
            )
            self._state_store.delete(run_id)
            return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)

        def timed_out() -> bool:
            if task_spec.timeout_seconds is None:
                return False
            started = datetime.fromisoformat(started_at)
            return (datetime.now(UTC) - started).total_seconds() >= task_spec.timeout_seconds

        def enforce_timeout() -> EngineOutcome | None:
            if not timed_out():
                return None
            return fail_run(
                f"run exceeded timeout_seconds={task_spec.timeout_seconds}",
                reason="timeout_exceeded",
            )

        def enforce_step_limit_before_start() -> EngineOutcome | None:
            if step_index < task_spec.max_steps:
                return None
            return fail_run(
                f"run exceeded max_steps={task_spec.max_steps}",
                reason="max_steps_exceeded",
                include_step_failure=False,
            )

        def start_new_step() -> str:
            nonlocal step_status, step_id
            step_id = self._make_step_id(step_index)
            step_status = apply_step_event("pending", "step_scheduled")
            emit("step_scheduled", {"step_id": step_id, "step_index": step_index}, step_id=step_id)
            step_status = apply_step_event(step_status, "step_started")
            emit("step_started", {"step_id": step_id, "step_index": step_index}, step_id=step_id)
            self._save_checkpoint(
                run_id,
                run_status,
                step_id,
                step_status,
                step_index,
                sequence,
                task_spec,
                task_input,
                agent,
                "step_boundary",
                started_at,
                "step_started",
            )
            return step_id

        def advance_to_next_step() -> EngineOutcome | str:
            nonlocal step_index, step_status, step_id
            emit("step_completed", {"step_id": step_id, "step_index": step_index}, step_id=step_id)
            step_status = "completed"
            step_index += 1
            step_limit_failure = enforce_step_limit_before_start()
            if step_limit_failure is not None:
                return step_limit_failure
            return start_new_step()

        if run_status == "created":
            emit("run_created", {"task_type": task_spec.task_type})
            run_status = apply_run_event(run_status, "validate_passed")
            emit("run_validated", {})
            run_status = apply_run_event(run_status, "prepare_run")
            emit("run_prepared", {})
            run_status = apply_run_event(run_status, "start_run")
            emit("run_started", {"started_at": started_at})

        if run_status == "paused":
            self._clear_pause_signal(run_id)
            run_status = apply_run_event(run_status, "resume_requested")
            emit("run_resumed", {"from_step": step_id, "from_step_index": step_index, "started_at": started_at})

        timeout_failure = enforce_timeout()
        if timeout_failure is not None:
            return timeout_failure

        if step_id is None:
            step_limit_failure = enforce_step_limit_before_start()
            if step_limit_failure is not None:
                return step_limit_failure
            start_new_step()

        run_context = RunContext(run_id=run_id, task_spec=task_spec, task_input=task_input)
        refresh_context()

        while True:
            timeout_failure = enforce_timeout()
            if timeout_failure is not None:
                return timeout_failure

            if self._pause_requested or self._check_pause_signal(run_id):
                self._pause_requested = False
                self._clear_pause_signal(run_id)
                run_status = apply_run_event(run_status, "pause_requested")
                emit("run_paused", {"step_id": step_id, "step_index": step_index, "checkpoint_kind": "pause"})
                self._save_checkpoint(
                    run_id,
                    run_status,
                    step_id,
                    step_status,
                    step_index,
                    sequence,
                    task_spec,
                    task_input,
                    agent,
                    "pause",
                    started_at,
                    "user_requested",
                )
                run_result = RunResult(
                    run_id=run_id,
                    task_type=task_spec.task_type,
                    status="paused",
                )
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=None)

            decision = agent.decide(task_spec, run_context)
            emit(
                "agent_decision_produced",
                {"decision_type": decision.decision_type, "step_id": step_id},
                step_id=step_id,
            )

            if decision.decision_type == "request_action":
                step_status = apply_step_event(step_status, "decision_request_action")
                run_status = apply_run_event(run_status, "action_requested")
                emit("action_requested", {"action_name": decision.action_name}, step_id=step_id)
                self._save_checkpoint(
                    run_id,
                    run_status,
                    step_id,
                    step_status,
                    step_index,
                    sequence,
                    task_spec,
                    task_input,
                    agent,
                    "action_before",
                    started_at,
                    f"action:{decision.action_name}",
                )

                request = ActionRequest(
                    run_id=run_id,
                    step_id=step_id,
                    action_name=decision.action_name,
                    action_input=decision.action_input,
                    requested_by="agent",
                )
                action_result = self.gateway.execute(task_spec, request)

                if action_result.status == "success":
                    emit("action_approved", {"action_name": request.action_name}, step_id=step_id)
                    emit("action_executed", {"output": action_result.output}, step_id=step_id)
                    step_status = apply_step_event(step_status, "action_completed")
                    run_status = apply_run_event(run_status, "action_completed")
                    self._save_checkpoint(
                        run_id,
                        run_status,
                        step_id,
                        step_status,
                        step_index,
                        sequence,
                        task_spec,
                        task_input,
                        agent,
                        "action_after",
                        started_at,
                        f"action:{decision.action_name}",
                    )
                    run_context.action_count += 1
                    refresh_context()
                    continue

                if action_result.status == "rejected":
                    emit("action_rejected", {"error": action_result.error}, step_id=step_id)
                    emit("step_failed", {"step_id": step_id, "step_index": step_index, "reason": "action_rejected"}, step_id=step_id)
                    step_status = "failed"
                    run_status = apply_run_event(run_status, "action_rejected")
                    return fail_run(action_result.error or "action rejected", reason="action_rejected", include_step_failure=False)

                emit("action_failed", {"error": action_result.error}, step_id=step_id)
                emit("step_failed", {"step_id": step_id, "step_index": step_index, "reason": "action_failed"}, step_id=step_id)
                step_status = "failed"
                run_status = apply_run_event(run_status, "action_failed")
                return fail_run(action_result.error or "action failed", reason="action_failed", include_step_failure=False)

            if decision.decision_type == "respond":
                emit("agent_response", {"response": decision.response, "step_id": step_id}, step_id=step_id)
                refresh_context()
                continue

            if decision.decision_type == "advance_step":
                emit("step_advance_requested", {"step_id": step_id, "step_index": step_index}, step_id=step_id)
                next_step = advance_to_next_step()
                if isinstance(next_step, EngineOutcome):
                    return next_step
                step_id = next_step
                refresh_context()
                continue

            if decision.decision_type == "complete":
                step_status = apply_step_event(step_status, "decision_complete")
                emit("step_completed", {"step_id": step_id, "step_index": step_index}, step_id=step_id)
                run_status = apply_run_event(run_status, "run_succeeded")
                run_result = RunResult(
                    run_id=run_id,
                    task_type=task_spec.task_type,
                    status="completed",
                    output=decision.final_result,
                )
                emit("run_completed", {"status": run_status, "output": decision.final_result, "total_steps": step_index + 1})
                trace = current_trace()
                eval_result = self.evaluator.evaluate(task_spec, trace, run_result)
                emit(
                    "evaluation_completed",
                    {
                        "passed": eval_result.passed,
                        "score": eval_result.score,
                        "reasons": eval_result.reasons,
                        "metrics": eval_result.metrics,
                    },
                )
                self._state_store.delete(run_id)
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)

            if decision.decision_type == "fail":
                return fail_run(decision.failure_reason, reason=decision.failure_reason or "agent_failed")

    def resume(self, run_id: str, agent: AgentProtocol) -> EngineOutcome:
        state = self._state_store.load(run_id)
        if state is None:
            raise ValueError(f"No paused state found for run_id: {run_id}")
        if state.run_status != "paused":
            raise ValueError(f"Run {run_id} is not paused (status: {state.run_status})")

        return self.run(
            task_spec=state.task_spec,
            task_input=state.task_input,
            agent=agent,
            run_id=run_id,
            initial_state=state,
        )

    def get_state(self, run_id: str) -> RunState | None:
        return self._state_store.load(run_id)
