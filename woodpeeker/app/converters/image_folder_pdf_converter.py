"""Convert all images in a folder into one PDF via ImageMagick."""

from __future__ import annotations

import re
from pathlib import Path

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class ImageFolderPdfConverter(Converter):
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
        return {"<image-folder>"}

    @property
    def supported_outputs(self) -> set[str]:
        return {"pdf"}

    def can_handle(self, source: Path, target_format: str) -> bool:
        if target_format != "pdf":
            return False
        # Some inputs can carry wrapped quotes from external drag/drop sources.
        normalized = Path(str(source).strip().strip('"'))
        return normalized.is_dir()

    def build_output_path(self, task: ConversionTask) -> Path:
        folder_name = task.source_path.name or "image_folder"
        return task.output_dir / f"{folder_name}.pdf"

    def _sorted_image_files(self, source_dir: Path) -> list[Path]:
        images = [
            path
            for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower().lstrip(".") in self._IMAGE_FORMATS
        ]
        return sorted(images, key=lambda item: self._natural_key(item.name))

    def _natural_key(self, name: str) -> tuple[tuple[int, object], ...]:
        parts = re.split(r"(\d+)", name.lower())
        key: list[tuple[int, object]] = []
        for part in parts:
            if not part:
                continue
            # Use tagged tuples to avoid direct str/int comparison in sorting.
            if part.isdigit():
                key.append((0, int(part)))
            else:
                key.append((1, part))
        return tuple(key)

    def build_command(self, task: ConversionTask) -> list[str]:
        source_dir = Path(str(task.source_path).strip().strip('"'))
        if not source_dir.is_dir():
            raise ValueError(f"Source is not a folder: {task.source_path}")
        image_files = self._sorted_image_files(source_dir)
        if not image_files:
            raise ValueError(f"No image files found in folder: {source_dir}")
        output = self.build_output_path(task)
        return [self._magick, *[str(path) for path in image_files], str(output)]
