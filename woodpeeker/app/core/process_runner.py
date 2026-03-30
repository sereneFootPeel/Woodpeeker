"""Unified subprocess execution for converters."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Sequence


def _windows_subprocess_kwargs() -> dict[str, object]:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }


@dataclass
class ProcessResult:
    command: str
    stdout: str
    stderr: str
    return_code: int
    started_at: datetime
    finished_at: datetime


class ProcessRunner:
    def __init__(self) -> None:
        self._active_processes: dict[str, subprocess.Popen[str]] = {}
        self._lock = Lock()
        self._runtime_env = self._build_runtime_env()

    def _build_runtime_env(self) -> dict[str, str]:
        env = os.environ.copy()
        path_sep = os.pathsep
        raw_path = env.get("PATH", "")
        existing_parts = [part for part in raw_path.split(path_sep) if part]
        existing_lower = {part.lower() for part in existing_parts}

        from app.config.toolchain import detect_all

        config = detect_all()
        tool_paths = [
            config.ffmpeg,
            config.pandoc,
            config.libreoffice,
            config.calibre,
            config.ncmdump,
            config.imagemagick,
        ]
        extra_parts: list[str] = []
        for tool in tool_paths:
            if not tool:
                continue
            parent = str(Path(tool).resolve().parent)
            if parent.lower() in existing_lower:
                continue
            extra_parts.append(parent)
            existing_lower.add(parent.lower())

        if extra_parts:
            env["PATH"] = path_sep.join(extra_parts + existing_parts)
        return env

    def run(
        self,
        task_id: str,
        command: Sequence[str],
        cwd: Path | None = None,
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
    ) -> ProcessResult:
        started = datetime.now()
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._runtime_env,
            text=True,
            shell=False,
            encoding="utf-8",
            errors="replace",
            **_windows_subprocess_kwargs(),
        )
        with self._lock:
            self._active_processes[task_id] = process

        stdout_data = ""
        stderr_data = ""
        out, err = process.communicate()
        if out:
            stdout_data = out
            if on_stdout:
                on_stdout(out)
        if err:
            stderr_data = err
            if on_stderr:
                on_stderr(err)

        with self._lock:
            self._active_processes.pop(task_id, None)

        finished = datetime.now()
        return ProcessResult(
            command=" ".join(command),
            stdout=stdout_data,
            stderr=stderr_data,
            return_code=process.returncode,
            started_at=started,
            finished_at=finished,
        )

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            process = self._active_processes.get(task_id)
        if not process:
            return False
        process.terminate()
        return True
