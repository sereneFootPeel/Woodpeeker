"""Image conversion via ImageMagick."""

from __future__ import annotations

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class ImageMagickConverter(Converter):
    _IMAGE_FORMATS = extension_set(
        [
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
    )

    def __init__(self, config: ToolchainConfig) -> None:
        self._magick = config.imagemagick or "magick"

    @property
    def supported_inputs(self) -> set[str]:
        return self._IMAGE_FORMATS

    @property
    def supported_outputs(self) -> set[str]:
        return self._IMAGE_FORMATS

    def build_command(self, task: ConversionTask) -> list[str]:
        output = self.build_output_path(task)
        return [self._magick, str(task.source_path), str(output)]
