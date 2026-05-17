from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldDefinition:
    number: int
    name: str
    type: str = "STRING"
    enums: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GroupDefinition:
    name: str
    number: int
    fields: tuple[int, ...] = ()
    groups: dict[int, "GroupDefinition"] = field(default_factory=dict)


@dataclass(frozen=True)
class MessageDefinition:
    msgtype: str
    name: str
    category: str = ""
    fields: tuple[int, ...] = ()
    groups: dict[int, GroupDefinition] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecodedField:
    tag: int
    value: str
    name: str
    position: int
    type: str = "STRING"
    enum_label: str | None = None
    group_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class MessageSummary:
    begin_string: str | None
    msg_type: str | None
    msg_name: str | None
    seq_num: str | None
    sender: str | None
    target: str | None
    sending_time: str | None
    cl_ord_id: str | None
    order_id: str | None
    exec_id: str | None
    validation_status: str


@dataclass(frozen=True)
class DecodedMessage:
    raw: str
    normalized: str
    delimiter: str
    fields: tuple[DecodedField, ...]
    validation: ValidationResult
    summary: MessageSummary

    def field_value(self, tag: int) -> str | None:
        for item in self.fields:
            if item.tag == tag:
                return item.value
        return None
