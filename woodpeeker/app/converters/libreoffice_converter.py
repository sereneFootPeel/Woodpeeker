"""Office/PDF conversion via LibreOffice headless."""

from __future__ import annotations

from pathlib import Path

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class LibreOfficeConverter(Converter):
    def __init__(self, config: ToolchainConfig) -> None:
        self._soffice = config.libreoffice or "soffice"

    @property
    def supported_inputs(self) -> set[str]:
        return extension_set(["doc", "docx", "ppt", "pptx", "xls", "xlsx", "odt", "rtf"])

    @property
    def supported_outputs(self) -> set[str]:
        return extension_set(["pdf", "docx", "odt", "rtf", "html", "txt"])

    def build_command(self, task: ConversionTask) -> list[str]:
        return [
            self._soffice,
            "--headless",
            "--convert-to",
            task.target_format,
            str(task.source_path),
            "--outdir",
            str(task.output_dir),
        ]

    def build_output_path(self, task: ConversionTask) -> Path:
        return task.output_dir / f"{task.source_path.stem}.{task.target_format}"
