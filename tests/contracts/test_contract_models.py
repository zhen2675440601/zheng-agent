import importlib


def test_package_imports_before_contracts_exist():
    package = importlib.import_module("zheng_agent")
    assert package.__name__ == "zheng_agent"