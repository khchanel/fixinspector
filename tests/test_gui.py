from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QHeaderView

    from fixinspector.gui import MainWindow, MessageTableModel, refit_message_columns_after_load
except ImportError as exc:
    pytest.skip(f"PySide6 is not available for GUI tests: {exc}", allow_module_level=True)

from fixinspector.core.models import MessageSummary
from fixinspector.indexing import IndexEntry


def make_summary(
    msg_type: str | None = "D",
    msg_name: str | None = "NewOrderSingle",
    sender: str | None = "CLIENT",
    target: str | None = "BROKER",
    trade_summary: str = "",
) -> MessageSummary:
    return MessageSummary(
        begin_string="FIX.4.2",
        msg_type=msg_type,
        msg_name=msg_name,
        seq_num="1",
        sender=sender,
        target=target,
        sending_time="20260518-01:02:03.000",
        cl_ord_id="ABC-1",
        order_id=None,
        exec_id=None,
        trade_summary=trade_summary,
        validation_status="OK",
    )


def make_entry(row: int, summary: MessageSummary) -> IndexEntry:
    return IndexEntry(row=row, offset=0, length=0, summary=summary)


def brush_color_name(model: MessageTableModel, row: int, column: int, role: Qt.ItemDataRole) -> str:
    brush = model.data(model.index(row, column), role)
    return brush.color().name()


def test_message_table_columns_are_unchanged_except_type_coloring() -> None:
    assert MessageTableModel.COLUMNS == (
        "#",
        "Time",
        "Type",
        "Name",
        "Seq",
        "Sender",
        "Target",
        "ClOrdID",
        "Summary",
        "Status",
    )


def test_message_type_and_name_share_stable_colors() -> None:
    model = MessageTableModel()
    model.set_entries(
        [
            make_entry(0, make_summary(msg_type="D", msg_name="NewOrderSingle")),
            make_entry(1, make_summary(msg_type="D", msg_name="NewOrderSingle")),
            make_entry(2, make_summary(msg_type="8", msg_name="ExecutionReport")),
        ]
    )

    first_type_background = brush_color_name(model, 0, 2, Qt.BackgroundRole)
    first_name_background = brush_color_name(model, 0, 3, Qt.BackgroundRole)
    second_type_background = brush_color_name(model, 1, 2, Qt.BackgroundRole)
    execution_type_background = brush_color_name(model, 2, 2, Qt.BackgroundRole)

    assert first_type_background == first_name_background
    assert first_type_background == second_type_background
    assert first_type_background != execution_type_background

    assert brush_color_name(model, 0, 2, Qt.ForegroundRole) == brush_color_name(model, 0, 3, Qt.ForegroundRole)
    assert model.data(model.index(0, 1), Qt.BackgroundRole) is None


def test_message_table_columns_are_refit_after_load() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        header = window.message_table.horizontalHeader()
        window.message_model.set_entries(
            [
                make_entry(0, make_summary(sender="CLIENT", target="BROKER")),
                make_entry(1, make_summary(sender="LONG-SENDER-COMP-ID", target="LONG-TARGET-COMP-ID")),
            ]
        )
        refit_message_columns_after_load(window.message_table)

        summary_column = MessageTableModel.COLUMNS.index("Summary")
        assert header.sectionResizeMode(summary_column) == QHeaderView.Stretch
        for column in range(len(MessageTableModel.COLUMNS)):
            if column != summary_column:
                assert header.sectionResizeMode(column) == QHeaderView.Interactive
    finally:
        window.close()
        app.processEvents()


def test_decode_paste_does_not_require_summary_column_attribute() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert not hasattr(window, "message_summary_column")
        window.paste_box.setPlainText("not a fix message")
        window._decode_paste()
        assert window.message_model.rowCount() == 0
    finally:
        window.close()
        app.processEvents()
