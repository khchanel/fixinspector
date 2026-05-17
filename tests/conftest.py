from __future__ import annotations

SOH = "\x01"


def make_fix(fields: list[tuple[int, str]], delimiter: str = "|") -> str:
    body = SOH.join(f"{tag}={value}" for tag, value in fields) + SOH
    header = f"8=FIX.4.2{SOH}9={len(body.encode('latin1'))}{SOH}"
    payload = header + body
    message = payload + f"10={sum(payload.encode('latin1')) % 256:03d}{SOH}"
    if delimiter == "<SOH>":
        return message.replace(SOH, "<SOH>")
    return message.replace(SOH, delimiter)
