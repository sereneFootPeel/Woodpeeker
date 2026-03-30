"""Text/document to ebook conversion via Pandoc + Calibre."""

from __future__ import annotations

import sys

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class TextEbookConverter(Converter):
    _INPUT_FORMATS = extension_set(["txt", "md", "markdown", "html", "docx", "odt", "rtf"])
    _OUTPUT_FORMATS = extension_set(["epub", "mobi", "azw3"])

    def __init__(self, config: ToolchainConfig) -> None:
        self._pandoc = config.pandoc or "pandoc"
        self._calibre = config.calibre or "ebook-convert"

    @property
    def supported_inputs(self) -> set[str]:
        return self._INPUT_FORMATS

    @property
    def supported_outputs(self) -> set[str]:
        return self._OUTPUT_FORMATS

    def build_command(self, task: ConversionTask) -> list[str]:
        output = self.build_output_path(task)
        return [
            sys.executable,
            "-m",
            "app.tools.text_ebook_pipeline",
            "--pandoc",
            self._pandoc,
            "--calibre",
            self._calibre,
            "--source",
            str(task.source_path),
            "--output",
            str(output),
            "--target-format",
            task.target_format,
        ]
