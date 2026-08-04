"""Batch input file list: add/remove/reorder, drag-and-drop from Explorer,
used by every converter/feature page that accepts one-or-more input files."""
import os

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)


class _DropListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class FileBatchList(QWidget):
    changed = Signal()

    def __init__(self, dialog_filter: str = "All files (*.*)", parent=None):
        super().__init__(parent)
        self._dialog_filter = dialog_filter

        self.list_widget = _DropListWidget()
        self.list_widget.files_dropped.connect(self._add_paths)
        self.list_widget.model().rowsMoved.connect(lambda *_: self.changed.emit())

        add_btn = QPushButton(qta.icon("fa5s.plus"), " Add Files")
        add_folder_btn = QPushButton(qta.icon("fa5s.folder-plus"), " Add Folder")
        remove_btn = QPushButton(qta.icon("fa5s.minus"), " Remove")
        clear_btn = QPushButton(qta.icon("fa5s.trash"), " Clear")
        up_btn = QPushButton(qta.icon("fa5s.arrow-up"), "")
        down_btn = QPushButton(qta.icon("fa5s.arrow-down"), "")

        add_btn.clicked.connect(self._browse_files)
        add_folder_btn.clicked.connect(self._browse_folder)
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn.clicked.connect(self._clear)
        up_btn.clicked.connect(lambda: self._move(-1))
        down_btn.clicked.connect(lambda: self._move(1))

        btn_row = QHBoxLayout()
        for b in (add_btn, add_folder_btn, remove_btn, clear_btn):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(btn_row)
        layout.addWidget(self.list_widget)

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add files", "", self._dialog_filter)
        self._add_paths(paths)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add folder")
        if not folder:
            return
        paths = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                  if os.path.isfile(os.path.join(folder, f))]
        self._add_paths(paths)

    def _add_paths(self, paths: list):
        existing = set(self.paths())
        for p in paths:
            if p and p not in existing and os.path.isfile(p):
                item = QListWidgetItem(os.path.basename(p))
                item.setData(Qt.ItemDataRole.UserRole, p)
                item.setToolTip(p)
                self.list_widget.addItem(item)
                existing.add(p)
        self.changed.emit()

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.changed.emit()

    def _clear(self):
        self.list_widget.clear()
        self.changed.emit()

    def _move(self, delta: int):
        row = self.list_widget.currentRow()
        new_row = row + delta
        if row < 0 or new_row < 0 or new_row >= self.list_widget.count():
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(new_row, item)
        self.list_widget.setCurrentRow(new_row)
        self.changed.emit()

    def paths(self) -> list:
        return [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list_widget.count())]

    def count(self) -> int:
        return self.list_widget.count()
