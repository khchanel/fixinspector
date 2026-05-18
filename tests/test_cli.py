from __future__ import annotations

import json
from pathlib import Path

from fixinspector import __version__
from fixinspector.cli import main

from tests.conftest import make_fix


def test_cli_decode_json(tmp_path: Path, capsys) -> None:
    path = tmp_path / "message.fix"
    path.write_text(make_fix([(35, "D"), (49, "S"), (56, "T"), (11, "ABC")]), encoding="latin1")

    exit_code = main(["decode", str(path), "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["summary"]["msg_name"] == "NewOrderSingle"
    assert payload[0]["summary"]["cl_ord_id"] == "ABC"


def test_cli_index_text(tmp_path: Path, capsys) -> None:
    path = tmp_path / "message.fix"
    path.write_text(make_fix([(35, "0"), (49, "S"), (56, "T")]), encoding="latin1")

    exit_code = main(["index", str(path)])

    assert exit_code == 0
    assert "Heartbeat" in capsys.readouterr().out


def test_cli_prints_version(capsys) -> None:
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0

    assert capsys.readouterr().out.strip() == f"fixinspect {__version__}"


def test_cli_accepts_requested_version_typo_alias(capsys) -> None:
    try:
        main(["--versoin"])
    except SystemExit as exc:
        assert exc.code == 0

    assert capsys.readouterr().out.strip() == f"fixinspect {__version__}"
