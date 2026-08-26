import json
from datetime import datetime

from .models import ChecklistField


def validate_field_value(field, value):
    """
    Validates `value` against the field type rules.
    Returns a dict with extra metadata (e.g. out_of_range for NUMBER/METER).
    Raises ValueError for invalid/unparseable values.
    """
    ft = field.field_type
    result = {}

    if ft == ChecklistField.FieldType.BOOLEAN:
        if value.lower() not in ("true", "false", "1", "0", "yes", "no", "si"):
            raise ValueError(f"El campo '{field.label}' debe ser verdadero o falso (true/false).")

    elif ft in (ChecklistField.FieldType.NUMBER, ChecklistField.FieldType.METER):
        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"El campo '{field.label}' debe ser un valor numérico.")
        opts = field.options_json if isinstance(field.options_json, dict) else {}
        out_of_range = False
        if "min" in opts and num < opts["min"]:
            out_of_range = True
        if "max" in opts and num > opts["max"]:
            out_of_range = True
        result["out_of_range"] = out_of_range

    elif ft == ChecklistField.FieldType.SELECT:
        options = field.options_json if isinstance(field.options_json, list) else []
        if options and value not in options:
            raise ValueError(
                f"El campo '{field.label}' debe ser una de las opciones: {', '.join(map(str, options))}."
            )

    elif ft == ChecklistField.FieldType.MULTI_SELECT:
        options = field.options_json if isinstance(field.options_json, list) else []
        if options and value:
            try:
                selected = json.loads(value) if isinstance(value, str) else value
                if isinstance(selected, list):
                    invalid = [v for v in selected if v not in options]
                    if invalid:
                        raise ValueError(
                            f"Opciones inválidas para '{field.label}': {', '.join(map(str, invalid))}."
                        )
            except json.JSONDecodeError:
                pass

    elif ft == ChecklistField.FieldType.DATE:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError(f"El campo '{field.label}' debe ser una fecha válida (YYYY-MM-DD).")

    elif ft == ChecklistField.FieldType.DATETIME:
        try:
            datetime.fromisoformat(value)
        except (ValueError, TypeError, AttributeError):
            raise ValueError(f"El campo '{field.label}' debe ser una fecha-hora válida (ISO 8601).")

    elif ft == ChecklistField.FieldType.GPS:
        try:
            parts = value.split(",")
            if len(parts) != 2:
                raise ValueError
            float(parts[0].strip())
            float(parts[1].strip())
        except (ValueError, TypeError, AttributeError):
            raise ValueError(
                f"El campo '{field.label}' debe ser coordenadas GPS válidas (lat,lon)."
            )

    # TEXT, TEXTAREA, PHOTO, SIGNATURE: accept any value.

    return result
