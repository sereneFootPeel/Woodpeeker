"""Application entry point for the converter GUI."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _dispatch_embedded_module_cli() -> int | None:
    """Emulate `python -m ...` when running from frozen executable."""
    argv = sys.argv
    if len(argv) < 3 or argv[1] != "-m":
        return None

    module = argv[2]
    forwarded = [argv[0], *argv[3:]]
    if module == "app.tools.ncm_pipeline":
        from app.tools.ncm_pipeline import main as pipeline_main

        sys.argv = forwarded
        return pipeline_main()
    if module == "app.tools.text_ebook_pipeline":
        from app.tools.text_ebook_pipeline import main as pipeline_main

        sys.argv = forwarded
        return pipeline_main()
    return None


def run() -> int:
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Woodpeeker")
    app.setOrganizationName("Woodpeeker")
    window = MainWindow()
    window.show()
    return app.exec()


def _write_startup_error_log(detail: str) -> Path:
    log_dir = Path.home() / ".woodpeeker"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "startup_error.log"
    log_path.write_text(detail, encoding="utf-8")
    return log_path


def main() -> int:
    try:
        dispatched = _dispatch_embedded_module_cli()
        if dispatched is not None:
            return dispatched
        return run()
    except Exception:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWidgets import QMessageBox

        detail = traceback.format_exc()
        log_path = _write_startup_error_log(detail)
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Woodpeeker failed to start",
                (
                    "Startup failed. Error details were written to:\n"
                    f"{log_path}"
                ),
            )
        except Exception:
            # If UI reporting fails, keep the original startup failure visible in log file.
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
