import os
import shutil
from pathlib import Path

# ============================================================
#  CONFIGURACIÓN - Cambiá esta ruta a tu carpeta de videos
# ============================================================
CARPETA_VIDEOS = r"C:\Users\esteban\Downloads\Video"
# ============================================================

EXTENSIONES = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg"}

def obtener_artista(nombre_archivo):
    """
    Formato esperado: 'Artista - Canción (Video Oficial).mp4'
    Extrae todo lo que está antes del primer ' - '
    """
    if " - " in nombre_archivo:
        artista = nombre_archivo.split(" - ", 1)[0].strip()
        return artista if artista else "Sin Artista"
    return "Sin Artista"

def mover_sin_sobrescribir(origen, destino):
    """Mueve el archivo, agrega (1)(2)... si ya existe uno igual."""
    if destino.exists():
        contador = 1
        while destino.exists():
            nuevo_nombre = f"{origen.stem} ({contador}){origen.suffix}"
            destino = destino.parent / nuevo_nombre
            contador += 1
    shutil.move(str(origen), str(destino))
    return destino

def eliminar_carpetas_vacias(carpeta_raiz):
    """Borra subcarpetas que quedaron vacías."""
    eliminadas = 0
    for ruta in sorted(Path(carpeta_raiz).rglob("*"), reverse=True):
        if ruta.is_dir() and ruta != Path(carpeta_raiz):
            try:
                ruta.rmdir()
                eliminadas += 1
            except OSError:
                pass
    return eliminadas

def organizar_videos():
    carpeta = Path(CARPETA_VIDEOS)

    if not carpeta.exists():
        print(f"❌ No se encontró la carpeta: {CARPETA_VIDEOS}")
        print("   Revisá la ruta en CARPETA_VIDEOS.")
        input("\nPresioná Enter para cerrar...")
        return

    # Buscar todos los videos en subcarpetas y en la raíz
    print("🔍 Buscando videos en todas las subcarpetas...\n")
    archivos = []
    for ruta in carpeta.rglob("*"):
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES:
            archivos.append(ruta)

    if not archivos:
        print("⚠️  No se encontraron archivos de video.")
        input("\nPresioná Enter para cerrar...")
        return

    print(f"🎬 Se encontraron {len(archivos)} videos. Organizando por artista...\n")

    movidos = 0
    errores = 0
    resumen = {}

    for archivo in archivos:
        artista = obtener_artista(archivo.stem)
        carpeta_artista = carpeta / artista

        # Si ya está en la carpeta correcta, saltar
        if archivo.parent == carpeta_artista:
            resumen.setdefault(artista, []).append(archivo.name)
            continue

        carpeta_artista.mkdir(exist_ok=True)
        destino = carpeta_artista / archivo.name

        try:
            destino_final = mover_sin_sobrescribir(archivo, destino)
            resumen.setdefault(artista, []).append(destino_final.name)
            movidos += 1
            print(f"  ✅ {archivo.name}")
            print(f"      → 📂 {artista}/")
        except Exception as e:
            print(f"  ❌ Error con {archivo.name}: {e}")
            errores += 1

    # Limpiar carpetas vacías
    print("\n🧹 Eliminando carpetas vacías...")
    eliminadas = eliminar_carpetas_vacias(carpeta)

    # Resumen final
    print("\n" + "="*60)
    print(f"  ✅ Videos organizados        : {movidos}")
    print(f"  🗑️  Carpetas vacías eliminadas : {eliminadas}")
    print(f"  ❌ Errores                   : {errores}")
    print("="*60)
    print(f"\n📁 Artistas encontrados ({len(resumen)}):")
    for artista, canciones in sorted(resumen.items()):
        print(f"  📂 {artista}/ → {len(canciones)} canción/es")

    print("\n🎉 ¡Listo! Ya podés copiar todo a tu MP5.")
    input("\nPresioná Enter para cerrar...")

if __name__ == "__main__":
    organizar_videos()