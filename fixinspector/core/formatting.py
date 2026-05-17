from __future__ import annotations

import json

from fixinspector.core.models import DecodedMessage
from fixinspector.core.parser import printable_message


def format_message_text(message: DecodedMessage) -> str:
    summary = message.summary
    lines = [
        f"Message: {summary.msg_name or summary.msg_type or 'Unknown'}",
        f"Status: {summary.validation_status}",
        f"Raw: {printable_message(message)}",
        "",
        "Fields:",
    ]
    for field in message.fields:
        value = field.value
        if field.enum_label:
            value = f"{value} ({field.enum_label})"
        group = f" [{'/'.join(field.group_path)}]" if field.group_path else ""
        lines.append(f"  {field.tag:<5} {field.name:<28} {value}{group}")
    if message.validation.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"  - {error}" for error in message.validation.errors)
    if message.validation.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"  - {warning}" for warning in message.validation.warnings)
    return "\n".join(lines)


def messages_to_json(messages: list[DecodedMessage]) -> str:
    payload = []
    for message in messages:
        payload.append(
            {
                "summary": message.summary.__dict__,
                "validation": {
                    "is_valid": message.validation.is_valid,
                    "errors": list(message.validation.errors),
                    "warnings": list(message.validation.warnings),
                },
                "fields": [
                    {
                        "tag": field.tag,
                        "name": field.name,
                        "value": field.value,
                        "type": field.type,
                        "enum_label": field.enum_label,
                        "group_path": list(field.group_path),
                    }
                    for field in message.fields
                ],
            }
        )
    return json.dumps(payload, indent=2)
