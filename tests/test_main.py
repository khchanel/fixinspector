from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from fixinspector import __version__
from fixinspector import __main__

from tests.conftest import make_fix


def test_module_help(capsys) -> None:
    exit_code = __main__.main(["--help"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Launch the GUI" in output
    assert "decode" in output
    assert "index" in output


def test_module_prints_version(capsys) -> None:
    exit_code = __main__.main(["--version"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == f"fixinspector {__version__}"


def test_module_launches_gui_by_default(monkeypatch) -> None:
    gui_module = types.ModuleType("fixinspector.gui")
    gui_module.main = lambda: 17
    monkeypatch.setitem(sys.modules, "fixinspector.gui", gui_module)

    assert __main__.main([]) == 17


def test_module_delegates_decode_to_cli(tmp_path: Path, capsys) -> None:
    path = tmp_path / "message.fix"
    path.write_text(make_fix([(35, "D"), (49, "S"), (56, "T"), (11, "ABC")]), encoding="latin1")

    exit_code = __main__.main(["decode", str(path), "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["summary"]["msg_name"] == "NewOrderSingle"


def test_module_delegates_index_to_cli(tmp_path: Path, capsys) -> None:
    path = tmp_path / "message.fix"
    path.write_text(make_fix([(35, "0"), (49, "S"), (56, "T")]), encoding="latin1")

    exit_code = __main__.main(["index", str(path)])

    assert exit_code == 0
    assert "Heartbeat" in capsys.readouterr().out


def test_module_rejects_unknown_command(capsys) -> None:
    exit_code = __main__.main(["bogus"])

    assert exit_code == 2
    assert "unknown command: bogus" in capsys.readouterr().err
