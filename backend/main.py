"""
Backend FastAPI para el descargador de YouTube.

Endpoints:
    GET  /                       -> health check
    POST /api/info               -> lista videos de una URL (video o playlist)
    POST /api/download           -> descarga un video y lo devuelve como stream

Usa yt-dlp + ffmpeg (debe estar instalado en el sistema).
"""

import os
import re
import shutil
import tempfile
import uuid
from typing import List, Optional

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── Configuración ─────────────────────────────────────────────────────────────

# Orígenes permitidos para CORS (frontend en GitHub Pages + desarrollo local).
# En producción, sobrescribir con la variable de entorno ALLOWED_ORIGINS.
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://estebanjgg.github.io",
]
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", ",".join(_default_origins)).split(",")
    if o.strip()
]

app = FastAPI(title="YouTube Downloader API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Modelos ──────────────────────────────────────────────────────────────────

class InfoRequest(BaseModel):
    url: str


class VideoEntry(BaseModel):
    id: Optional[str] = None
    title: str
    url: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None


class InfoResponse(BaseModel):
    type: str  # "video" | "playlist"
    title: str
    count: int
    entries: List[VideoEntry]


class DownloadRequest(BaseModel):
    url: str
    formato: str = "video"   # "video" | "audio"
    calidad: str = "720"     # "144" | "240" | "360" | "480" | "720" | "1080" | "mp5"
                              # "mp5" = preset compatible reproductores MP5 (H.264 + AAC, 720p 30fps)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalizar_url_playlist(url: str) -> str:
    m = re.search(r"[?&]list=([^&]+)", url)
    if m and not m.group(1).startswith(("RD", "UL", "OL")):
        return f"https://www.youtube.com/playlist?list={m.group(1)}"
    return url


def _safe_filename(name: str) -> str:
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", name or "video")
    return name[:120].strip() or "video"


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "youtube-downloader-api"}


@app.post("/api/info", response_model=InfoResponse)
def info(req: InfoRequest):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="URL vacía")

    url = _normalizar_url_playlist(req.url.strip())

    opts = {
        "quiet":              True,
        "no_warnings":        True,
        "skip_download":      True,
        "ignoreerrors":       True,
        "extract_flat":       "in_playlist",
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo info: {e}")

    if not data:
        raise HTTPException(status_code=404, detail="No se pudo obtener información")

    entries: List[VideoEntry] = []
    raw = data.get("entries")

    if raw is not None:
        for e in list(raw):
            if not e:
                continue
            vid_id = e.get("id")
            u = e.get("url") or e.get("webpage_url")
            if u and not u.startswith("http"):
                u = f"https://www.youtube.com/watch?v={vid_id or u}"
            elif not u and vid_id:
                u = f"https://www.youtube.com/watch?v={vid_id}"
            if not u:
                continue
            entries.append(VideoEntry(
                id=vid_id,
                title=e.get("title") or vid_id or "(sin título)",
                url=u,
                duration=e.get("duration"),
                thumbnail=(e.get("thumbnails") or [{}])[-1].get("url") if e.get("thumbnails") else None,
            ))
        return InfoResponse(
            type="playlist",
            title=data.get("title", "Playlist"),
            count=len(entries),
            entries=entries,
        )

    vid_id = data.get("id")
    entries.append(VideoEntry(
        id=vid_id,
        title=data.get("title") or vid_id or "(sin título)",
        url=data.get("webpage_url") or url,
        duration=data.get("duration"),
        thumbnail=(data.get("thumbnails") or [{}])[-1].get("url") if data.get("thumbnails") else None,
    ))
    return InfoResponse(
        type="video",
        title=data.get("title", "Video"),
        count=1,
        entries=entries,
    )


@app.post("/api/download")
def download(req: DownloadRequest):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="URL vacía")

    solo_audio = req.formato == "audio"
    es_mp5 = (req.calidad or "").lower() == "mp5"
    try:
        calidad = int(req.calidad)
    except ValueError:
        calidad = 720
    if calidad not in (144, 240, 360, 480, 720, 1080):
        calidad = 720

    # Carpeta temporal aislada por descarga
    tmp_dir = tempfile.mkdtemp(prefix="ytdl_")
    out_tmpl = os.path.join(tmp_dir, "%(title).80s.%(ext)s")

    base = {
        "outtmpl":            out_tmpl,
        "ignoreerrors":       False,
        "no_warnings":        True,
        "quiet":              True,
        "noprogress":         True,
        "windowsfilenames":   True,
        "noplaylist":         True,  # backend descarga 1 video por request
        "nocheckcertificate": True,
    }

    if solo_audio:
        opciones = {
            **base,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    elif es_mp5:
        # Preset MP5: H.264 + AAC, máx 1280x720, 30fps, faststart.
        # Idéntico al script original de escritorio para máxima compatibilidad
        # con reproductores MP5 / radios de auto.
        opciones = {
            **base,
            "format": (
                "bestvideo[vcodec^=avc1][height<=720]+bestaudio[acodec^=mp4a]/"
                "best[ext=mp4][vcodec^=avc1][acodec^=mp4a]/"
                "best[ext=mp4]"
            ),
            "merge_output_format": "mp4",
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }],
            "postprocessor_args": [
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-vf", "scale='min(1280,iw)':-2",
                "-r", "30",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-movflags", "+faststart",
            ],
        }
    else:
        opciones = {
            **base,
            "format": (
                f"bestvideo[vcodec^=avc1][height<={calidad}]+bestaudio[acodec^=mp4a]/"
                f"best[ext=mp4][vcodec^=avc1][height<={calidad}]/"
                f"best[ext=mp4][height<={calidad}]/best"
            ),
            "merge_output_format": "mp4",
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }],
            "postprocessor_args": [
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale='min({calidad*16//9},iw)':-2",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-movflags", "+faststart",
            ],
        }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info_dict = ydl.extract_info(req.url.strip(), download=True)
            if not info_dict:
                raise HTTPException(status_code=500, detail="No se pudo descargar")

            # Buscar el archivo generado
            archivos = [f for f in os.listdir(tmp_dir) if os.path.isfile(os.path.join(tmp_dir, f))]
            if not archivos:
                raise HTTPException(status_code=500, detail="Archivo no generado")

            # Priorizar mp4 / mp3 sobre archivos intermedios
            ext_preferida = ".mp3" if solo_audio else ".mp4"
            archivos.sort(key=lambda f: (0 if f.endswith(ext_preferida) else 1, len(f)))
            archivo = archivos[0]
            ruta = os.path.join(tmp_dir, archivo)

            titulo = _safe_filename(info_dict.get("title", "video"))
            nombre_descarga = f"{titulo}{ext_preferida}"

            media_type = "audio/mpeg" if solo_audio else "video/mp4"

            # Limpieza al terminar la respuesta
            def _cleanup():
                shutil.rmtree(tmp_dir, ignore_errors=True)

            response = FileResponse(
                ruta,
                media_type=media_type,
                filename=nombre_descarga,
                background=None,
            )
            # FastAPI ejecutará este callback cuando el cliente termine de leer
            from starlette.background import BackgroundTask
            response.background = BackgroundTask(_cleanup)
            return response

    except yt_dlp.utils.DownloadError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"yt-dlp: {e}")
    except HTTPException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Error: {e}")
