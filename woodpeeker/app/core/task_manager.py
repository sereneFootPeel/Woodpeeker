"""Task queue lifecycle, retries, cancellation and execution."""

from __future__ import annotations

import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
import tempfile
from threading import Event, Lock, Thread
from typing import Callable

from app.converters.router import ConverterRouter
from app.core.models import ConversionResult, ConversionTask
from app.core.process_runner import ProcessRunner


TaskCallback = Callable[[ConversionResult], None]
ProgressCallback = Callable[[str, str], None]


class TaskManager:
    def __init__(
        self,
        router: ConverterRouter,
        runner: ProcessRunner,
        max_retries: int = 1,
        max_workers: int = 1,
    ):
        self._router = router
        self._runner = runner
        self._max_retries = max_retries
        self._max_workers = max(1, max_workers)
        self._queue: deque[tuple[ConversionTask, int]] = deque()
        self._cancelled: set[str] = set()
        self._queue_lock = Lock()
        self._wake_event = Event()
        self._stop_event = Event()
        self._callbacks_lock = Lock()
        self._task_callbacks: list[TaskCallback] = []
        self._progress_callbacks: list[ProgressCallback] = []
        self._workers: list[Thread] = []
        for worker_id in range(self._max_workers):
            worker = Thread(target=self._work_loop, args=(worker_id,), daemon=True)
            worker.start()
            self._workers.append(worker)

    def on_task_done(self, callback: TaskCallback) -> None:
        with self._callbacks_lock:
            self._task_callbacks.append(callback)

    def on_progress(self, callback: ProgressCallback) -> None:
        with self._callbacks_lock:
            self._progress_callbacks.append(callback)

    def enqueue(self, task: ConversionTask) -> None:
        with self._queue_lock:
            self._queue.append((task, 0))
        self._emit_progress(task.task_id, "queued")
        self._wake_event.set()

    def retry(self, task: ConversionTask) -> None:
        with self._queue_lock:
            self._queue.appendleft((task, 0))
        self._emit_progress(task.task_id, "retry_queued")
        self._wake_event.set()

    def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)
        self._runner.cancel(task_id)
        self._emit_progress(task_id, "cancelled")

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def _emit_progress(self, task_id: str, status: str) -> None:
        with self._callbacks_lock:
            callbacks = list(self._progress_callbacks)
        for callback in callbacks:
            callback(task_id, status)

    def _emit_result(self, result: ConversionResult) -> None:
        with self._callbacks_lock:
            callbacks = list(self._task_callbacks)
        for callback in callbacks:
            callback(result)

    def _work_loop(self, worker_id: int) -> None:
        while not self._stop_event.is_set():
            task_item = self._pop_task()
            if task_item is None:
                self._wake_event.wait(timeout=0.2)
                self._wake_event.clear()
                continue
            task, retry_count = task_item
            if task.task_id in self._cancelled:
                continue
            self._emit_progress(task.task_id, f"running_w{worker_id + 1}")
            self._run_task(task, retry_count)

    def _pop_task(self) -> tuple[ConversionTask, int] | None:
        with self._queue_lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def _run_task(self, task: ConversionTask, retry_count: int) -> None:
        started = datetime.now()
        try:
            plan = self._router.resolve_plan(task.source_path, task.target_format, max_hops=2)

            output_path = task.output_dir / f"{task.source_path.stem}.{task.target_format}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_parts: list[str] = []
            stderr_parts: list[str] = []
            command_parts: list[str] = []
            process = None

            if len(plan) == 1:
                converter = plan[0].converter
                process = self._runner.run(
                    task_id=task.task_id,
                    command=converter.build_command(task),
                    cwd=Path.cwd(),
                )
                stdout_parts.append(process.stdout)
                stderr_parts.append(process.stderr)
                command_parts.append(process.command)
            else:
                with tempfile.TemporaryDirectory(prefix="woodpeeker_chain_") as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    middle_task = ConversionTask(
                        source_path=task.source_path,
                        output_dir=temp_dir,
                        target_format=plan[0].target_format,
                        profile=task.profile,
                        task_id=task.task_id,
                    )
                    middle_converter = plan[0].converter
                    middle_process = self._runner.run(
                        task_id=task.task_id,
                        command=middle_converter.build_command(middle_task),
                        cwd=Path.cwd(),
                    )
                    stdout_parts.append(middle_process.stdout)
                    stderr_parts.append(middle_process.stderr)
                    command_parts.append(middle_process.command)
                    middle_output = middle_converter.build_output_path(middle_task)
                    if middle_process.return_code != 0 or not middle_output.exists():
                        process = middle_process
                    else:
                        final_task = ConversionTask(
                            source_path=middle_output,
                            output_dir=task.output_dir,
                            target_format=plan[1].target_format,
                            profile=task.profile,
                            task_id=task.task_id,
                        )
                        final_converter = plan[1].converter
                        final_process = self._runner.run(
                            task_id=task.task_id,
                            command=final_converter.build_command(final_task),
                            cwd=Path.cwd(),
                        )
                        stdout_parts.append(final_process.stdout)
                        stderr_parts.append(final_process.stderr)
                        command_parts.append(final_process.command)
                        process = final_process

            if process is None:
                raise RuntimeError("Conversion process did not start.")

            if task.task_id in self._cancelled:
                result = ConversionResult(
                    task_id=task.task_id,
                    source_path=task.source_path,
                    output_path=None,
                    success=False,
                    message="Cancelled",
                    command=" && ".join(command_parts),
                    stderr="\n".join(part for part in stderr_parts if part),
                    stdout="\n".join(part for part in stdout_parts if part),
                    return_code=process.return_code,
                    started_at=process.started_at,
                    finished_at=process.finished_at,
                )
                self._emit_result(result)
                self._emit_progress(task.task_id, "done")
                return
            success = process.return_code == 0 and output_path.exists()
            message = "Completed" if success else "Failed"
            result = ConversionResult(
                task_id=task.task_id,
                source_path=task.source_path,
                output_path=output_path if output_path.exists() else None,
                success=success,
                message=message,
                command=" && ".join(command_parts),
                stderr="\n".join(part for part in stderr_parts if part),
                stdout="\n".join(part for part in stdout_parts if part),
                return_code=process.return_code,
                started_at=process.started_at,
                finished_at=process.finished_at,
            )
            if not success and retry_count < self._max_retries and task.task_id not in self._cancelled:
                with self._queue_lock:
                    self._queue.append((task, retry_count + 1))
                self._emit_progress(task.task_id, f"retrying_{retry_count + 1}")
            else:
                self._emit_result(result)
                self._emit_progress(task.task_id, "done")
        except Exception as exc:  # pylint: disable=broad-except
            finished = datetime.now()
            error_detail = f"{exc}\n{traceback.format_exc()}"
            result = ConversionResult(
                task_id=task.task_id,
                source_path=task.source_path,
                output_path=None,
                success=False,
                message=f"Exception: {exc}",
                command="(not started)",
                stderr=error_detail,
                stdout="",
                return_code=1,
                started_at=started,
                finished_at=finished,
            )
            self._emit_result(result)
            self._emit_progress(task.task_id, "done")
