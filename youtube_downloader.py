import os

import yt_dlp


def download_video(url, carpeta_destino="descargas", solo_audio=False):
    os.makedirs(carpeta_destino, exist_ok=True)

    opciones_base = {
        "outtmpl": os.path.join(carpeta_destino, "%(title).80s.%(ext)s"),
        "ignoreerrors": True,
        "no_warnings": False,
        "windowsfilenames": True,
        "extractor_args": {"youtube": {"player_client": ["ios", "web"]}},
    }

    if solo_audio:
        opciones = {
            **opciones_base,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        opciones = {
            **opciones_base,

            # Prioriza video H.264 y audio AAC/M4A
            "format": (
                "bestvideo[vcodec^=avc1][height<=720]+bestaudio[acodec^=mp4a]/"
                "best[ext=mp4][vcodec^=avc1][acodec^=mp4a]/"
                "best[ext=mp4]"
            ),

            # Si queda en otro contenedor, intenta dejarlo en mp4
            "merge_output_format": "mp4",

            # Re-encode para máxima compatibilidad con radios genéricas
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],

            # Pasa argumentos a ffmpeg para codec compatible
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

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                if "entries" in info:
                    total = len([e for e in info["entries"] if e])
                    print(f"✓ Playlist concluída: {total} vídeos baixados")
                else:
                    print(f"✓ Descargado: {info.get('title', 'desconocido')}")
    except Exception as e:
        print(f"✗ Erro geral: {e}")


def menu():
    print("\n=== Descargador de YouTube ===")
    url = input("URL del video o playlist: ").strip()

    print("\n¿Qué querés descargar?")
    print("  1. Video compatible para MP5 (MP4 H.264 + AAC)")
    print("  2. Solo audio (MP3)")
    opcion = input("Opción (1/2): ").strip()

    carpeta = input("Carpeta de destino (Enter = 'descargas'): ").strip() or "descargas"

    if opcion == "1":
        download_video(url, carpeta, solo_audio=False)
    elif opcion == "2":
        download_video(url, carpeta, solo_audio=True)
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    menu()