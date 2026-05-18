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


def test_summarizes_trade_quantity_symbol_and_prices() -> None:
    raw = make_fix(
        [(35, "8"), (54, "1"), (32, "12345"), (55, "TESTSYM"), (31, "45.67"), (6, "45.89")]
    )

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Buy 12,345 TESTSYM @ 45.67 avg px 45.89"


def test_summarizes_partial_trade_information() -> None:
    raw = make_fix([(35, "8"), (54, "2"), (55, "TESTSYM"), (6, "45.89")])

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Sell TESTSYM avg px 45.89"


def test_summarizes_order_quantity_when_last_quantity_is_absent() -> None:
    raw = make_fix([(35, "D"), (54, "1"), (38, "12345"), (55, "TESTSYM")])

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Buy 12,345 TESTSYM"


def test_summarizes_order_quantity_when_last_quantity_is_zero() -> None:
    raw = make_fix([(35, "8"), (54, "1"), (32, "0"), (38, "12345"), (55, "TESTSYM"), (31, "0"), (6, "0")])

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Buy 12,345 TESTSYM"


def test_summarizes_order_price_when_last_price_is_zero() -> None:
    raw = make_fix([(35, "D"), (54, "1"), (38, "12345"), (55, "TESTSYM"), (31, "0"), (44, "45.67")])

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Buy 12,345 TESTSYM @ 45.67"


def test_reject_summary_uses_text() -> None:
    raw = make_fix([(35, "3"), (58, "Required tag missing"), (54, "1"), (32, "12345")])

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Required tag missing"


def test_execution_report_reject_summary_uses_text() -> None:
    raw = make_fix(
        [(35, "8"), (150, "8"), (39, "8"), (58, "Order rejected"), (54, "1"), (32, "12345")]
    )

    message = decode_fix_message(raw)

    assert message.summary.trade_summary == "Order rejected"
