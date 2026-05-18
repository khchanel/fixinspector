from __future__ import annotations

import sys
from collections.abc import Sequence

CLI_COMMANDS = {"decode", "index"}

HELP_TEXT = """FIX Inspector

Usage:
  python -m fixinspector              Launch the GUI
  python -m fixinspector decode ...   Decode FIX messages from a file or stdin
  python -m fixinspector index ...    Index FIX messages in a log file

Commands:
  decode    Decode FIX messages from a file or stdin
  index     Build an in-memory message index for a log file

Use `python -m fixinspector <command> --help` for command options.
"""


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(HELP_TEXT)
        return 0
    if args and args[0] in CLI_COMMANDS:
        from fixinspector.cli import main as cli_main

        return cli_main(args)
    if args:
        print(f"fixinspector: unknown command: {args[0]}", file=sys.stderr)
        print("Run `python -m fixinspector --help` for usage.", file=sys.stderr)
        return 2

    from fixinspector.gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
