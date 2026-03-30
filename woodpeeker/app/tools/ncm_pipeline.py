"""Decode .ncm and optionally transcode into a target format."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _audio_profile_args(profile: str) -> list[str]:
    if profile == "fast":
        return ["-b:a", "128k"]
    if profile == "quality":
        return ["-b:a", "320k"]
    return ["-b:a", "192k"]


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {}
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs = {
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "startupinfo": startupinfo,
        }
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode ncm and convert to target audio format.")
    parser.add_argument("--ncmdump", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-format", required=True)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    target_format = args.target_format.lower().lstrip(".")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="woodpeeker_ncm_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        decode = _run_command([args.ncmdump, "-o", str(temp_dir), str(source)])
        if decode.returncode != 0:
            if decode.stdout:
                sys.stdout.write(decode.stdout)
            if decode.stderr:
                sys.stderr.write(decode.stderr)
            return decode.returncode

        decoded_files = [
            path
            for path in temp_dir.iterdir()
            if path.is_file() and path.suffix.lower().lstrip(".") != "ncm"
        ]
        if not decoded_files:
            sys.stderr.write("ncmdump succeeded but produced no decoded file.\n")
            return 2
        decoded = max(decoded_files, key=lambda item: item.stat().st_mtime)

        if decoded.suffix.lower().lstrip(".") == target_format:
            shutil.move(str(decoded), str(output))
            if decode.stdout:
                sys.stdout.write(decode.stdout)
            return 0

        convert = _run_command(
            [
                args.ffmpeg,
                "-y",
                "-i",
                str(decoded),
                "-map",
                "0:a:0",
                "-vn",
                *_audio_profile_args(args.profile),
                str(output),
            ]
        )
        if decode.stdout:
            sys.stdout.write(decode.stdout)
        if convert.stdout:
            sys.stdout.write(convert.stdout)
        if convert.stderr:
            sys.stderr.write(convert.stderr)
        return convert.returncode


if __name__ == "__main__":
    raise SystemExit(main())
