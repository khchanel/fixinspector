from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fixinspector.core.dictionary import FixDictionary
from fixinspector.core.formatting import format_message_text, messages_to_json
from fixinspector.core.parser import parse_fix_messages
from fixinspector.indexing import index_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fixinspect")
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
    rows = index_file(source, dictionary)
    for entry in rows[:limit]:
        summary = entry.summary
        print(
            "\t".join(
                [
                    str(entry.row),
                    str(entry.offset),
                    str(entry.length),
                    summary.sending_time or "",
                    summary.msg_type or "",
                    summary.msg_name or "",
                    summary.seq_num or "",
                    summary.sender or "",
                    summary.target or "",
                    summary.validation_status,
                ]
            )
        )
    return 0


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
