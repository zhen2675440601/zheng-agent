import jsonschema
from jsonschema import ValidationError


def validate_input(schema: dict, data: dict) -> tuple[bool, list[str]]:
    """Validate input data against input_schema."""
    if not schema:
        return True, []
    try:
        jsonschema.validate(data, schema)
        return True, []
    except ValidationError as e:
        return False, [f"input validation error: {e.message}"]


def validate_output(schema: dict, data: dict | None) -> tuple[bool, list[str]]:
    """Validate output data against output_schema."""
    if not schema:
        return True, []

    if data is None:
        # Check if schema requires properties
        required = schema.get("required_keys", schema.get("required", []))
        if required:
            return False, ["output is None but schema requires fields"]
        return True, []

    errors: list[str] = []

    # Check required_keys (simple format from demo)
    required_keys = schema.get("required_keys", [])
    for key in required_keys:
        if key not in data:
            errors.append(f"missing required key: {key}")

    # If schema has standard JSON Schema format, validate fully
    if "type" in schema and "properties" in schema:
        try:
            jsonschema.validate(data, schema)
        except ValidationError as e:
            errors.append(f"output validation error: {e.message}")

    return not errors, errors