"""Convert text/document inputs to ebook outputs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


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
    parser = argparse.ArgumentParser(description="Convert text-like files to epub/mobi/azw3.")
    parser.add_argument("--pandoc", required=True)
    parser.add_argument("--calibre", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-format", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    target_format = args.target_format.lower().lstrip(".")
    output.parent.mkdir(parents=True, exist_ok=True)

    if target_format == "epub":
        to_epub = _run_command([args.pandoc, str(source), "-o", str(output)])
        if to_epub.stdout:
            sys.stdout.write(to_epub.stdout)
        if to_epub.stderr:
            sys.stderr.write(to_epub.stderr)
        return to_epub.returncode

    with tempfile.TemporaryDirectory(prefix="woodpeeker_ebook_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        intermediate_epub = temp_dir / f"{source.stem}.epub"
        to_epub = _run_command([args.pandoc, str(source), "-o", str(intermediate_epub)])
        if to_epub.returncode != 0:
            if to_epub.stdout:
                sys.stdout.write(to_epub.stdout)
            if to_epub.stderr:
                sys.stderr.write(to_epub.stderr)
            return to_epub.returncode

        to_target = _run_command([args.calibre, str(intermediate_epub), str(output)])
        if to_epub.stdout:
            sys.stdout.write(to_epub.stdout)
        if to_target.stdout:
            sys.stdout.write(to_target.stdout)
        if to_target.stderr:
            sys.stderr.write(to_target.stderr)
        return to_target.returncode


if __name__ == "__main__":
    raise SystemExit(main())
