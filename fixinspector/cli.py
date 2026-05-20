from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fixinspector import __version__
from fixinspector.core.dictionary import FixDictionary
from fixinspector.core.formatting import format_message_text, messages_to_json
from fixinspector.core.parser import parse_fix_messages
from fixinspector.indexing import IndexEntry, index_file


INDEX_COLUMNS = (
    "#",
    "Offset",
    "Bytes",
    "Time",
    "Type",
    "Name",
    "Seq",
    "Sender",
    "Target",
    "ID",
    "Summary",
    "Status",
)
RIGHT_ALIGNED_INDEX_COLUMNS = {0, 1, 2, 6}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fixinspect")
    parser.add_argument("--version", "--versoin", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    decode_parser = subparsers.add_parser("decode", help="Decode FIX messages from a file or stdin")
    decode_parser.add_argument("source", nargs="?", default="-", help="Path to log/FIX text, or '-' for stdin")
    decode_parser.add_argument("--dict", dest="dictionary_path", help="QuickFIX-style XML dictionary")
    decode_parser.add_argument("--format", choices=("text", "json"), default="text")
    decode_parser.add_argument("--limit", type=int, help="Maximum number of messages to decode")

    index_parser = subparsers.add_parser("index", help="Build an in-memory message index for a log file")
    index_parser.add_argument("source", help="Path to log/FIX text")
    index_parser.add_argument("--dict", dest="dictionary_path", help="QuickFIX-style XML dictionary")
    index_parser.add_argument("--limit", type=int, help="Maximum number of rows to print")

    args = parser.parse_args(argv)
    try:
        dictionary = _load_dictionary(args.dictionary_path)
        if args.command == "decode":
            return _decode(args.source, dictionary, args.format, args.limit)
        if args.command == "index":
            return _index(args.source, dictionary, args.limit)
        return 2
    except FileNotFoundError as exc:
        print(f"fixinspect: file not found: {exc.filename}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"fixinspect: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"fixinspect: {exc}", file=sys.stderr)
        return 1


def _decode(source: str, dictionary: FixDictionary, output_format: str, limit: int | None) -> int:
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="latin1")
    messages = parse_fix_messages(text, dictionary, limit=limit)
    if output_format == "json":
        print(messages_to_json(messages))
    else:
        for index, message in enumerate(messages, start=1):
            if index > 1:
                print("\n" + "=" * 80 + "\n")
            print(format_message_text(message))
    return 0 if messages else 1


def _index(source: str, dictionary: FixDictionary, limit: int | None) -> int:
    rows = index_file(source, dictionary)[:limit]
    if rows:
        print(_format_index_table(rows))
    return 0


def _format_index_table(entries: list[IndexEntry]) -> str:
    rows = [_index_row(entry) for entry in entries]
    widths = [
        max(len(INDEX_COLUMNS[index]), *(len(row[index]) for row in rows))
        for index in range(len(INDEX_COLUMNS))
    ]

    lines = [
        _format_index_table_row(INDEX_COLUMNS, widths),
        _format_index_table_row(tuple("-" * width for width in widths), widths),
    ]
    lines.extend(_format_index_table_row(row, widths) for row in rows)
    return "\n".join(lines)


def _index_row(entry: IndexEntry) -> tuple[str, ...]:
    summary = entry.summary
    identifier = summary.cl_ord_id or summary.order_id or summary.exec_id or ""
    return (
        str(entry.row + 1),
        str(entry.offset),
        str(entry.length),
        summary.sending_time or "",
        summary.msg_type or "",
        summary.msg_name or "",
        summary.seq_num or "",
        summary.sender or "",
        summary.target or "",
        identifier,
        summary.trade_summary,
        summary.validation_status,
    )


def _format_index_table_row(values: tuple[str, ...], widths: list[int]) -> str:
    cells = []
    for index, value in enumerate(values):
        formatter = str.rjust if index in RIGHT_ALIGNED_INDEX_COLUMNS else str.ljust
        cells.append(formatter(value, widths[index]))
    return "  ".join(cells).rstrip()


def _load_dictionary(path: str | None) -> FixDictionary:
    if path:
        try:
            return FixDictionary.from_xml(path)
        except FileNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001 - CLI should report dictionary load failures cleanly.
            raise ValueError(f"could not load dictionary {path}: {exc}") from exc
    return FixDictionary.common()


if __name__ == "__main__":
    raise SystemExit(main())
