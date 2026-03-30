"""Ebook conversion via Calibre ebook-convert."""

from __future__ import annotations

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class CalibreConverter(Converter):
    def __init__(self, config: ToolchainConfig) -> None:
        self._calibre = config.calibre or "ebook-convert"

    @property
    def supported_inputs(self) -> set[str]:
        return extension_set(["epub", "mobi", "azw3", "pdf"])

    @property
    def supported_outputs(self) -> set[str]:
        return extension_set(["epub", "mobi", "azw3", "pdf", "txt"])

    def build_command(self, task: ConversionTask) -> list[str]:
        output = self.build_output_path(task)
        return [self._calibre, str(task.source_path), str(output)]
