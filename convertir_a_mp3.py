"""Convierte archivos de video o audio a un formato elegido usando ffmpeg.

Al ejecutar el script se abre una interfaz para:
- elegir archivos o una carpeta completa
- seleccionar el formato de salida
- elegir la carpeta donde guardar los convertidos

También mantiene un modo básico de línea de comandos.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path


EXTENSIONES_ACEPTADAS = {
    ".mp4",
    ".m4a",
    ".mpg",
    ".mpeg",
    ".mov",
    ".avi",
    ".wmv",
    ".flv",
    ".mkv",
    ".webm",
}

FORMATOS_SALIDA = {
    "MP3": ".mp3",
    "M4A": ".m4a",
    "WAV": ".wav",
    "OGG": ".ogg",
    "FLAC": ".flac",
}


def convertir_archivo(origen: Path, destino: Path, formato: str, sobrescribir: bool = False) -> bool:
    if destino.exists() and not sobrescribir:
        print(f"[SKIP] Ya existe: {destino.name}")
        return False

    argumentos_audio = []
    formato = formato.upper()
    if formato == "MP3":
        argumentos_audio = ["-c:a", "libmp3lame", "-q:a", "2"]
    elif formato == "M4A":
        argumentos_audio = ["-c:a", "aac", "-b:a", "192k"]
    elif formato == "WAV":
        argumentos_audio = ["-c:a", "pcm_s16le"]
    elif formato == "OGG":
        argumentos_audio = ["-c:a", "libvorbis", "-q:a", "5"]
    elif formato == "FLAC":
        argumentos_audio = ["-c:a", "flac"]
    else:
        argumentos_audio = ["-c:a", "libmp3lame", "-q:a", "2"]

    comando = [
        "ffmpeg",
        "-y" if sobrescribir else "-n",
        "-i",
        str(origen),
        "-vn",
        str(destino),
    ]
    comando[5:5] = argumentos_audio

    resultado = subprocess.run(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if resultado.returncode == 0:
        print(f"[OK] {origen.name} -> {destino.name}")
        return True

    print(f"[ERROR] No se pudo convertir {origen.name}")
    mensaje = resultado.stderr.strip()
    if mensaje:
        print(mensaje.splitlines()[-1])
    return False


def obtener_archivos(carpeta: Path, recursivo: bool) -> list[Path]:
    if recursivo:
        return [
            archivo
            for archivo in carpeta.rglob("*")
            if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_ACEPTADAS
        ]

    return [
        archivo
        for archivo in carpeta.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_ACEPTADAS
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte archivos de video/audio a un formato elegido para reproductores de auto o MP5."
    )
    parser.add_argument(
        "--carpeta",
        default=".",
        help="Carpeta donde buscar archivos. Por defecto usa la carpeta actual.",
    )
    parser.add_argument(
        "--formato",
        default="MP3",
        choices=list(FORMATOS_SALIDA.keys()),
        help="Formato de salida.",
    )
    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Busca archivos en subcarpetas.",
    )
    parser.add_argument(
        "--sobrescribir",
        action="store_true",
        help="Reemplaza el MP3 si ya existe.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    carpeta = Path(args.carpeta).expanduser().resolve()

    if not carpeta.exists() or not carpeta.is_dir():
        print(f"La carpeta no existe o no es válida: {carpeta}")
        return 1

    archivos = obtener_archivos(carpeta, args.recursivo)

    if not archivos:
        print("No se encontraron archivos compatibles para convertir.")
        return 0

    convertidos = 0
    fallidos = 0

    for archivo in archivos:
        destino = archivo.with_suffix(FORMATOS_SALIDA[args.formato])
        if convertir_archivo(archivo, destino, args.formato, sobrescribir=args.sobrescribir):
            convertidos += 1
        else:
            fallidos += 1

    print(f"\nResumen: {convertidos} convertido/s, {fallidos} con error.")
    return 0 if fallidos == 0 else 2


class VentanaConvertidor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Convertidor de música")
        self.geometry("820x560")
        self.minsize(760, 500)

        self.archivos: list[Path] = []
        self.carpeta_salida = tk.StringVar(value=str(Path.cwd()))
        self.formato_salida = tk.StringVar(value="MP3")
        self.recursivo = tk.BooleanVar(value=False)
        self.sobrescribir = tk.BooleanVar(value=False)

        self._construir_ui()

    def _construir_ui(self) -> None:
        contenedor = ttk.Frame(self, padding=16)
        contenedor.pack(fill="both", expand=True)

        titulo = ttk.Label(contenedor, text="Convertidor de música", font=("Segoe UI", 18, "bold"))
        titulo.pack(anchor="w")

        subtitulo = ttk.Label(
            contenedor,
            text="Selecciona archivos, elige formato y define dónde guardarlos.",
        )
        subtitulo.pack(anchor="w", pady=(4, 14))

        acciones = ttk.Frame(contenedor)
        acciones.pack(fill="x", pady=(0, 12))

        ttk.Button(acciones, text="Agregar archivos", command=self.agregar_archivos).pack(side="left")
        ttk.Button(acciones, text="Agregar carpeta", command=self.agregar_carpeta).pack(side="left", padx=8)
        ttk.Button(acciones, text="Quitar seleccionados", command=self.quitar_seleccionados).pack(side="left")
        ttk.Button(acciones, text="Limpiar", command=self.limpiar_lista).pack(side="left", padx=8)

        panel = ttk.Frame(contenedor)
        panel.pack(fill="both", expand=True)

        lista_frame = ttk.Frame(panel)
        lista_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(lista_frame, text="Archivos seleccionados").pack(anchor="w")
        self.lista = tk.Listbox(lista_frame, selectmode=tk.EXTENDED, height=16)
        self.lista.pack(side="left", fill="both", expand=True, pady=(6, 0))

        barra = ttk.Scrollbar(lista_frame, orient="vertical", command=self.lista.yview)
        barra.pack(side="right", fill="y", pady=(6, 0))
        self.lista.config(yscrollcommand=barra.set)

        opciones = ttk.Frame(panel, width=240, padding=(16, 0, 0, 0))
        opciones.pack(side="right", fill="y")
        opciones.pack_propagate(False)

        ttk.Label(opciones, text="Formato de salida").pack(anchor="w")
        combo = ttk.Combobox(opciones, textvariable=self.formato_salida, values=list(FORMATOS_SALIDA.keys()), state="readonly")
        combo.pack(fill="x", pady=(6, 12))

        ttk.Checkbutton(opciones, text="Buscar también en subcarpetas", variable=self.recursivo).pack(anchor="w", pady=(0, 6))
        ttk.Checkbutton(opciones, text="Sobrescribir si ya existe", variable=self.sobrescribir).pack(anchor="w", pady=(0, 12))

        ttk.Label(opciones, text="Carpeta de salida").pack(anchor="w")
        salida_frame = ttk.Frame(opciones)
        salida_frame.pack(fill="x", pady=(6, 12))
        ttk.Entry(salida_frame, textvariable=self.carpeta_salida).pack(side="left", fill="x", expand=True)
        ttk.Button(salida_frame, text="...", width=3, command=self.elegir_carpeta_salida).pack(side="left", padx=(6, 0))

        ttk.Button(opciones, text="Convertir", command=self.iniciar_conversion).pack(fill="x", pady=(6, 8))

        self.progreso = ttk.Progressbar(opciones, mode="determinate")
        self.progreso.pack(fill="x", pady=(0, 8))

        self.estado = ttk.Label(opciones, text="Listo")
        self.estado.pack(anchor="w")

        self.bitacora = tk.Text(contenedor, height=8, wrap="word")
        self.bitacora.pack(fill="both", expand=False, pady=(12, 0))

    def registrar(self, mensaje: str) -> None:
        self.bitacora.insert("end", mensaje + "\n")
        self.bitacora.see("end")

    def agregar_archivos(self) -> None:
        seleccionados = filedialog.askopenfilenames(
            title="Selecciona archivos",
            filetypes=[
                ("Archivos compatibles", "*.mp4 *.m4a *.mpg *.mpeg *.mov *.avi *.wmv *.flv *.mkv *.webm"),
                ("Todos los archivos", "*.*"),
            ],
        )
        self._agregar_paths([Path(archivo) for archivo in seleccionados])

    def agregar_carpeta(self) -> None:
        carpeta = filedialog.askdirectory(title="Selecciona una carpeta")
        if not carpeta:
            return
        base = Path(carpeta)
        archivos = obtener_archivos(base, self.recursivo.get())
        self._agregar_paths(archivos)

    def _agregar_paths(self, paths: list[Path]) -> None:
        agregados = 0
        existentes = {self.lista.get(i) for i in range(self.lista.size())}
        for path in paths:
            texto = str(path)
            if texto not in existentes and path.suffix.lower() in EXTENSIONES_ACEPTADAS:
                self.archivos.append(path)
                self.lista.insert("end", texto)
                existentes.add(texto)
                agregados += 1
        self.estado.config(text=f"{len(self.archivos)} archivo/s en la lista")
        if agregados:
            self.registrar(f"Agregados {agregados} archivo/s")

    def quitar_seleccionados(self) -> None:
        seleccion = list(self.lista.curselection())
        if not seleccion:
            return
        for indice in reversed(seleccion):
            self.lista.delete(indice)
            del self.archivos[indice]
        self.estado.config(text=f"{len(self.archivos)} archivo/s en la lista")

    def limpiar_lista(self) -> None:
        self.archivos.clear()
        self.lista.delete(0, "end")
        self.estado.config(text="Lista vacía")
        self.registrar("Lista limpia")

    def elegir_carpeta_salida(self) -> None:
        carpeta = filedialog.askdirectory(title="Elegir carpeta de salida")
        if carpeta:
            self.carpeta_salida.set(carpeta)

    def iniciar_conversion(self) -> None:
        if not self.archivos:
            messagebox.showwarning("Sin archivos", "Primero agrega uno o más archivos para convertir.")
            return

        carpeta_salida = Path(self.carpeta_salida.get()).expanduser()
        if not carpeta_salida.exists():
            try:
                carpeta_salida.mkdir(parents=True, exist_ok=True)
            except Exception as error:
                messagebox.showerror("Carpeta inválida", f"No se pudo crear la carpeta de salida:\n{error}")
                return

        self.progreso["maximum"] = len(self.archivos)
        self.progreso["value"] = 0
        self.estado.config(text="Convirtiendo...")
        self.registrar("Iniciando conversión...")

        hilo = threading.Thread(
            target=self._convertir_en_segundo_plano,
            args=(carpeta_salida,),
            daemon=True,
        )
        hilo.start()

    def _convertir_en_segundo_plano(self, carpeta_salida: Path) -> None:
        formato = self.formato_salida.get()
        extension = FORMATOS_SALIDA[formato]
        convertidos = 0
        fallidos = 0

        for indice, archivo in enumerate(list(self.archivos), start=1):
            destino = carpeta_salida / archivo.with_suffix(extension).name
            ok = convertir_archivo(archivo, destino, formato, sobrescribir=self.sobrescribir.get())
            if ok:
                convertidos += 1
                self.after(0, self.registrar, f"Convertido: {archivo.name} -> {destino.name}")
            else:
                fallidos += 1
                self.after(0, self.registrar, f"Error: {archivo.name}")

            self.after(0, self._actualizar_progreso, indice, len(self.archivos))

        self.after(0, self._finalizar_conversion, convertidos, fallidos)

    def _actualizar_progreso(self, valor: int, total: int) -> None:
        self.progreso["value"] = valor
        self.estado.config(text=f"{valor}/{total} procesado/s")

    def _finalizar_conversion(self, convertidos: int, fallidos: int) -> None:
        self.estado.config(text=f"Listo: {convertidos} convertidos, {fallidos} con error")
        messagebox.showinfo("Conversión finalizada", f"Convertidos: {convertidos}\nErrores: {fallidos}")


def ejecutar_interfaz() -> None:
    app = VentanaConvertidor()
    app.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(main())
    ejecutar_interfaz()
