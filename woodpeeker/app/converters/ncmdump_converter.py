"""NCM decoding converter based on ncmdump + ffmpeg pipeline."""

from __future__ import annotations

import sys

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class NcmdumpConverter(Converter):
    _INPUT_FORMATS = extension_set(["ncm"])
    _OUTPUT_FORMATS = extension_set(["mp3", "wav", "flac", "aac", "ogg", "m4a"])

    def __init__(self, config: ToolchainConfig) -> None:
        self._ncmdump = config.ncmdump or "ncmdump"
        self._ffmpeg = config.ffmpeg or "ffmpeg"

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
            "app.tools.ncm_pipeline",
            "--ncmdump",
            self._ncmdump,
            "--ffmpeg",
            self._ffmpeg,
            "--source",
            str(task.source_path),
            "--output",
            str(output),
            "--target-format",
            task.target_format,
            "--profile",
            task.profile,
        ]
