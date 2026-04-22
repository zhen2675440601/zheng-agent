from collections.abc import Callable

ActionAdapter = Callable[[dict], dict]


class ActionAdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, ActionAdapter] = {}

    def register(self, action_name: str, adapter: ActionAdapter) -> None:
        self._adapters[action_name] = adapter

    def get(self, action_name: str) -> ActionAdapter | None:
        return self._adapters.get(action_name)