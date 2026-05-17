from __future__ import annotations

from fixinspector.core.parser import decode_fix_message, parse_fix_messages

from tests.conftest import make_fix


def test_decodes_pipe_delimited_message_from_noisy_log() -> None:
    raw = make_fix([(35, "D"), (49, "CLIENT"), (56, "BROKER"), (34, "12"), (11, "ABC-1"), (54, "1")])
    messages = parse_fix_messages(f"2026-05-18 INFO inbound {raw}\n")

    assert len(messages) == 1
    message = messages[0]
    assert message.validation.is_valid
    assert message.summary.msg_type == "D"
    assert message.summary.msg_name == "NewOrderSingle"
    assert message.summary.sender == "CLIENT"
    assert message.summary.target == "BROKER"
    assert message.summary.cl_ord_id == "ABC-1"
    assert message.field_value(54) == "1"
    assert [field.enum_label for field in message.fields if field.tag == 54] == ["Buy"]


def test_decodes_angle_soh_delimited_message() -> None:
    raw = make_fix([(35, "0"), (49, "S"), (56, "T"), (34, "1")], delimiter="<SOH>")
    message = decode_fix_message(raw)

    assert message.validation.is_valid
    assert message.delimiter == "<SOH>"
    assert message.summary.msg_name == "Heartbeat"


def test_reports_body_length_and_checksum_errors() -> None:
    raw = make_fix([(35, "D"), (49, "S"), (56, "T")])
    parts = raw.split("|")
    parts[1] = "9=1"
    parts[-2] = "10=999"
    broken = "|".join(parts)

    message = decode_fix_message(broken)

    assert not message.validation.is_valid
    assert any("BodyLength mismatch" in error for error in message.validation.errors)
    assert any("CheckSum mismatch" in error for error in message.validation.errors)


def test_returns_truncated_message_with_validation_errors() -> None:
    messages = parse_fix_messages("prefix 8=FIX.4.2|9=20|35=D|49=S|")

    assert len(messages) == 1
    assert not messages[0].validation.is_valid
    assert any("Missing CheckSum" in error for error in messages[0].validation.errors)


def test_extracts_message_without_trailing_delimiter() -> None:
    raw = make_fix([(35, "0"), (49, "S"), (56, "T")]).rstrip("|")

    messages = parse_fix_messages(f"prefix {raw}\nnext line")

    assert len(messages) == 1
    assert messages[0].validation.is_valid
