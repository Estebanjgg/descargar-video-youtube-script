import yt_dlp
import os

def download_video(url, carpeta_destino="descargas", solo_audio=False, calidad="best"):
    os.makedirs(carpeta_destino, exist_ok=True)

    opciones_base = {
        "outtmpl": f"{carpeta_destino}/%(title)s.%(ext)s",
        "ignoreerrors": True,        # ← continua mesmo com erros individuais
        "no_warnings": False,
    }

    if solo_audio:
        opciones = {
            **opciones_base,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    else:
        formato = "bestvideo+bestaudio/best" if calidad == "best" else calidad
        opciones = {
            **opciones_base,
            "format": formato,
            "merge_output_format": "mp4",
        }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                # Playlist retorna entries, vídeo único retorna title direto
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
    print("  1. Video (MP4 - mejor calidad)")
    print("  2. Video (720p)")
    print("  3. Solo audio (MP3)")
    opcion = input("Opción (1/2/3): ").strip()

    carpeta = input("Carpeta de destino (Enter = 'descargas'): ").strip() or "descargas"

    if opcion == "1":
        download_video(url, carpeta, solo_audio=False, calidad="best")
    elif opcion == "2":
        download_video(url, carpeta, solo_audio=False, calidad="bestvideo[height<=720]+bestaudio/best")
    elif opcion == "3":
        download_video(url, carpeta, solo_audio=True)
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    menu()