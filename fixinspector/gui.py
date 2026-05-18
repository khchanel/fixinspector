from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from fixinspector.core.dictionary import FixDictionary
from fixinspector.core.formatting import format_message_text
from fixinspector.core.models import DecodedField, DecodedMessage
from fixinspector.core.parser import parse_fix_messages, printable_message
from fixinspector.indexing import IndexEntry, index_file, read_indexed_message


def app_icon() -> QIcon:
    """Load application icon from resources with fallback support."""
    try:
        # Try to load SVG icon from package resources
        icon_path = resources.files("fixinspector.assets").joinpath("app-icon.svg")
        icon = QIcon(str(icon_path))
        # Verify icon loaded successfully on Windows by checking availableSizes
        if not icon.availableSizes():
            # SVG failed to load on Windows, try PNG fallback
            icon_png = resources.files("fixinspector.assets").joinpath("app-icon.png")
            icon = QIcon(str(icon_png))
        return icon
    except Exception:
        # Fallback: return empty icon if resources fail
        return QIcon()


class MessageTableModel(QAbstractTableModel):
    COLUMNS = ("#", "Time", "Type", "Name", "Seq", "Sender", "Target", "ClOrdID", "Status")

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[IndexEntry] = []

    def set_entries(self, entries: list[IndexEntry]) -> None:
        self.beginResetModel()
        self.entries = entries
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        entry = self.entries[index.row()]
        summary = entry.summary
        values = (
            entry.row + 1,
            summary.sending_time or "",
            summary.msg_type or "",
            summary.msg_name or "",
            summary.seq_num or "",
            summary.sender or "",
            summary.target or "",
            summary.cl_ord_id or summary.order_id or summary.exec_id or "",
            summary.validation_status,
        )
        return values[index.column()]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return None


class FieldTableModel(QAbstractTableModel):
    COLUMNS = ("#", "Tag", "Name", "Value", "Enum", "Type", "Group")

    def __init__(self) -> None:
        super().__init__()
        self.fields: tuple[DecodedField, ...] = ()

    def set_message(self, message: DecodedMessage | None) -> None:
        self.beginResetModel()
        self.fields = message.fields if message else ()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.fields)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        field = self.fields[index.row()]
        values = (
            field.position + 1,
            field.tag,
            field.name,
            field.value,
            field.enum_label or "",
            field.type,
            " / ".join(field.group_path),
        )
        return values[index.column()]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section]
        return None


class IndexWorker(QObject):
    finished = Signal(list, str)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, path: Path, dictionary: FixDictionary) -> None:
        super().__init__()
        self.path = path
        self.dictionary = dictionary
        self.cancelled = False

    def run(self) -> None:
        try:
            entries = index_file(
                self.path,
                self.dictionary,
                progress=lambda done, total: self.progress.emit(done, total or 0),
                should_cancel=lambda: self.cancelled,
            )
            self.finished.emit(entries, str(self.path))
        except Exception as exc:  # noqa: BLE001 - GUI boundary needs a user-facing error.
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.cancelled = True


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FIX Inspector")
        self.setWindowIcon(app_icon())
        self.resize(1200, 800)
        self.setAcceptDrops(True)
        self.dictionary = FixDictionary.common()
        self.current_file: Path | None = None
        self.message_model = MessageTableModel()
        self.field_model = FieldTableModel()
        self.pasted_messages: list[DecodedMessage] = []
        self.worker: IndexWorker | None = None
        self.worker_thread: QThread | None = None

        self.message_table = QTableView()
        self.message_table.setModel(self.message_model)
        self.message_table.setSelectionBehavior(QTableView.SelectRows)
        self.message_table.setSelectionMode(QTableView.SingleSelection)
        self.message_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.message_table.horizontalHeader().setStretchLastSection(True)
        self.message_table.selectionModel().selectionChanged.connect(self._select_message)

        self.field_table = QTableView()
        self.field_table.setModel(self.field_model)
        self.field_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.field_table.horizontalHeader().setStretchLastSection(True)

        self.raw_view = QPlainTextEdit()
        self.raw_view.setReadOnly(True)

        self.paste_box = QPlainTextEdit()
        self.paste_box.setPlaceholderText("Paste FIX messages or log excerpts here")
        decode_button = QPushButton("Decode Paste")
        decode_button.clicked.connect(self._decode_paste)
        self.shortcut = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_Return), self.paste_box)
        self.shortcut.activated.connect(self._decode_paste)
        paste_panel = QWidget()
        paste_layout = QVBoxLayout(paste_panel)
        paste_layout.addWidget(self.paste_box)
        paste_layout.addWidget(decode_button)

        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.field_table)
        right_splitter.addWidget(self.raw_view)
        right_splitter.setSizes([500, 250])

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.message_table)
        splitter.addWidget(right_splitter)
        splitter.setSizes([600, 600])

        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Filter visible rows by MsgType, name, seq, sender, target, or order id")
        self.filter_box.textChanged.connect(self._filter_rows)
        self.status_label = QLabel("Ready")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(paste_panel)
        layout.addWidget(self.filter_box)
        layout.addWidget(splitter, 1)
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label, 1)
        layout.addLayout(status_row)
        self.setCentralWidget(central)
        self._build_toolbar()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            self._open_file(Path(urls[0].toLocalFile()))

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        open_action = QAction("Open Log", self)
        open_action.triggered.connect(self._choose_file)
        toolbar.addAction(open_action)

        dict_action = QAction("Load Dictionary", self)
        dict_action.triggered.connect(self._choose_dictionary)
        toolbar.addAction(dict_action)

        cancel_action = QAction("Cancel Index", self)
        cancel_action.triggered.connect(self._cancel_index)
        toolbar.addAction(cancel_action)

    def _choose_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open FIX log")
        if file_name:
            self._open_file(Path(file_name))

    def _choose_dictionary(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open QuickFIX XML dictionary", filter="XML files (*.xml);;All files (*)")
        if not file_name:
            return
        try:
            self.dictionary = FixDictionary.from_xml(file_name)
            self.status_label.setText(f"Loaded dictionary: {file_name}")
        except Exception as exc:  # noqa: BLE001 - GUI boundary needs a user-facing error.
            QMessageBox.critical(self, "Dictionary error", str(exc))

    def _decode_paste(self) -> None:
        messages = parse_fix_messages(self.paste_box.toPlainText(), self.dictionary)
        self.current_file = None
        self.pasted_messages = messages
        entries = [
            IndexEntry(row=index, offset=0, length=len(message.raw), summary=message.summary)
            for index, message in enumerate(messages)
        ]
        self.message_model.set_entries(entries)
        self.field_model.set_message(messages[0] if messages else None)
        self.raw_view.setPlainText(format_message_text(messages[0]) if messages else "")
        self.status_label.setText(f"Decoded {len(messages)} pasted message(s)")

    def _open_file(self, path: Path) -> None:
        self._cancel_index()
        self.current_file = path
        self.pasted_messages = []
        self.message_model.set_entries([])
        self.field_model.set_message(None)
        self.raw_view.clear()
        self.status_label.setText(f"Indexing {path} ...")
        self.worker_thread = QThread(self)
        self.worker = IndexWorker(path, self.dictionary)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._index_finished)
        self.worker.failed.connect(self._index_failed)
        self.worker.progress.connect(self._index_progress)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _cancel_index(self) -> None:
        if self.worker:
            self.worker.cancel()

    def _index_progress(self, done: int, total: int) -> None:
        if total:
            self.status_label.setText(f"Indexing {done:,} / {total:,} bytes")
        else:
            self.status_label.setText(f"Indexing {done:,} bytes")

    def _index_finished(self, entries: list[IndexEntry], path_text: str) -> None:
        self.message_model.set_entries(entries)
        self.status_label.setText(f"Indexed {len(entries)} message(s) from {path_text}")
        self.worker = None
        self.worker_thread = None
        if entries:
            self.message_table.selectRow(0)

    def _index_failed(self, error: str) -> None:
        self.worker = None
        self.worker_thread = None
        QMessageBox.critical(self, "Indexing error", error)
        self.status_label.setText("Indexing failed")

    def _select_message(self, *_args) -> None:
        rows = self.message_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        entry = self.message_model.entries[row]
        try:
            if self.current_file:
                message = read_indexed_message(self.current_file, entry, self.dictionary)
            else:
                message = self.pasted_messages[row]
        except Exception as exc:  # noqa: BLE001 - GUI boundary needs a user-facing error.
            QMessageBox.critical(self, "Decode error", str(exc))
            return
        self.field_model.set_message(message)
        self.raw_view.setPlainText(format_message_text(message) + "\n\nNormalized:\n" + printable_message(message))

    def _filter_rows(self, text: str) -> None:
        needle = text.casefold().strip()
        for row, entry in enumerate(self.message_model.entries):
            summary = entry.summary
            haystack = " ".join(
                value or ""
                for value in (
                    summary.msg_type,
                    summary.msg_name,
                    summary.seq_num,
                    summary.sender,
                    summary.target,
                    summary.cl_ord_id,
                    summary.order_id,
                    summary.exec_id,
                    summary.validation_status,
                )
            ).casefold()
            self.message_table.setRowHidden(row, bool(needle and needle not in haystack))


def main() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.show()
    return app.exec()
