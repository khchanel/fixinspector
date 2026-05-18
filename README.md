# FIX Inspector

[![CI](https://github.com/khchanel/fixinspector/actions/workflows/ci.yml/badge.svg)](https://github.com/khchanel/fixinspector/actions/workflows/ci.yml)

Offline FIX message viewer and decoder for troubleshooting trade logs.

![Main UI](./docs/screenshots/main.png)

## Requirements

- Python 3.12+
- `PySide6` (Qt6)
- Supported platforms: Windows, macOS, and Linux

## Install from source

```sh
python -m pip install -e .
python -m fixinspector
```

## Install from PyPI

```sh
python -m pip install fixinspector
python -m fixinspector
```

The `fixinspector` command launches the GUI after installation.

## CLI

```sh
fixinspect decode sample.log --format text
fixinspect decode sample.log --format json
fixinspect index sample.log
```

The same CLI subcommands are available through the package module:

```sh
python -m fixinspector decode sample.log --format json
python -m fixinspector index sample.log
```

Custom QuickFIX-style XML dictionaries can be supplied with `--dict`.

## Development

If you use `uv`, the existing lockfile supports the same workflows:

```sh
uv sync --all-groups
uv run python -m fixinspector
uv run pytest -q
```
