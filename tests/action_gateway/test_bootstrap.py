"""Tests for action bootstrap and catalog."""

from pathlib import Path

from zheng_agent.core.action_gateway import (
    ActionAdapterRegistry,
    ActionCatalog,
    BUILTIN_ACTIONS,
    create_registry_for_task,
    get_catalog,
    reset_catalog,
)
from zheng_agent.core.contracts import TaskSpec


def test_builtin_actions_catalog_contains_echo_and_log():
    """Builtin catalog contains core actions."""
    assert "echo" in BUILTIN_ACTIONS
    assert "log" in BUILTIN_ACTIONS
    # v0.5 添加了更多内置动作用于多步骤任务测试
    assert "fetch_data" in BUILTIN_ACTIONS
    assert "analyze" in BUILTIN_ACTIONS
    assert "summarize" in BUILTIN_ACTIONS


def test_catalog_register_adds_new_action():
    """Catalog can register new actions."""
    catalog = ActionCatalog()
    catalog.register("custom_action", lambda payload: {"custom": payload.get("value")})

    assert catalog.is_available("custom_action")
    assert catalog.get("custom_action") is not None


def test_catalog_register_with_metadata():
    """Catalog can register actions with metadata."""
    catalog = ActionCatalog()
    catalog.register(
        "annotated_action",
        lambda payload: {"result": True},
        metadata={"description": "An annotated action", "version": "1.0"},
    )

    metadata = catalog.get_metadata("annotated_action")
    assert metadata is not None
    assert metadata["description"] == "An annotated action"
    assert metadata["version"] == "1.0"


def test_catalog_list_actions_returns_all_names():
    """list_actions returns all registered action names."""
    catalog = ActionCatalog(builtin_actions={"echo": lambda p: {}, "log": lambda p: {}})
    catalog.register("custom", lambda p: {})

    actions = catalog.list_actions()
    assert "echo" in actions
    assert "log" in actions
    assert "custom" in actions
    assert len(actions) == 3


def test_get_catalog_returns_global_instance():
    """get_catalog returns a global singleton catalog."""
    reset_catalog()
    catalog1 = get_catalog()
    catalog2 = get_catalog()

    assert catalog1 is catalog2


def test_reset_catalog_clears_global_instance():
    """reset_catalog clears the global catalog."""
    catalog1 = get_catalog()
    catalog1.register("temp_action", lambda p: {})

    reset_catalog()
    catalog2 = get_catalog()

    # New catalog should be different instance with no temp_action
    assert catalog1 is not catalog2
    assert not catalog2.is_available("temp_action")


def test_create_registry_for_task_filters_by_allowed_actions():
    """create_registry_for_task only registers allowed actions."""
    spec = TaskSpec(
        task_type="test",
        title="Test",
        description="Test task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],  # Only echo, not log
    )

    registry = create_registry_for_task(spec)

    assert registry.get("echo") is not None
    assert registry.get("log") is None  # log is not allowed


def test_create_registry_for_task_with_custom_catalog():
    """create_registry_for_task can use a custom catalog."""
    custom_catalog = ActionCatalog()
    custom_catalog.register("custom_echo", lambda payload: {"custom": payload.get("message")})

    spec = TaskSpec(
        task_type="test",
        title="Test",
        description="Test task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["custom_echo"],
    )

    registry = create_registry_for_task(spec, catalog=custom_catalog)

    assert registry.get("custom_echo") is not None


def test_registry_from_catalog_executes_actions():
    """Registry created from catalog can execute actions."""
    spec = TaskSpec(
        task_type="test",
        title="Test",
        description="Test task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = create_registry_for_task(spec)
    adapter = registry.get("echo")

    result = adapter({"message": "hello"})
    assert result["echoed"] == "hello"


def test_catalog_is_available_returns_false_for_missing_action():
    """is_available returns False for unregistered actions."""
    catalog = ActionCatalog()
    assert not catalog.is_available("nonexistent_action")


def test_catalog_get_returns_none_for_missing_action():
    """get returns None for unregistered actions."""
    catalog = ActionCatalog()
    assert catalog.get("nonexistent_action") is None


def test_catalog_get_metadata_returns_none_for_missing_action():
    """get_metadata returns None for actions without metadata."""
    catalog = ActionCatalog()
    catalog.register("no_metadata_action", lambda p: {})

    assert catalog.get_metadata("no_metadata_action") is None
    assert catalog.get_metadata("nonexistent_action") is None


def test_create_registry_for_task_empty_allowed_actions():
    """create_registry_for_task with empty allowed_actions creates empty registry."""
    spec = TaskSpec(
        task_type="test",
        title="Test",
        description="Test task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=[],  # No allowed actions
    )

    registry = create_registry_for_task(spec)

    assert registry.get("echo") is None
    assert registry.get("log") is None