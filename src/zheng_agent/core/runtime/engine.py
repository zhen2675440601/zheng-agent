from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from zheng_agent.core.action_gateway import ActionGatewayExecutor
from zheng_agent.core.agent.base import AgentProtocol
from zheng_agent.core.contracts import ActionRequest, RunContext, RunResult, TaskSpec
from zheng_agent.core.evaluation.base import RunEvaluator
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

    def run(self, task_spec: TaskSpec, task_input: dict, agent: AgentProtocol) -> EngineOutcome:
        run_id = str(uuid4())
        trace_store = JsonlTraceStore(self.trace_root / f"{run_id}.jsonl")
        run_status = "created"
        step_status = "pending"
        sequence = 0

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

        emit("run_created", {"task_type": task_spec.task_type})
        run_status = apply_run_event(run_status, "validate_passed")
        emit("run_validated", {})
        run_status = apply_run_event(run_status, "prepare_run")
        emit("run_prepared", {})
        run_status = apply_run_event(run_status, "start_run")
        emit("run_started", {})

        step_id = "step-1"
        step_status = apply_step_event(step_status, "step_scheduled")
        emit("step_scheduled", {"step_id": step_id}, step_id=step_id)
        step_status = apply_step_event(step_status, "step_started")
        emit("step_started", {"step_id": step_id}, step_id=step_id)

        run_context = RunContext(run_id=run_id, task_spec=task_spec, task_input=task_input)

        while True:
            decision = agent.decide(task_spec, run_context)
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
                    requested_by="mock-agent",
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
                    run_context.step_index = 1
                    continue

                if action_result.status == "rejected":
                    emit("action_rejected", {"error": action_result.error}, step_id=step_id)
                    step_status = apply_step_event(step_status, "action_rejected")
                    run_status = apply_run_event(run_status, "action_rejected")
                else:
                    emit("action_failed", {"error": action_result.error}, step_id=step_id)
                    step_status = apply_step_event(step_status, "action_failed")
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
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)

            if decision.decision_type == "fail":
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
                return EngineOutcome(run_id=run_id, run_result=run_result, eval_result=eval_result)