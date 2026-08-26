import pytest
from unittest.mock import MagicMock

from apps.checklists.validators import validate_field_value


def make_field(field_type, options_json=None, label="Campo Test"):
    field = MagicMock()
    field.field_type = field_type
    field.options_json = options_json if options_json is not None else []
    field.label = label
    return field


def test_number_valid_returns_not_out_of_range():
    field = make_field("NUMBER")
    result = validate_field_value(field, "42.5")
    assert result["out_of_range"] is False


def test_number_non_numeric_raises():
    field = make_field("NUMBER")
    with pytest.raises(ValueError, match="numérico"):
        validate_field_value(field, "no-es-numero")


def test_number_out_of_range_detected():
    field = make_field("NUMBER", options_json={"min": 0, "max": 100})
    result = validate_field_value(field, "150")
    assert result["out_of_range"] is True


def test_boolean_invalid_raises():
    field = make_field("BOOLEAN")
    with pytest.raises(ValueError, match="verdadero o falso"):
        validate_field_value(field, "quizas")


def test_date_invalid_format_raises():
    field = make_field("DATE")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validate_field_value(field, "31-12-2026")


def test_select_invalid_option_raises():
    field = make_field("SELECT", options_json=["A", "B", "C"])
    with pytest.raises(ValueError, match="opciones"):
        validate_field_value(field, "D")


def test_meter_in_range():
    field = make_field("METER", options_json={"min": 10, "max": 200})
    result = validate_field_value(field, "50")
    assert result["out_of_range"] is False


def test_text_accepts_any_value():
    field = make_field("TEXT")
    result = validate_field_value(field, "cualquier texto libre")
    assert result == {}
