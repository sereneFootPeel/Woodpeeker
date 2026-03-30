"""Converter abstraction and helper utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from app.core.models import ConversionTask
from app.core.process_runner import ProcessResult


class Converter(ABC):
    @property
    @abstractmethod
    def supported_inputs(self) -> set[str]:
        pass

    @property
    @abstractmethod
    def supported_outputs(self) -> set[str]:
        pass

    def can_handle(self, source: Path, target_format: str) -> bool:
        source_ext = source.suffix.lower().lstrip(".")
        return source_ext in self.supported_inputs and target_format in self.supported_outputs

    @abstractmethod
    def build_command(self, task: ConversionTask) -> list[str]:
        pass

    def build_output_path(self, task: ConversionTask) -> Path:
        stem = task.source_path.stem
        return task.output_dir / f"{stem}.{task.target_format}"


def extension_set(items: Iterable[str]) -> set[str]:
    return {item.lower().lstrip(".") for item in items}


def quote_if_needed(value: str) -> str:
    return f'"{value}"' if " " in value else value


def merge_command(parts: list[str]) -> str:
    return " ".join(quote_if_needed(item) for item in parts)


def process_ok(result: ProcessResult) -> bool:
    return result.return_code == 0
