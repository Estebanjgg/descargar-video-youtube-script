@echo off
REM ============================================================================
REM  Build script para generar YouTubeDownloader.exe en Windows.
REM
REM  Requisitos previos (una sola vez):
REM    1) Tener instalado Python 3.10+ desde https://www.python.org/
REM       (marcar "Add Python to PATH" durante la instalacion).
REM    2) (Opcional pero recomendado) Descargar ffmpeg para Windows:
REM         https://www.gyan.dev/ffmpeg/builds/  ->  "ffmpeg-release-essentials.zip"
REM       Extraerlo y copiar ffmpeg.exe y ffprobe.exe a la carpeta bin\
REM       (al lado de este archivo). Asi quedaran dentro del .exe final.
REM
REM  Uso:
REM    Doble clic sobre este archivo  ->  genera  dist\YouTubeDownloader.exe
REM ============================================================================

setlocal
cd /d "%~dp0"

echo.
echo === [1/4] Creando entorno virtual (.venv) si no existe ===
if not exist .venv (
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: no se pudo crear el entorno virtual. ?Esta Python instalado y en el PATH?
        pause
        exit /b 1
    )
)

echo.
echo === [2/4] Activando entorno virtual e instalando dependencias ===
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo.
echo === [3/4] Limpiando build anterior ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo === [4/4] Construyendo ejecutable con PyInstaller ===
pyinstaller --noconfirm --clean youtube_downloader.spec
if errorlevel 1 (
    echo ERROR: PyInstaller fallo.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo  LISTO! El ejecutable esta en:  dist\YouTubeDownloader.exe
echo ============================================================================
echo.
pause
