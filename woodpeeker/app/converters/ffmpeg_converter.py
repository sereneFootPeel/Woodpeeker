"""Audio and video conversion via FFmpeg."""

from __future__ import annotations

from app.config.toolchain import ToolchainConfig
from app.converters.base import Converter, extension_set
from app.core.models import ConversionTask


class FFmpegConverter(Converter):
    _AUDIO_FORMATS = extension_set(["mp3", "wav", "flac", "aac", "ogg", "m4a"])
    _VIDEO_FORMATS = extension_set(["mp4", "mkv", "avi", "mov", "webm"])

    def __init__(self, config: ToolchainConfig) -> None:
        self._ffmpeg = config.ffmpeg or "ffmpeg"

    @property
    def supported_inputs(self) -> set[str]:
        return self._AUDIO_FORMATS | self._VIDEO_FORMATS

    @property
    def supported_outputs(self) -> set[str]:
        return self.supported_inputs

    def build_command(self, task: ConversionTask) -> list[str]:
        output = self.build_output_path(task)
        target_ext = task.target_format.lower()
        target_is_video = target_ext in self._VIDEO_FORMATS
        target_is_audio = target_ext in self._AUDIO_FORMATS

        command = [
            self._ffmpeg,
            "-y",
            "-i",
            str(task.source_path),
        ]

        # Video conversion defaults: use H.264 + AAC for broad compatibility.
        if target_is_video:
            command += self._video_args(task.profile, target_ext)
        elif target_is_audio:
            command += self._audio_args(task.profile)

        command.append(str(output))
        return command

    def _video_args(self, profile: str, target_ext: str) -> list[str]:
        args: list[str] = []
        if target_ext == "webm":
            args += ["-c:v", "libvpx-vp9", "-c:a", "libopus"]
            if profile == "fast":
                args += ["-deadline", "realtime", "-cpu-used", "5"]
            elif profile == "quality":
                args += ["-b:v", "0", "-crf", "30"]
            else:
                args += ["-b:v", "0", "-crf", "34"]
            return args

        args += ["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"]
        if profile == "fast":
            args += ["-preset", "veryfast", "-crf", "25"]
        elif profile == "quality":
            args += ["-preset", "slow", "-crf", "18"]
        else:
            args += ["-preset", "medium", "-crf", "22"]
        return args

    def _audio_args(self, profile: str) -> list[str]:
        # Always force audio-only output to avoid attached-picture streams
        # being auto-mapped as video (e.g. FLAC cover art to M4A).
        args: list[str] = ["-map", "0:a:0", "-vn"]
        if profile == "fast":
            args += ["-b:a", "128k"]
        elif profile == "quality":
            args += ["-b:a", "320k"]
        else:
            args += ["-b:a", "192k"]
        return args
