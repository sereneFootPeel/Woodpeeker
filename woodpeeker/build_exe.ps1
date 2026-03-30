$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Missing .venv\\Scripts\\python.exe. Create venv and install dependencies first."
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip pyinstaller
& ".venv\Scripts\python.exe" -m pip install -r "requirements.txt"

& ".venv\Scripts\pyinstaller.exe" `
  --noconfirm `
  --clean `
  --windowed `
  --name "Woodpeeker" `
  --paths "." `
  "app/main.py"

# Copy embedded tools as external folder (avoids native DLL conflicts during app startup).
$distTools = Join-Path "dist\Woodpeeker" "embedded_tools"
if (Test-Path $distTools) {
    Remove-Item -Recurse -Force $distTools
}
Copy-Item -Recurse -Force "embedded_tools" $distTools

function Clear-EmbeddedToolsBloat {
    param([string]$Root)

    # --- Helper: remove a list of paths (files or directories) ---
    function Remove-Paths {
        param([string[]]$Paths)
        foreach ($p in $Paths) {
            if (Test-Path $p) {
                Remove-Item -Recurse -Force $p
            }
        }
    }

    # --- FFmpeg: keep only ffmpeg.exe (~201 MB saved by dropping ffplay + ffprobe + docs) ---
    Remove-Paths @(
        (Join-Path $Root "ffmpeg\bin\ffplay.exe"),
        (Join-Path $Root "ffmpeg\bin\ffprobe.exe"),
        (Join-Path $Root "ffmpeg\doc"),
        (Join-Path $Root "ffmpeg\presets")
    )

    # --- Calibre ---
    # Remove executables that are never invoked (only ebook-convert.exe is used).
    $calibreRoot = Join-Path $Root "calibre"
    $calibreKeepExes = @("ebook-convert.exe")
    if (Test-Path $calibreRoot) {
        Get-ChildItem -LiteralPath $calibreRoot -File -Filter "*.exe" -ErrorAction SilentlyContinue |
            Where-Object { $calibreKeepExes -notcontains $_.Name } |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
    # Heavy optional components not needed for headless ebook-convert.
    Remove-Paths @(
        (Join-Path $Root "calibre\app\translations"),
        (Join-Path $Root "calibre\app\resources\qtwebengine_devtools_resources.pak"),
        (Join-Path $Root "calibre\app\bin\opengl32sw.dll")
    )

    # --- LibreOffice: keep only the program/ core + minimal share/ for headless conversion ---
    Remove-Paths @(
        (Join-Path $Root "libreoffice\help"),
        (Join-Path $Root "libreoffice\readmes"),
        (Join-Path $Root "libreoffice\share\gallery"),
        (Join-Path $Root "libreoffice\share\template"),
        (Join-Path $Root "libreoffice\share\wizards"),
        (Join-Path $Root "libreoffice\share\xpdfimport"),
        (Join-Path $Root "libreoffice\share\extensions\dict-en"),
        (Join-Path $Root "libreoffice\share\extensions\dict-es"),
        (Join-Path $Root "libreoffice\share\extensions\dict-fr"),
        (Join-Path $Root "libreoffice\share\extensions\nlpsolver"),
        (Join-Path $Root "libreoffice\share\extensions\wiki-publisher")
    )
    # Remove all icon-theme zip files except the default colibre set.
    $loConfig = Join-Path $Root "libreoffice\share\config"
    if (Test-Path $loConfig) {
        Get-ChildItem -LiteralPath $loConfig -File -Filter "images_*" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notlike "images_colibre.*" } |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }

    # --- Pandoc / ImageMagick: docs ---
    Remove-Paths @(
        (Join-Path $Root "pandoc\MANUAL.html"),
        (Join-Path $Root "imagemagick\ChangeLog.md")
    )

    # --- Global: stray log files ---
    Get-ChildItem -LiteralPath $Root -Recurse -File -Filter "*.log" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

Clear-EmbeddedToolsBloat $distTools

Write-Host ""
Write-Host "Build finished: dist\\Woodpeeker\\Woodpeeker.exe"
