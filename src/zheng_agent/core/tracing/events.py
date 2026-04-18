from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


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