# Construir el ejecutable para Windows (.exe)

Este documento explica cómo generar `YouTubeDownloader.exe` a partir de
`youtube_downloader_gui.py`.

---

## 1) Requisitos en la máquina Windows

1. **Python 3.10 o superior** desde <https://www.python.org/downloads/windows/>
   - Durante la instalación, marcá la casilla **“Add Python to PATH”**.
2. **(Recomendado) FFmpeg para Windows** — necesario para convertir a MP3 / MP4.
   - Descargar el zip *“ffmpeg-release-essentials”* desde
     <https://www.gyan.dev/ffmpeg/builds/>.
   - Extraerlo y copiar los dos archivos siguientes a una carpeta llamada
     `bin\` dentro del proyecto:
     - `ffmpeg.exe`
     - `ffprobe.exe`
   - Estructura final esperada:

     ```
     descargar-video-youtube-script\
         bin\
             ffmpeg.exe
             ffprobe.exe
         youtube_downloader_gui.py
         build_windows.bat
         youtube_downloader.spec
     ```

   > Si no agregás `bin\`, el `.exe` igual se construye, pero el usuario final
   > tendrá que tener `ffmpeg` instalado en su PATH para que la conversión
   > funcione.

---

## 2) Pasos para construir el `.exe`

Opción A — **automática** (lo más fácil):

1. Hacé **doble clic** en `build_windows.bat`.
2. Esperá a que termine (la primera vez tarda unos minutos: crea el entorno
   virtual, instala dependencias y empaqueta).
3. Cuando termine vas a ver el ejecutable en:

   ```
   dist\YouTubeDownloader.exe
   ```

Opción B — **manual** (PowerShell o `cmd`):

```bat
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --noconfirm --clean youtube_downloader.spec
```

El resultado queda en `dist\YouTubeDownloader.exe`.

---

## 3) Distribuir el ejecutable

- El archivo `dist\YouTubeDownloader.exe` es **un único archivo** y se puede
  copiar/pegar a cualquier Windows 10/11 (64-bit) sin instalar nada.
- Si NO incluiste `ffmpeg.exe` dentro (paso 1.2), el usuario final deberá tener
  ffmpeg instalado en el `PATH` del sistema; si no, las conversiones a MP4
  re-encodeado y a MP3 fallarán.
- El primer arranque puede tardar 3-5 segundos (PyInstaller descomprime).

---

## 4) Problemas comunes

| Problema | Solución |
|---|---|
| `python` no se reconoce como comando | Reinstalar Python y marcar “Add Python to PATH”. |
| Windows Defender / SmartScreen bloquea el .exe | Es normal en ejecutables sin firma. Clic en **“Más información” → “Ejecutar de todas formas”**. Para distribuir oficialmente, hay que firmar el binario. |
| `Failed to extract audio` / `ffmpeg not found` | Copiar `ffmpeg.exe` y `ffprobe.exe` a `bin\` y volver a construir. |
| El `.exe` pesa mucho (~70-100 MB) | Es esperado: incluye Python + Tcl/Tk + yt-dlp + ffmpeg. |

---

## 5) (Opcional) Ícono personalizado

Si querés un ícono propio:

1. Creá la carpeta `assets\` en la raíz del proyecto.
2. Poné ahí un archivo `icon.ico` (256×256, formato `.ico`).
3. Volvé a construir: el spec lo detecta automáticamente.
