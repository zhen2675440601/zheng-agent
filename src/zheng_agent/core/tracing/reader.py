import json
from pathlib import Path

from zheng_agent.core.tracing.events import TraceEvent


def read_trace_events(path: Path) -> list[TraceEvent]:
    if not path.exists():
        return []

    events: list[TraceEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                events.append(TraceEvent.model_validate(json.loads(line)))
    return events