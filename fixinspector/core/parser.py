from __future__ import annotations

import re

from fixinspector.core.dictionary import FixDictionary
from fixinspector.core.models import DecodedField, DecodedMessage, MessageSummary, ValidationResult

SOH = "\x01"
CHECKSUM_RE = re.compile(r"(?:\x01|\||<SOH>)10=\d{3}(?:\x01|\||<SOH>|(?=\s)|$)")


def parse_fix_messages(text: str, dictionary: FixDictionary | None = None, limit: int | None = None) -> list[DecodedMessage]:
    dictionary = dictionary or FixDictionary.common()
    messages: list[DecodedMessage] = []
    for raw in extract_fix_messages(text):
        messages.append(decode_fix_message(raw, dictionary))
        if limit is not None and len(messages) >= limit:
            break
    return messages


def extract_fix_messages(text: str) -> list[str]:
    messages: list[str] = []
    cursor = 0
    while True:
        start = text.find("8=FIX", cursor)
        if start < 0:
            return messages
        match = CHECKSUM_RE.search(text, start)
        if match is None:
            tail = text[start:].strip()
            if tail:
                messages.append(tail)
            return messages
        messages.append(text[start:match.end()])
        cursor = match.end()


def decode_fix_message(raw: str, dictionary: FixDictionary | None = None) -> DecodedMessage:
    dictionary = dictionary or FixDictionary.common()
    delimiter = detect_delimiter(raw)
    normalized = normalize_delimiters(raw, delimiter)
    pairs = _split_pairs(normalized)
    validation = _validate(normalized, pairs)
    fields = tuple(_decode_fields(pairs, dictionary))
    summary = _summary(fields, validation, dictionary)
    return DecodedMessage(
        raw=raw,
        normalized=normalized,
        delimiter=delimiter,
        fields=fields,
        validation=validation,
        summary=summary,
    )


def detect_delimiter(text: str) -> str:
    if SOH in text:
        return SOH
    if "<SOH>" in text:
        return "<SOH>"
    if "|" in text:
        return "|"
    return SOH


def normalize_delimiters(text: str, delimiter: str | None = None) -> str:
    delimiter = delimiter or detect_delimiter(text)
    if delimiter == "<SOH>":
        return text.replace("<SOH>", SOH)
    if delimiter == "|":
        return text.replace("|", SOH)
    return text


def printable_message(message: DecodedMessage, delimiter: str = "|") -> str:
    return message.normalized.replace(SOH, delimiter)


def _split_pairs(normalized: str) -> list[tuple[int, str, str]]:
    pairs: list[tuple[int, str, str]] = []
    for position, piece in enumerate(part for part in normalized.split(SOH) if part):
        tag_text, separator, value = piece.partition("=")
        if not separator or not tag_text.isdigit():
            continue
        pairs.append((int(tag_text), value, piece))
    return pairs


def _decode_fields(pairs: list[tuple[int, str, str]], dictionary: FixDictionary) -> list[DecodedField]:
    decoded: list[DecodedField] = []
    group_stack: list[tuple[str, int]] = []
    for position, (tag, value, _piece) in enumerate(pairs):
        definition = dictionary.field(tag)
        if definition.type == "NUMINGROUP":
            group_stack = [(definition.name, max(_safe_int(value), 0))]
            group_path = tuple(name for name, _ in group_stack)
        else:
            group_path = tuple(name for name, remaining in group_stack if remaining > 0)
            if group_stack:
                name, remaining = group_stack[-1]
                group_stack[-1] = (name, max(remaining - 1, 0))
        decoded.append(
            DecodedField(
                tag=tag,
                value=value,
                name=definition.name,
                type=definition.type,
                enum_label=dictionary.enum_label(tag, value),
                position=position,
                group_path=group_path,
            )
        )
    return decoded


def _validate(normalized: str, pairs: list[tuple[int, str, str]]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    values = {tag: value for tag, value, _piece in pairs}

    if not pairs:
        return ValidationResult(False, ("No FIX tag/value pairs found",), ())
    if pairs[0][0] != 8:
        errors.append("Message does not start with BeginString tag 8")
    if 9 not in values:
        errors.append("Missing BodyLength tag 9")
    if 35 not in values:
        errors.append("Missing MsgType tag 35")
    if 10 not in values:
        errors.append("Missing CheckSum tag 10")

    body_length = _calculate_body_length(normalized)
    if 9 in values:
        expected = _safe_int(values[9], -1)
        if expected < 0:
            errors.append(f"BodyLength is not numeric: {values[9]}")
        elif body_length is None:
            warnings.append("Could not calculate BodyLength from malformed message")
        elif expected != body_length:
            errors.append(f"BodyLength mismatch: expected {expected}, calculated {body_length}")

    checksum = _calculate_checksum(normalized)
    if 10 in values:
        expected_checksum = values[10]
        if not re.fullmatch(r"\d{3}", expected_checksum):
            errors.append(f"CheckSum is not a three digit value: {expected_checksum}")
        elif checksum is None:
            warnings.append("Could not calculate CheckSum from malformed message")
        elif expected_checksum != checksum:
            errors.append(f"CheckSum mismatch: expected {expected_checksum}, calculated {checksum}")

    return ValidationResult(not errors, tuple(errors), tuple(warnings))


def _calculate_body_length(normalized: str) -> int | None:
    body_start_marker = SOH + "9="
    body_start = normalized.find(body_start_marker)
    if body_start < 0 and normalized.startswith("8="):
        first_delimiter = normalized.find(SOH)
        body_length_delimiter = normalized.find(SOH, first_delimiter + 1)
    else:
        body_length_delimiter = normalized.find(SOH, body_start + 1)
    if body_length_delimiter < 0:
        return None
    body_start_index = body_length_delimiter + 1
    checksum_index = normalized.rfind(SOH + "10=")
    if checksum_index < 0:
        return None
    return len(normalized[body_start_index : checksum_index + 1].encode("latin1", errors="replace"))


def _calculate_checksum(normalized: str) -> str | None:
    checksum_index = normalized.rfind(SOH + "10=")
    if checksum_index < 0:
        return None
    payload = normalized[: checksum_index + 1].encode("latin1", errors="replace")
    return f"{sum(payload) % 256:03d}"


def _summary(fields: tuple[DecodedField, ...], validation: ValidationResult, dictionary: FixDictionary) -> MessageSummary:
    values = {field.tag: field.value for field in fields}
    msg_type = values.get(35)
    status = "OK" if validation.is_valid else "ERROR"
    if validation.warnings and validation.is_valid:
        status = "WARN"
    return MessageSummary(
        begin_string=values.get(8),
        msg_type=msg_type,
        msg_name=dictionary.message_name(msg_type),
        seq_num=values.get(34),
        sender=values.get(49),
        target=values.get(56),
        sending_time=values.get(52),
        cl_ord_id=values.get(11),
        order_id=values.get(37),
        exec_id=values.get(17),
        trade_summary=_trade_summary(fields, values, dictionary),
        validation_status=status,
    )


def _trade_summary(fields: tuple[DecodedField, ...], values: dict[int, str], dictionary: FixDictionary) -> str:
    text = values.get(58)
    if text and _is_reject(values):
        return text

    side = _side_label(values, dictionary)
    qty = _format_quantity(_first_non_zero(values.get(32), values.get(38)))
    symbol = values.get(55)
    last_px = _first_non_zero(values.get(31), values.get(44))
    avg_px = _first_non_zero(values.get(6))

    head = " ".join(part for part in (side, qty, symbol) if part)
    parts = [head] if head else []
    if last_px:
        parts.append(f"@ {last_px}")
    if avg_px:
        parts.append(f"avg px {avg_px}")
    return " ".join(parts)


def _is_reject(values: dict[int, str]) -> bool:
    msg_type = values.get(35)
    return msg_type in {"3", "9", "j"} or (
        msg_type == "8" and (values.get(150) == "8" or values.get(39) == "8")
    )


def _side_label(values: dict[int, str], dictionary: FixDictionary) -> str | None:
    side = values.get(54)
    return dictionary.enum_label(54, side) or side if side else None


def _first_non_zero(*values: str | None) -> str | None:
    for value in values:
        if value is not None and not _is_numeric_zero(value):
            return value
    return None


def _is_numeric_zero(value: str) -> bool:
    try:
        return float(value) == 0
    except ValueError:
        return False


def _format_quantity(value: str | None) -> str | None:
    if value is None:
        return None
    sign = ""
    rest = value
    if rest.startswith(("+", "-")):
        sign = rest[0]
        rest = rest[1:]
    whole, dot, fractional = rest.partition(".")
    if not whole.isdigit() or (dot and not fractional.isdigit()):
        return value
    formatted = f"{int(whole):,}"
    if dot:
        formatted = f"{formatted}.{fractional}"
    return f"{sign}{formatted}"


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except ValueError:
        return default
