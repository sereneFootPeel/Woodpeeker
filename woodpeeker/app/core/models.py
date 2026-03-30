"""Core data models for conversion tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4


@dataclass
class ConversionTask:
    source_path: Path
    output_dir: Path
    target_format: str
    profile: str = "default"
    task_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ConversionResult:
    task_id: str
    source_path: Path
    output_path: Optional[Path]
    success: bool
    message: str
    command: str
    stderr: str
    stdout: str
    return_code: int
    started_at: datetime
    finished_at: datetime
