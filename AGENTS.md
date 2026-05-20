# AGENTS: Fix Inspector

Minimal context for coding agents working in this repository.

## Commands

- Launch GUI: `python -m fixinspector` or `python main.py`.
- Decode FIX text: `python -m fixinspector decode <path> --format text|json`.
- Index a log file: `python -m fixinspector index <path> [--limit N]`.
- Installed scripts: `fixinspector` launches the GUI; `fixinspect` runs the CLI.
- Run tests: `pytest -q` or `uv run --no-sync pytest -q`.

The package requires Python 3.12+. PySide6 is required for the GUI; core parsing, indexing, and CLI logic should stay usable without importing GUI code.

## Architecture

- `main.py` is a tiny shim to `fixinspector.__main__.main()`.
- `fixinspector/__main__.py` dispatches module usage: no args launches the GUI, `decode` and `index` delegate to `fixinspector.cli`.
- `fixinspector/cli.py` owns CLI argument parsing, exit-code behavior, decode formatting, and the aligned index table.
- `fixinspector/core/parser.py` extracts and decodes FIX messages, detects delimiters, validates BodyLength/CheckSum, and builds `MessageSummary`.
- `fixinspector/core/dictionary.py` contains the built-in common FIX dictionary and merges QuickFIX-style XML dictionaries.
- `fixinspector/core/formatting.py` formats decoded messages as text or JSON.
- `fixinspector/indexing.py` scans large files in chunks and yields byte-offset `IndexEntry` rows.
- `fixinspector/gui.py` is the Qt UI. `IndexWorker` runs indexing on a `QThread` and updates `MessageTableModel` / `FieldTableModel`.

## Conventions

- Preserve byte offsets in indexing. Read files as binary, decode chunks with latin1, and keep `IndexEntry.offset` / `length` byte-accurate.
- `IndexEntry.row` is zero-based internally. User-facing CLI and GUI output display rows as one-based.
- Supported delimiters are SOH (`\x01`), `<SOH>`, and `|`. Use `detect_delimiter()` and `normalize_delimiters()` instead of custom delimiter handling.
- Message boundaries are found with `CHECKSUM_RE`; BodyLength and CheckSum behavior is covered by `tests/test_parser.py`.
- Use `FixDictionary.common()` when no dictionary is supplied. XML dictionaries should keep the existing merge behavior so built-in names/enums remain available.
- Models in `fixinspector/core/models.py` are frozen dataclasses. Create new instances instead of mutating them.
- CLI errors are mapped to user-facing messages and exit code `1`; unknown module commands return `2`; `decode` returns `1` when no messages are decoded; `index` returns `0`.
- GUI work must not block the main thread. Keep the `IndexWorker` signals compatible: `finished(list, str)`, `failed(str)`, and `progress(int, int)`.

## Tests

- Parser behavior: `tests/test_parser.py`.
- Dictionary XML merge/name/enum behavior: `tests/test_dictionary.py`.
- Byte-accurate indexing and `read_indexed_message`: `tests/test_indexing.py`.
- CLI output and exit behavior: `tests/test_cli.py`.
- Module dispatch: `tests/test_main.py`.
- Qt models and GUI helpers: `tests/test_gui.py`.

When changing behavior, add or update a focused test. `tests/conftest.py::make_fix` is the preferred helper for valid FIX fixtures.
