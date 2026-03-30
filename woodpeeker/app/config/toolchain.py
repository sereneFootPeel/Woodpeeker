"""External tool detection and persistence."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict


CONFIG_DIR = Path.home() / ".woodpeeker"
CONFIG_PATH = CONFIG_DIR / "toolchain.json"


def _project_root_candidates() -> list[Path]:
    if getattr(sys, "frozen", False):
        candidates: list[Path] = []
        # PyInstaller onefile: temp extraction dir; onedir: app executable dir.
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(Path(meipass))
        candidates.append(Path(sys.executable).resolve().parent)
        return candidates
    return [Path(__file__).resolve().parents[2]]


def _resolve_embedded_tools_dir() -> Path:
    for root in _project_root_candidates():
        candidate = root / "embedded_tools"
        if candidate.exists():
            return candidate
    # Keep a deterministic fallback when tools are missing.
    return _project_root_candidates()[0] / "embedded_tools"


EMBEDDED_TOOLS_DIR = _resolve_embedded_tools_dir()


@dataclass
class ToolchainConfig:
    ffmpeg: str = ""
    pandoc: str = ""
    libreoffice: str = ""
    calibre: str = ""
    ncmdump: str = ""
    imagemagick: str = ""


def _default_candidates() -> Dict[str, list[str]]:
    return {
        "ffmpeg": ["ffmpeg.exe", "ffmpeg"],
        "pandoc": ["pandoc.exe", "pandoc"],
        "libreoffice": ["soffice.exe", "soffice"],
        "calibre": ["ebook-convert.exe", "ebook-convert"],
        "ncmdump": ["ncmdump.exe", "ncmdump"],
        "imagemagick": ["magick.exe", "magick"],
    }


def _embedded_candidates() -> Dict[str, list[Path]]:
    return {
        "ffmpeg": [EMBEDDED_TOOLS_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"],
        "pandoc": [EMBEDDED_TOOLS_DIR / "pandoc" / "pandoc.exe"],
        "libreoffice": [EMBEDDED_TOOLS_DIR / "libreoffice" / "program" / "soffice.exe"],
        "calibre": [EMBEDDED_TOOLS_DIR / "calibre" / "ebook-convert.exe"],
        "ncmdump": [EMBEDDED_TOOLS_DIR / "ncmdump" / "ncmdump.exe"],
        "imagemagick": [EMBEDDED_TOOLS_DIR / "imagemagick" / "magick.exe"],
    }


def detect_tool(name: str) -> str:
    for candidate in _embedded_candidates().get(name, []):
        if candidate.exists():
            return str(candidate)
    for candidate in _default_candidates().get(name, []):
        path = shutil.which(candidate)
        if path:
            return path
    return ""


def detect_all() -> ToolchainConfig:
    return ToolchainConfig(
        ffmpeg=detect_tool("ffmpeg"),
        pandoc=detect_tool("pandoc"),
        libreoffice=detect_tool("libreoffice"),
        calibre=detect_tool("calibre"),
        ncmdump=detect_tool("ncmdump"),
        imagemagick=detect_tool("imagemagick"),
    )


def load_config() -> ToolchainConfig:
    if not CONFIG_PATH.exists():
        return detect_all()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return detect_all()

    detected = detect_all()
    return ToolchainConfig(
        ffmpeg=data.get("ffmpeg") or detected.ffmpeg,
        pandoc=data.get("pandoc") or detected.pandoc,
        libreoffice=data.get("libreoffice") or detected.libreoffice,
        calibre=data.get("calibre") or detected.calibre,
        ncmdump=data.get("ncmdump") or detected.ncmdump,
        imagemagick=data.get("imagemagick") or detected.imagemagick,
    )


def save_config(config: ToolchainConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(asdict(config), ensure_ascii=True, indent=2), encoding="utf-8"
    )
