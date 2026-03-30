"""Routes tasks to proper converter adapters."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from app.converters.base import Converter
from app.core.models import ConversionTask


class ConversionStep(NamedTuple):
    converter: Converter
    target_format: str


class ConverterRouter:
    def __init__(self, converters: list[Converter]) -> None:
        self._converters = converters

    def supports(self, source_path: Path, target_format: str) -> bool:
        target = target_format.lower().lstrip(".")
        for converter in self._converters:
            if converter.can_handle(source_path, target):
                return True
        return self.can_route(source_path, target, max_hops=2)

    def _source_ext(self, source_path: Path) -> str:
        return source_path.suffix.lower().lstrip(".")

    def all_supported_targets(self) -> set[str]:
        all_targets: set[str] = set()
        for converter in self._converters:
            all_targets |= converter.supported_outputs
        return all_targets

    def supported_targets_for_source(self, source_path: Path) -> set[str]:
        supported = self.reachable_targets_for_source(source_path, max_hops=2)
        for converter in self._converters:
            for target in converter.supported_outputs:
                if converter.can_handle(source_path, target):
                    supported.add(target)
        return supported

    def reachable_targets_for_source(self, source_path: Path, max_hops: int = 2) -> set[str]:
        source_ext = self._source_ext(source_path)
        if not source_ext or max_hops <= 0:
            return set()

        visited_depth: dict[str, int] = {source_ext: 0}
        queue: list[str] = [source_ext]
        reachable: set[str] = set()

        while queue:
            current = queue.pop(0)
            current_depth = visited_depth[current]
            if current_depth >= max_hops:
                continue
            for converter in self._converters:
                if current not in converter.supported_inputs:
                    continue
                for nxt in converter.supported_outputs:
                    next_depth = current_depth + 1
                    old_depth = visited_depth.get(nxt)
                    if old_depth is not None and old_depth <= next_depth:
                        continue
                    visited_depth[nxt] = next_depth
                    queue.append(nxt)
                    if nxt != source_ext:
                        reachable.add(nxt)
        return reachable

    def can_route(self, source_path: Path, target_format: str, max_hops: int = 2) -> bool:
        target = target_format.lower().lstrip(".")
        if self._converter_for_step(source_path, target):
            return True
        return target in self.reachable_targets_for_source(source_path, max_hops=max_hops)

    def common_targets_for_sources(self, source_paths: list[Path]) -> set[str]:
        if not source_paths:
            return self.all_supported_targets()

        common: set[str] | None = None
        for source_path in source_paths:
            current = self.supported_targets_for_source(source_path)
            if common is None:
                common = set(current)
            else:
                common &= current
            if not common:
                return set()
        return common or set()

    def find_route(self, source_path: Path, target_format: str, max_hops: int = 2) -> list[str]:
        source_ext = self._source_ext(source_path)
        target = target_format.lower().lstrip(".")
        if not source_ext or not target:
            return []
        if source_ext == target:
            return [source_ext]

        queue: list[str] = [source_ext]
        depth: dict[str, int] = {source_ext: 0}
        parent: dict[str, str] = {}

        while queue:
            current = queue.pop(0)
            current_depth = depth[current]
            if current_depth >= max_hops:
                continue
            for converter in self._converters:
                if current not in converter.supported_inputs:
                    continue
                for nxt in converter.supported_outputs:
                    next_depth = current_depth + 1
                    if next_depth > max_hops:
                        continue
                    if nxt in depth:
                        continue
                    depth[nxt] = next_depth
                    parent[nxt] = current
                    if nxt == target:
                        route = [target]
                        while route[-1] != source_ext:
                            prev = parent.get(route[-1])
                            if not prev:
                                return []
                            route.append(prev)
                        route.reverse()
                        return route
                    queue.append(nxt)
        return []

    def resolve(self, task: ConversionTask) -> Converter:
        plan = self.resolve_plan(task.source_path, task.target_format)
        return plan[0].converter

    def _converter_for_step(self, source_path: Path, target_format: str) -> Converter | None:
        for converter in self._converters:
            if converter.can_handle(source_path, target_format):
                return converter
        return None

    def resolve_plan(self, source_path: Path, target_format: str, max_hops: int = 2) -> list[ConversionStep]:
        target = target_format.lower().lstrip(".")

        direct = self._converter_for_step(source_path, target)
        if direct:
            return [ConversionStep(converter=direct, target_format=target)]

        route = self.find_route(source_path, target, max_hops=max_hops)
        if len(route) < 2:
            source_ext = source_path.suffix.lower().lstrip(".")
            if source_path.is_dir():
                source_ext = "<dir>"
            raise ValueError(f"No converter supports {source_ext} -> {target} (direct or two-step)")

        steps: list[ConversionStep] = []
        current_source = source_path
        for idx, next_format in enumerate(route[1:], start=1):
            converter = self._converter_for_step(current_source, next_format)
            if not converter:
                prev_format = route[idx - 1]
                dummy = Path(f"intermediate.{prev_format}")
                converter = self._converter_for_step(dummy, next_format)
            if not converter:
                raise ValueError(f"No converter found for route step to '{next_format}'")
            steps.append(ConversionStep(converter=converter, target_format=next_format))
            current_source = Path(f"intermediate.{next_format}")
        return steps
