from pathlib import Path

from zheng_agent.core.tracing.reader import read_trace_events


def replay_trace(path: Path) -> dict:
    events = read_trace_events(path)
    if not events:
        return {
            "run_id": None,
            "event_count": 0,
            "terminal_event": None,
            "step_ids": [],
        }

    return {
        "run_id": events[0].run_id,
        "event_count": len(events),
        "terminal_event": events[-1].event_type,
        "step_ids": [event.step_id for event in events if event.step_id is not None],
    }