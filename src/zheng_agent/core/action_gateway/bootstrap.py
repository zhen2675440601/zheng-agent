"""Action bootstrap and catalog for unified action registration.

Provides a centralized source for action adapters, removing inline
registration from CLI commands and enabling consistent behavior
between fresh runs and resumed runs.
"""

from pathlib import Path
from typing import Callable

from zheng_agent.core.action_gateway.registry import ActionAdapterRegistry, ActionAdapter
from zheng_agent.core.contracts import TaskSpec


# Built-in action catalog
BUILTIN_ACTIONS: dict[str, ActionAdapter] = {
    "echo": lambda payload: {"echoed": payload.get("message", "")},
    "log": lambda payload: {"logged": payload.get("message", "")},
}


class ActionCatalog:
    """Catalog of available actions with metadata."""

    def __init__(self, builtin_actions: dict[str, ActionAdapter] | None = None):
        self._actions: dict[str, ActionAdapter] = builtin_actions or BUILTIN_ACTIONS.copy()
        self._metadata: dict[str, dict] = {}

    def register(
        self,
        action_name: str,
        adapter: ActionAdapter,
        metadata: dict | None = None,
    ) -> None:
        """Register an action with optional metadata."""
        self._actions[action_name] = adapter
        if metadata:
            self._metadata[action_name] = metadata

    def get(self, action_name: str) -> ActionAdapter | None:
        """Get action adapter by name."""
        return self._actions.get(action_name)

    def get_metadata(self, action_name: str) -> dict | None:
        """Get action metadata by name."""
        return self._metadata.get(action_name)

    def list_actions(self) -> list[str]:
        """List all registered action names."""
        return list(self._actions.keys())

    def is_available(self, action_name: str) -> bool:
        """Check if an action is available."""
        return action_name in self._actions


# Global catalog instance
_global_catalog: ActionCatalog | None = None


def get_catalog() -> ActionCatalog:
    """Get the global action catalog."""
    global _global_catalog
    if _global_catalog is None:
        _global_catalog = ActionCatalog()
    return _global_catalog


def reset_catalog() -> None:
    """Reset the global catalog (for testing)."""
    global _global_catalog
    _global_catalog = None


def create_registry_for_task(
    task_spec: TaskSpec,
    catalog: ActionCatalog | None = None,
) -> ActionAdapterRegistry:
    """Create a registry containing only actions allowed by task spec.

    Args:
        task_spec: TaskSpec defining allowed actions
        catalog: Catalog to use (defaults to global catalog)

    Returns:
        ActionAdapterRegistry with allowed actions registered
    """
    if catalog is None:
        catalog = get_catalog()

    registry = ActionAdapterRegistry()
    for action_name in task_spec.allowed_actions:
        adapter = catalog.get(action_name)
        if adapter is not None:
            registry.register(action_name, adapter)

    return registry


def load_actions_from_config(config_path: Path | None = None) -> None:
    """Load additional actions from a config file.

    Config file format (YAML):
    ```yaml
    actions:
      custom_action:
        type: module_path.to.function
        metadata:
          description: "Custom action description"
    ```

    Args:
        config_path: Path to actions config file (optional)
    """
    if config_path is None or not config_path.exists():
        return

    import yaml

    catalog = get_catalog()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    if not config or "actions" not in config:
        return

    for action_name, action_config in config["actions"].items():
        action_type = action_config.get("type")
        if action_type:
            # Dynamic import of action function
            module_path, func_name = action_type.rsplit(".", 1)
            try:
                import importlib
                module = importlib.import_module(module_path)
                adapter = getattr(module, func_name)
                catalog.register(action_name, adapter, action_config.get("metadata"))
            except (ImportError, AttributeError):
                # Skip actions that can't be loaded
                pass