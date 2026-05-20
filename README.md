# FIX Inspector

[![CI](https://github.com/khchanel/fixinspector/actions/workflows/ci.yml/badge.svg)](https://github.com/khchanel/fixinspector/actions/workflows/ci.yml)

Offline FIX message viewer and decoder for troubleshooting trade logs.
Supports quickfix XML dictionaries.

![FIX Inspector main window](https://raw.githubusercontent.com/khchanel/fixinspector/master/docs/screenshots/main.png)

## Install

FIX Inspector requires Python 3.12+.

```sh
python -m pip install fixinspector
```

For local development:

```sh
python -m pip install -e .
```

## Run

Launch the GUI:

```sh
python -m fixinspector
fixinspector
```

Use the CLI:

```sh
fixinspect decode sample.log --format text
fixinspect decode sample.log --format json
fixinspect index sample.log
```

The same CLI commands are available through the package module:

```sh
python -m fixinspector decode sample.log --format json
python -m fixinspector index sample.log
```

Pass `--dict <path>` to use a QuickFIX-style XML dictionary.

## Development

```sh
pytest -q
```

With `uv`:

```sh
uv sync --all-groups
uv run --no-sync pytest -q
uv run python -m fixinspector
```
