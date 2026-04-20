from zheng_agent.core.contracts import TaskSpec, validate_input, validate_output


def test_validate_input_passes_valid_data():
    schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }
    data = {"message": "hello"}

    valid, errors = validate_input(schema, data)

    assert valid is True
    assert errors == []


def test_validate_input_fails_missing_required():
    schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }
    data = {}

    valid, errors = validate_input(schema, data)

    assert valid is False
    assert len(errors) == 1


def test_validate_input_fails_wrong_type():
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    data = {"count": "not_an_integer"}

    valid, errors = validate_input(schema, data)

    assert valid is False


def test_validate_output_passes_with_required_keys():
    schema = {"required_keys": ["message"]}
    data = {"message": "hello"}

    valid, errors = validate_output(schema, data)

    assert valid is True
    assert errors == []


def test_validate_output_fails_missing_required_keys():
    schema = {"required_keys": ["message", "status"]}
    data = {"message": "hello"}

    valid, errors = validate_output(schema, data)

    assert valid is False
    assert len(errors) == 1
    assert "status" in errors[0]


def test_validate_output_handles_none():
    schema = {"required_keys": ["message"]}

    valid, errors = validate_output(schema, None)

    assert valid is False
    assert "None" in errors[0] or "missing" in errors[0]


def test_validate_empty_schema_always_passes():
    data = {"anything": "goes"}

    valid, errors = validate_input({}, data)
    assert valid is True

    valid, errors = validate_output({}, data)
    assert valid is True