"""Main GUI for unified format conversion."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config.toolchain import load_config
from app.converters.calibre_converter import CalibreConverter
from app.converters.ffmpeg_converter import FFmpegConverter
from app.converters.image_folder_pdf_converter import ImageFolderPdfConverter
from app.converters.imagemagick_converter import ImageMagickConverter
from app.converters.libreoffice_converter import LibreOfficeConverter
from app.converters.ncmdump_converter import NcmdumpConverter
from app.converters.pandoc_converter import PandocConverter
from app.converters.router import ConverterRouter
from app.converters.text_ebook_converter import TextEbookConverter
from app.core.models import ConversionResult, ConversionTask
from app.core.process_runner import ProcessRunner
from app.core.task_manager import TaskManager


PREFERRED_TARGET_FORMATS = [
    "mp3",
    "wav",
    "flac",
    "aac",
    "ogg",
    "m4a",
    "mp4",
    "mkv",
    "avi",
    "mov",
    "webm",
    "txt",
    "md",
    "html",
    "docx",
    "pdf",
    "odt",
    "rtf",
    "epub",
    "mobi",
    "azw3",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",
    "bmp",
    "tif",
    "tiff",
    "avif",
    "heic",
    "svg",
    "ico",
]


class MainWindow(QMainWindow):
    taskProgressSignal = Signal(str, str)
    taskDoneSignal = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Woodpeeker")
        self.resize(1100, 700)

        self._config = load_config()
        self._task_index: dict[str, ConversionTask] = {}
        self._result_index: dict[str, ConversionResult] = {}
        self._task_row_by_id: dict[str, int] = {}
        self._router = self._build_router()

        self._manager = self._build_task_manager(max_workers=1)

        self.taskProgressSignal.connect(self._on_task_progress)
        self.taskDoneSignal.connect(self._on_task_done)

        self._queue_tab = QWidget()
        self.setCentralWidget(self._queue_tab)

        self._build_queue_tab()

    def closeEvent(self, event):  # type: ignore[override]
        self._manager.stop()
        super().closeEvent(event)

    def _build_queue_tab(self) -> None:
        root = QVBoxLayout()

        picker_row = QHBoxLayout()
        self._source_list = SourceListWidget()
        self._source_list.filesChanged.connect(self._refresh_target_formats)
        add_files_btn = QPushButton("Add Files")
        add_files_btn.clicked.connect(self._add_files)
        add_folder_btn = QPushButton("Add Folder")
        add_folder_btn.clicked.connect(self._add_folder)
        remove_selected_btn = QPushButton("Remove Selected")
        remove_selected_btn.clicked.connect(self._remove_selected_files)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_source_files)
        picker_row.addWidget(add_files_btn)
        picker_row.addWidget(add_folder_btn)
        picker_row.addWidget(remove_selected_btn)
        picker_row.addWidget(clear_btn)
        picker_row.addStretch()

        options_row = QGridLayout()
        self._target_combo = QComboBox()
        self._profile_combo = QComboBox()
        self._profile_combo.addItems(["default", "fast", "quality"])
        self._output_dir = QLineEdit("")
        output_btn = QPushButton("Browse")
        output_btn.clicked.connect(self._select_output_dir)
        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 8)
        self._parallel_spin.setValue(2)
        options_row.addWidget(QLabel("Target format"), 0, 0)
        options_row.addWidget(self._target_combo, 0, 1)
        options_row.addWidget(QLabel("Profile"), 0, 2)
        options_row.addWidget(self._profile_combo, 0, 3)
        options_row.addWidget(QLabel("Output directory"), 1, 0)
        options_row.addWidget(self._output_dir, 1, 1, 1, 2)
        options_row.addWidget(output_btn, 1, 3)
        options_row.addWidget(QLabel("Concurrency"), 2, 0, 1, 2)
        options_row.addWidget(self._parallel_spin, 2, 2)

        action_row = QHBoxLayout()
        self._start_btn = QPushButton("Start Queue")
        self._start_btn.clicked.connect(self._start_queue)
        cancel_btn = QPushButton("Cancel Selected Task")
        cancel_btn.clicked.connect(self._cancel_selected_task)
        retry_btn = QPushButton("Retry Selected Task")
        retry_btn.clicked.connect(self._retry_selected_task)
        export_logs_btn = QPushButton("Export Logs")
        export_logs_btn.clicked.connect(self._export_logs)
        action_row.addWidget(self._start_btn)
        action_row.addWidget(cancel_btn)
        action_row.addWidget(retry_btn)
        action_row.addWidget(export_logs_btn)
        action_row.addStretch()

        self._task_table = QTableWidget(0, 7)
        self._task_table.setHorizontalHeaderLabels(
            ["Task ID", "Source", "Target", "Profile", "Status", "Output", "Message"]
        )
        self._task_table.horizontalHeader().setStretchLastSection(True)

        self._detail_log = QPlainTextEdit()
        self._detail_log.setReadOnly(True)

        self._task_table.itemSelectionChanged.connect(self._show_task_details)

        root.addLayout(picker_row)
        root.addWidget(QLabel("Tip: You can drag files or folders here directly."))
        root.addWidget(self._source_list)
        root.addLayout(options_row)
        root.addLayout(action_row)
        root.addWidget(self._task_table, 2)
        root.addWidget(QLabel("Task details (command/stdout/stderr):"))
        root.addWidget(self._detail_log, 1)

        self._queue_tab.setLayout(root)
        self._refresh_target_formats()

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select source files")
        existing = {self._source_list.item(i).text() for i in range(self._source_list.count())}
        for source in files:
            if source not in existing:
                self._source_list.addItem(source)
                existing.add(source)

    def _remove_selected_files(self) -> None:
        for item in self._source_list.selectedItems():
            self._source_list.takeItem(self._source_list.row(item))

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select source folder")
        if not folder:
            return
        existing = {self._source_list.item(i).text() for i in range(self._source_list.count())}
        if folder not in existing:
            self._source_list.addItem(folder)

    def _clear_source_files(self) -> None:
        self._source_list.clear()

    def _source_paths(self) -> list[Path]:
        paths: list[Path] = []
        for i in range(self._source_list.count()):
            raw = self._source_list.item(i).text()
            normalized = raw.strip().strip('"')
            paths.append(Path(normalized))
        return paths

    def _refresh_target_formats(self) -> None:
        source_paths = self._source_paths()
        current = self._target_combo.currentText()
        if source_paths:
            common_targets = self._router.common_targets_for_sources(source_paths)
        else:
            common_targets = self._router.all_supported_targets()

        ordered_targets = self._order_targets(common_targets)
        self._target_combo.blockSignals(True)
        self._target_combo.clear()
        self._target_combo.addItems(ordered_targets)
        self._target_combo.blockSignals(False)

        has_targets = bool(ordered_targets)
        self._target_combo.setEnabled(has_targets)
        self._start_btn.setEnabled(self._source_list.count() > 0 and has_targets)
        if has_targets:
            if current in ordered_targets:
                self._target_combo.setCurrentText(current)
            else:
                self._target_combo.setCurrentIndex(0)

    def _order_targets(self, targets: set[str]) -> list[str]:
        ordered = [fmt for fmt in PREFERRED_TARGET_FORMATS if fmt in targets]
        extras = sorted(targets - set(PREFERRED_TARGET_FORMATS))
        return ordered + extras

    def _select_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Select output directory", self._output_dir.text()
        )
        if selected:
            self._output_dir.setText(selected)

    def _start_queue(self) -> None:
        if self._source_list.count() == 0:
            QMessageBox.warning(self, "No files", "Please add source files first.")
            return

        if not self._target_combo.isEnabled():
            QMessageBox.warning(
                self,
                "Unsupported conversion",
                "No common target format is available for current source files.",
            )
            return

        output_dir_text = self._output_dir.text().strip()
        if not output_dir_text:
            QMessageBox.warning(
                self, "No output directory", "Please choose an output directory first."
            )
            return
        output_dir = Path(output_dir_text).expanduser()
        target_format = self._target_combo.currentText()
        profile = self._profile_combo.currentText()
        source_paths = self._source_paths()

        missing = [source_path for source_path in source_paths if not source_path.exists()]
        if missing:
            samples = "\n".join(str(path) for path in missing[:8])
            extra = "" if len(missing) <= 8 else f"\n... and {len(missing) - 8} more"
            QMessageBox.warning(
                self,
                "Missing source path",
                (
                    "Some source paths do not exist:\n\n"
                    f"{samples}{extra}\n\n"
                    "Please remove them or re-add the correct paths."
                ),
            )
            return

        unsupported = [
            source_path
            for source_path in source_paths
            if not self._router.can_route(source_path, target_format, max_hops=2)
        ]
        if unsupported:
            samples = "\n".join(str(path) for path in unsupported[:8])
            extra = "" if len(unsupported) <= 8 else f"\n... and {len(unsupported) - 8} more"
            QMessageBox.warning(
                self,
                "Unsupported conversion",
                (
                    f"Target format '{target_format}' is not supported for these files:\n\n"
                    f"{samples}{extra}\n\n"
                    "Please choose another target format."
                ),
            )
            return

        max_workers = self._parallel_spin.value()
        self._rebuild_manager(max_workers=max_workers)

        for source_path in source_paths:
            task = ConversionTask(
                source_path=source_path,
                output_dir=output_dir,
                target_format=target_format,
                profile=profile,
            )
            self._append_task_row(task)
            self._task_index[task.task_id] = task
            self._manager.enqueue(task)

    def _append_task_row(self, task: ConversionTask) -> None:
        row = self._task_table.rowCount()
        self._task_table.insertRow(row)
        self._task_row_by_id[task.task_id] = row
        self._task_table.setItem(row, 0, QTableWidgetItem(task.task_id))
        self._task_table.setItem(row, 1, QTableWidgetItem(str(task.source_path)))
        self._task_table.setItem(row, 2, QTableWidgetItem(task.target_format))
        self._task_table.setItem(row, 3, QTableWidgetItem(task.profile))
        self._task_table.setItem(row, 4, QTableWidgetItem("queued"))
        self._task_table.setItem(row, 5, QTableWidgetItem(""))
        self._task_table.setItem(row, 6, QTableWidgetItem(""))

    def _on_task_progress(self, task_id: str, status: str) -> None:
        row = self._task_row_by_id.get(task_id)
        if row is None:
            return
        self._task_table.setItem(row, 4, QTableWidgetItem(status))

    def _on_task_done(self, result: ConversionResult) -> None:
        self._result_index[result.task_id] = result
        row = self._task_row_by_id.get(result.task_id)
        if row is None:
            return
        self._task_table.setItem(row, 4, QTableWidgetItem("success" if result.success else "failed"))
        self._task_table.setItem(row, 5, QTableWidgetItem(str(result.output_path or "")))
        self._task_table.setItem(row, 6, QTableWidgetItem(result.message))

    def _selected_task_id(self) -> str | None:
        row = self._task_table.currentRow()
        if row < 0:
            return None
        item = self._task_table.item(row, 0)
        return item.text() if item else None

    def _cancel_selected_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id:
            self._manager.cancel(task_id)

    def _retry_selected_task(self) -> None:
        task_id = self._selected_task_id()
        if not task_id:
            return
        task = self._task_index.get(task_id)
        if not task:
            return
        self._manager.retry(task)

    def _show_task_details(self) -> None:
        task_id = self._selected_task_id()
        if not task_id:
            self._detail_log.clear()
            return
        result = self._result_index.get(task_id)
        if not result:
            self._detail_log.setPlainText("Task has not finished yet.")
            return
        detail = "\n".join(
            [
                f"Command: {result.command}",
                f"Return code: {result.return_code}",
                f"Started: {result.started_at.isoformat()}",
                f"Finished: {result.finished_at.isoformat()}",
                "",
                "STDOUT:",
                result.stdout or "(empty)",
                "",
                "STDERR:",
                result.stderr or "(empty)",
            ]
        )
        self._detail_log.setPlainText(detail)

    def _export_logs(self) -> None:
        if not self._result_index:
            QMessageBox.information(self, "No logs", "No completed tasks to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export logs", "conversion_logs.txt", "Text files (*.txt)"
        )
        if not path:
            return
        lines: list[str] = []
        for task_id, result in self._result_index.items():
            lines.extend(
                [
                    f"Task: {task_id}",
                    f"Source: {result.source_path}",
                    f"Output: {result.output_path}",
                    f"Success: {result.success}",
                    f"Command: {result.command}",
                    f"Return code: {result.return_code}",
                    "STDERR:",
                    result.stderr,
                    "-" * 80,
                ]
            )
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        QMessageBox.information(self, "Exported", f"Logs exported to {path}")

    def _build_router(self) -> ConverterRouter:
        return ConverterRouter(
            [
                FFmpegConverter(self._config),
                NcmdumpConverter(self._config),
                PandocConverter(self._config),
                TextEbookConverter(self._config),
                LibreOfficeConverter(self._config),
                CalibreConverter(self._config),
                ImageMagickConverter(self._config),
                ImageFolderPdfConverter(self._config),
            ]
        )

    def _build_task_manager(self, max_workers: int) -> TaskManager:
        manager = TaskManager(
            router=self._router,
            runner=ProcessRunner(),
            max_workers=max_workers,
        )
        manager.on_progress(lambda task_id, status: self.taskProgressSignal.emit(task_id, status))
        manager.on_task_done(lambda result: self.taskDoneSignal.emit(result))
        return manager

    def _rebuild_manager(self, max_workers: int) -> None:
        self._manager.stop()
        self._manager = self._build_task_manager(max_workers=max_workers)


class SourceListWidget(QListWidget):
    filesChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def addItem(self, item):  # type: ignore[override]
        super().addItem(item)
        self.filesChanged.emit()

    def takeItem(self, row):  # type: ignore[override]
        item = super().takeItem(row)
        self.filesChanged.emit()
        return item

    def clear(self) -> None:  # type: ignore[override]
        if self.count() == 0:
            return
        super().clear()
        self.filesChanged.emit()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        existing = {self.item(i).text() for i in range(self.count())}
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            file_path = url.toLocalFile()
            if file_path and file_path not in existing:
                self.addItem(file_path)
                existing.add(file_path)
        event.acceptProposedAction()
