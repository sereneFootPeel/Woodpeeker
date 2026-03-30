"""Text and document conversion via Pandoc."""

from __future__ import annotations

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class PandocConverter(Converter):
    def __init__(self, config: ToolchainConfig) -> None:
        self._pandoc = config.pandoc or "pandoc"

    @property
    def supported_inputs(self) -> set[str]:
        return extension_set(["txt", "md", "markdown", "html", "docx", "odt", "rtf"])

    @property
    def supported_outputs(self) -> set[str]:
        return extension_set(["txt", "md", "html", "docx", "odt", "rtf", "pdf"])

    def build_command(self, task: ConversionTask) -> list[str]:
        output = self.build_output_path(task)
        return [
            self._pandoc,
            str(task.source_path),
            "-o",
            str(output),
        ]
