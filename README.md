# FIX Inspector

Offline FIX message viewer and decoder for troubleshooting trade logs.

## Run

```powershell
uv run python main.py
```

## CLI

```powershell
uv run python -m fixinspector.cli decode .\sample.log --format text
uv run python -m fixinspector.cli decode .\sample.log --format json
uv run python -m fixinspector.cli index .\sample.log
```

Custom QuickFIX-style XML dictionaries can be supplied with `--dict`.
