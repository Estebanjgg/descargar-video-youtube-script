# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para construir YouTubeDownloader.exe en Windows.

Uso:
    pyinstaller --noconfirm youtube_downloader.spec

Opcional: si querés incluir ffmpeg.exe dentro del .exe (recomendado para que el
usuario final no tenga que instalarlo), descargá ffmpeg.exe y ffprobe.exe y
ponelos en una carpeta llamada 'bin/' al lado de este archivo. El spec los
detectará automáticamente.
"""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# ── ffmpeg / ffprobe opcionales ───────────────────────────────────────────────
binaries = []
bin_dir = os.path.join(os.path.abspath(os.path.dirname(SPEC)), "bin")
for exe in ("ffmpeg.exe", "ffprobe.exe"):
    ruta = os.path.join(bin_dir, exe)
    if os.path.isfile(ruta):
        # (origen_en_disco, carpeta_destino_dentro_del_exe)
        binaries.append((ruta, "."))

# ── yt-dlp tiene muchos extractors cargados dinámicamente ─────────────────────
hidden = collect_submodules("yt_dlp")

a = Analysis(
    ["youtube_downloader_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="YouTubeDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # False = sin ventana de consola (solo GUI)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join("assets", "icon.ico") if os.path.isfile(os.path.join("assets", "icon.ico")) else None,
)
