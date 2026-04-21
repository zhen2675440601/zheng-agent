from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from zheng_agent.core.action_gateway import ActionGatewayExecutor
from zheng_agent.core.agent.base import AgentProtocol
from zheng_agent.core.agent.mock import ScriptedMockAgent
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

    def request_pause(self) -> None:
        """Signal the engine to pause at the next checkpoint."""
        self._pause_requested = True

    def run(
        self,
        task_spec: TaskSpec,
        task_input: dict,
        agent: AgentProtocol,
        run_id: str | None = None,
        initial_state: RunState | None = None,
    ) -> EngineOutcome:
        """Execute a task, optionally resuming from a paused state."""
        if run_id is None:
            run_id = str(uuid4())

        trace_store = JsonlTraceStore(self.trace_root / f"{run_id}.jsonl")

        # Initialize or restore state
        if initial_state:
            run_status = initial_state.run_status
            step_status = initial_state.step_status
            sequence = initial_state.sequence
            step_id = initial_state.step_id
            agent_decisions_index = initial_state.agent_decisions_index
            # Restore agent position for ScriptedMockAgent
            if isinstance(agent, ScriptedMockAgent):
                agent._index = agent_decisions_index
        else:
            run_status = "created"
            step_status = "pending"
            sequence = 0
            step_id = None
            agent_decisions_index = 0

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

        # Start phase (if not resuming from paused)
        if run_status == "created":
            emit("run_created", {"task_type": task_spec.task_type})
            run_status = apply_run_event(run_status, "validate_passed")
            emit("run_validated", {})
            run_status = apply_run_event(run_status, "prepare_run")
            emit("run_prepared", {})
            run_status = apply_run_event(run_status, "start_run")
            emit("run_started", {})

        if run_status == "paused":
            run_status = apply_run_event(run_status, "resume_requested")
            emit("run_resumed", {})

        # Step phase
        if step_id is None:
            step_id = "step-1"
            step_status = apply_step_event(step_status, "step_scheduled")
            emit("step_scheduled", {"step_id": step_id}, step_id=step_id)
            step_status = apply_step_event(step_status, "step_started")
            emit("step_started", {"step_id": step_id}, step_id=step_id)

        run_context = RunContext(run_id=run_id, task_spec=task_spec, task_input=task_input)
        run_context.visible_trace = [
            event.model_dump(mode="json")
            for event in read_trace_events(self.trace_root / f"{run_id}.jsonl")
        ]

        while True:
            # Check for pause request
            if self._pause_requested:
                run_status = apply_run_event(run_status, "pause_requested")
                emit("run_paused", {"step_id": step_id})
                state = RunState(
                    run_id=run_id,
                    run_status=run_status,
                    step_id=step_id,
                    step_status=step_status,
                    sequence=sequence,
                    task_spec=task_spec,
                    task_input=task_input,
                    agent_decisions_index=agent_decisions_index if isinstance(agent, ScriptedMockAgent) else 0,
                )
                self._state_store.save(state)
                run_result = RunResult(
                    run_id=run_id,
                    task_type=task_spec.task_type,
                    status="paused",
                )
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=None)

            decision = agent.decide(task_spec, run_context)
            agent_decisions_index += 1
            emit(
                "agent_decision_produced",
                {"decision_type": decision.decision_type},
                step_id=step_id,
            )

            if decision.decision_type == "request_action":
                step_status = apply_step_event(step_status, "decision_request_action")
                run_status = apply_run_event(run_status, "action_requested")
                emit("action_requested", {"action_name": decision.action_name}, step_id=step_id)

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
                    run_context.visible_trace = [
                        event.model_dump(mode="json")
                        for event in read_trace_events(self.trace_root / f"{run_id}.jsonl")
                    ]
                    run_context.step_index += 1
                    continue

                if action_result.status == "rejected":
                    emit("action_rejected", {"error": action_result.error}, step_id=step_id)
                    step_status = apply_step_event(step_status, "action_rejected")
                    emit("step_failed", {"step_id": step_id, "reason": "action_rejected"}, step_id=step_id)
                    run_status = apply_run_event(run_status, "action_rejected")
                else:
                    emit("action_failed", {"error": action_result.error}, step_id=step_id)
                    step_status = apply_step_event(step_status, "action_failed")
                    emit("step_failed", {"step_id": step_id, "reason": "action_failed"}, step_id=step_id)
                    run_status = apply_run_event(run_status, "action_failed")

                run_result = RunResult(
                    run_id=run_id,
                    task_type=task_spec.task_type,
                    status="failed",
                    error=action_result.error,
                )
                trace = read_trace_events(self.trace_root / f"{run_id}.jsonl")
                eval_result = self.evaluator.evaluate(task_spec, trace, run_result)
                emit("run_failed", {"error": action_result.error})
                emit("evaluation_completed", {"passed": eval_result.passed})
                self._state_store.delete(run_id)
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)

            if decision.decision_type == "complete":
                step_status = apply_step_event(step_status, "decision_complete")
                emit("step_completed", {"step_id": step_id}, step_id=step_id)
                run_status = apply_run_event(run_status, "run_succeeded")
                emit("run_completed", {"status": run_status})
                run_result = RunResult(
                    run_id=run_id,
                    task_type=task_spec.task_type,
                    status="completed",
                    output=decision.final_result,
                )
                trace = read_trace_events(self.trace_root / f"{run_id}.jsonl")
                eval_result = self.evaluator.evaluate(task_spec, trace, run_result)
                emit("evaluation_completed", {"passed": eval_result.passed})
                self._state_store.delete(run_id)
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)

            if decision.decision_type == "fail":
                emit("step_failed", {"step_id": step_id, "reason": decision.failure_reason}, step_id=step_id)
                step_status = apply_step_event(step_status, "decision_fail")
                run_status = apply_run_event(run_status, "run_failed")
                emit("run_failed", {"error": decision.failure_reason})
                run_result = RunResult(
                    run_id=run_id,
                    task_type=task_spec.task_type,
                    status="failed",
                    error=decision.failure_reason,
                )
                trace = read_trace_events(self.trace_root / f"{run_id}.jsonl")
                eval_result = self.evaluator.evaluate(task_spec, trace, run_result)
                emit("evaluation_completed", {"passed": eval_result.passed})
                self._state_store.delete(run_id)
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)

    def resume(self, run_id: str, agent: AgentProtocol) -> EngineOutcome:
        """Resume a paused run."""
        state = self._state_store.load(run_id)
        if state is None:
            raise ValueError(f"No paused state found for run_id: {run_id}")
        if state.run_status != "paused":
            raise ValueError(f"Run {run_id} is not paused (status: {state.run_status})")

        self._pause_requested = False  # Reset pause flag before resuming
        return self.run(
            task_spec=state.task_spec,
            task_input=state.task_input,
            agent=agent,
            run_id=run_id,
            initial_state=state,
        )

    def get_state(self, run_id: str) -> RunState | None:
        """Get the current state of a run."""
        return self._state_store.load(run_id)