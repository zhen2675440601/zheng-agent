from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

TraceEventVersion = Literal["1.0"]


class RunCreatedPayload(BaseModel):
    task_type: str


class RunValidatedPayload(BaseModel):
    input_valid: bool = True


class RunPreparedPayload(BaseModel):
    pass


class RunStartedPayload(BaseModel):
    pass


class RunPausedPayload(BaseModel):
    step_id: str | None = None
    checkpoint_kind: str = "pause"


class RunResumedPayload(BaseModel):
    from_checkpoint: bool = True


class RunCompletedPayload(BaseModel):
    status: str = "completed"
    output: dict | None = None


class RunFailedPayload(BaseModel):
    error: str
    step_id: str | None = None


class StepScheduledPayload(BaseModel):
    step_id: str


class StepStartedPayload(BaseModel):
    step_id: str


class StepCompletedPayload(BaseModel):
    step_id: str


class StepFailedPayload(BaseModel):
    step_id: str
    reason: str


class AgentDecisionPayload(BaseModel):
    decision_type: str
    action_name: str | None = None


class ActionRequestedPayload(BaseModel):
    action_name: str


class ActionApprovedPayload(BaseModel):
    action_name: str
    request_id: str | None = None


class ActionRejectedPayload(BaseModel):
    action_name: str
    error: str
    request_id: str | None = None


class ActionExecutedPayload(BaseModel):
    output: dict | None = None
    request_id: str | None = None


class ActionFailedPayload(BaseModel):
    error: str
    request_id: str | None = None


class EvaluationCompletedPayload(BaseModel):
    passed: bool
    score: float
    reasons: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


TypedPayload = (
    RunCreatedPayload
    | RunValidatedPayload
    | RunPreparedPayload
    | RunStartedPayload
    | RunPausedPayload
    | RunResumedPayload
    | RunCompletedPayload
    | RunFailedPayload
    | StepScheduledPayload
    | StepStartedPayload
    | StepCompletedPayload
    | StepFailedPayload
    | AgentDecisionPayload
    | ActionRequestedPayload
    | ActionApprovedPayload
    | ActionRejectedPayload
    | ActionExecutedPayload
    | ActionFailedPayload
    | EvaluationCompletedPayload
)


EVENT_PAYLOAD_TYPES: dict[str, type[BaseModel]] = {
    "run_created": RunCreatedPayload,
    "run_validated": RunValidatedPayload,
    "run_prepared": RunPreparedPayload,
    "run_started": RunStartedPayload,
    "run_paused": RunPausedPayload,
    "run_resumed": RunResumedPayload,
    "run_completed": RunCompletedPayload,
    "run_failed": RunFailedPayload,
    "step_scheduled": StepScheduledPayload,
    "step_started": StepStartedPayload,
    "step_completed": StepCompletedPayload,
    "step_failed": StepFailedPayload,
    "agent_decision_produced": AgentDecisionPayload,
    "action_requested": ActionRequestedPayload,
    "action_approved": ActionApprovedPayload,
    "action_rejected": ActionRejectedPayload,
    "action_executed": ActionExecutedPayload,
    "action_failed": ActionFailedPayload,
    "evaluation_completed": EvaluationCompletedPayload,
}


class TraceEvent(BaseModel):
    event_id: str
    run_id: str
    step_id: str | None = None
    event_type: str
    timestamp: datetime
    payload: dict
    sequence_number: int
    caused_by_event_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    version: TraceEventVersion = "1.0"

    def get_typed_payload(self) -> TypedPayload | None:
        payload_cls = EVENT_PAYLOAD_TYPES.get(self.event_type)
        if payload_cls:
            try:
                return payload_cls.model_validate(self.payload)
            except Exception:
                # Return None if payload doesn't match schema
                return None
        return None


def build_trace_event(
    *,
    run_id: str,
    step_id: str | None,
    event_type: str,
    payload: dict,
    sequence_number: int,
    caused_by_event_id: str | None = None,
    metadata: dict | None = None,
) -> TraceEvent:
    return TraceEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        step_id=step_id,
        event_type=event_type,
        timestamp=datetime.now(UTC),
        payload=payload,
        sequence_number=sequence_number,
        caused_by_event_id=caused_by_event_id,
        metadata=metadata or {},
    )


def build_typed_trace_event(
    *,
    run_id: str,
    step_id: str | None,
    event_type: str,
    payload: TypedPayload,
    sequence_number: int,
    caused_by_event_id: str | None = None,
    metadata: dict | None = None,
) -> TraceEvent:
    return TraceEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        step_id=step_id,
        event_type=event_type,
        timestamp=datetime.now(UTC),
        payload=payload.model_dump(mode="json"),
        sequence_number=sequence_number,
        caused_by_event_id=caused_by_event_id,
        metadata=metadata or {},
    )