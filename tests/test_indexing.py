from __future__ import annotations

from pathlib import Path

from fixinspector.indexing import index_file, read_indexed_message

from tests.conftest import make_fix


def test_indexes_noisy_file_and_reads_selected_message(tmp_path: Path) -> None:
    first = make_fix([(35, "0"), (49, "S"), (56, "T"), (34, "1")])
    second = make_fix(
        [(35, "D"), (49, "S"), (56, "T"), (34, "2"), (11, "ORDER-2"), (54, "1"), (32, "12345"), (55, "TESTSYM")]
    )
    path = tmp_path / "session.log"
    path.write_text(f"noise before {first}\nother log text {second}\n", encoding="latin1")

    entries = index_file(path, chunk_size=16)

    assert len(entries) == 2
    assert entries[0].summary.msg_name == "Heartbeat"
    assert entries[1].summary.cl_ord_id == "ORDER-2"
    assert entries[1].summary.trade_summary == "Buy 12,345 TESTSYM"
    message = read_indexed_message(path, entries[1])
    assert message.summary.msg_name == "NewOrderSingle"
    assert message.field_value(11) == "ORDER-2"
