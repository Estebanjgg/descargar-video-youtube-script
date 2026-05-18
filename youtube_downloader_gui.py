import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import yt_dlp


# ── Colores y estilos ──────────────────────────────────────────────────────────
BG        = "#1e1e2e"
BG2       = "#2a2a3e"
ACCENT    = "#7c3aed"
ACCENT_H  = "#6d28d9"
FG        = "#e2e8f0"
FG_DIM    = "#94a3b8"
GREEN     = "#22c55e"
RED       = "#ef4444"
YELLOW    = "#f59e0b"
FONT_MAIN = ("Segoe UI", 10)
FONT_BIG  = ("Segoe UI", 12, "bold")
FONT_MONO = ("Courier New", 9)


class GUILogger:
    """Redirige los mensajes de yt-dlp al widget de log."""

    def __init__(self, widget: scrolledtext.ScrolledText):
        self.widget = widget

    def _append(self, text: str, tag: str = "normal"):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text + "\n", tag)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def debug(self, msg):
        if msg.startswith("[download]"):
            self._append(msg, "progress")
        elif msg.startswith("[info]") or msg.startswith("[youtube]"):
            self._append(msg, "info")
        else:
            self._append(msg, "dim")

    def info(self, msg):
        self._append(msg, "info")

    def warning(self, msg):
        self._append(f"⚠  {msg}", "warning")

    def error(self, msg):
        self._append(f"✗  {msg}", "error")


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Descargador de YouTube")
        self.resizable(True, True)
        self.minsize(680, 560)
        self.configure(bg=BG)

        self._build_ui()
        self._center_window(720, 620)

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=ACCENT, pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text="▶  Descargador de YouTube",
            font=("Segoe UI", 14, "bold"),
            bg=ACCENT, fg="white",
        ).pack()

        # ── Formulario ────────────────────────────────────────────────────────
        form = tk.Frame(self, bg=BG, pady=4)
        form.pack(fill="x", **pad)

        # URL
        tk.Label(form, text="URL del video / playlist:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=0, column=0, sticky="w", pady=(8, 2)
        )
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(
            form, textvariable=self.url_var, font=FONT_MAIN,
            bg=BG2, fg=FG, insertbackground=FG,
            relief="flat", bd=6,
        )
        url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", ipady=5)
        url_entry.bind("<FocusIn>",  lambda e: url_entry.configure(highlightthickness=2, highlightbackground=ACCENT))
        url_entry.bind("<FocusOut>", lambda e: url_entry.configure(highlightthickness=0))
        form.columnconfigure(0, weight=1)

        # Formato
        tk.Label(form, text="Formato:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=2, column=0, sticky="w", pady=(10, 2)
        )
        self.formato_var = tk.StringVar(value="video")
        fmt_frame = tk.Frame(form, bg=BG)
        fmt_frame.grid(row=3, column=0, columnspan=2, sticky="w")

        for label, val in [("🎬  Video MP4 (H.264 + AAC)", "video"), ("🎵  Solo Audio (MP3 192k)", "audio")]:
            tk.Radiobutton(
                fmt_frame, text=label, variable=self.formato_var, value=val,
                font=FONT_MAIN, bg=BG, fg=FG,
                activebackground=BG, activeforeground=ACCENT,
                selectcolor=BG2, relief="flat",
            ).pack(side="left", padx=(0, 20))

        # Carpeta destino
        tk.Label(form, text="Carpeta de destino:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=4, column=0, sticky="w", pady=(10, 2)
        )
        dest_row = tk.Frame(form, bg=BG)
        dest_row.grid(row=5, column=0, columnspan=2, sticky="ew")
        dest_row.columnconfigure(0, weight=1)

        self.carpeta_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "descargas"))
        carpeta_entry = tk.Entry(
            dest_row, textvariable=self.carpeta_var, font=FONT_MAIN,
            bg=BG2, fg=FG, insertbackground=FG, relief="flat", bd=6,
        )
        carpeta_entry.grid(row=0, column=0, sticky="ew", ipady=5)

        tk.Button(
            dest_row, text="📁 Examinar", font=FONT_MAIN,
            bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="white",
            relief="flat", cursor="hand2", padx=8,
            command=self._elegir_carpeta,
        ).grid(row=0, column=1, padx=(6, 0))

        # ── Botón Descargar ───────────────────────────────────────────────────
        self.btn_download = tk.Button(
            self,
            text="⬇  DESCARGAR",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="white",
            activebackground=ACCENT_H, activeforeground="white",
            relief="flat", cursor="hand2",
            pady=10,
            command=self._iniciar_descarga,
        )
        self.btn_download.pack(fill="x", padx=16, pady=(10, 4))

        # ── Barra de progreso ─────────────────────────────────────────────────
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=200)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=BG2, background=ACCENT, thickness=6)
        self.progress.pack(fill="x", padx=16, pady=(0, 4))

        # ── Log ───────────────────────────────────────────────────────────────
        tk.Label(self, text="Registro del proceso:", font=FONT_MAIN, bg=BG, fg=FG_DIM).pack(
            anchor="w", padx=16
        )
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(2, 14))

        self.log = scrolledtext.ScrolledText(
            log_frame,
            font=FONT_MONO,
            bg="#0f0f1a", fg=FG,
            insertbackground=FG,
            relief="flat", bd=0,
            state="disabled",
            wrap="word",
        )
        self.log.pack(fill="both", expand=True)

        # Tags de colores para el log
        self.log.tag_config("info",     foreground=FG)
        self.log.tag_config("progress", foreground=ACCENT)
        self.log.tag_config("dim",      foreground=FG_DIM)
        self.log.tag_config("warning",  foreground=YELLOW)
        self.log.tag_config("error",    foreground=RED)
        self.log.tag_config("success",  foreground=GREEN)
        self.log.tag_config("normal",   foreground=FG)

        # Botón limpiar log
        tk.Button(
            self, text="🗑  Limpiar registro", font=("Segoe UI", 9),
            bg=BG2, fg=FG_DIM, activebackground=BG2, activeforeground=FG,
            relief="flat", cursor="hand2",
            command=self._limpiar_log,
        ).pack(anchor="e", padx=16, pady=(0, 8))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center_window(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if carpeta:
            self.carpeta_var.set(carpeta)

    def _limpiar_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")

    def _log(self, msg: str, tag: str = "normal"):
        self.log.configure(state="normal")
        self.log.insert(tk.END, msg + "\n", tag)
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _set_ui_descargando(self, descargando: bool):
        """Bloquea/desbloquea controles mientras se descarga."""
        state = "disabled" if descargando else "normal"
        self.btn_download.configure(state=state, bg=BG2 if descargando else ACCENT)
        if descargando:
            self.progress.start(12)
        else:
            self.progress.stop()

    # ── Descarga ──────────────────────────────────────────────────────────────

    def _iniciar_descarga(self):
        url     = self.url_var.get().strip()
        carpeta = self.carpeta_var.get().strip() or "descargas"
        formato = self.formato_var.get()

        if not url:
            self._log("⚠  Por favor ingresá una URL.", "warning")
            return

        self._set_ui_descargando(True)
        self._log(f"\n{'─'*60}", "dim")
        self._log(f"🔗  URL     : {url}", "info")
        self._log(f"📁  Carpeta : {carpeta}", "info")
        self._log(f"🎞  Formato : {'Video MP4' if formato == 'video' else 'Audio MP3'}", "info")
        self._log(f"{'─'*60}", "dim")

        hilo = threading.Thread(
            target=self._descargar,
            args=(url, carpeta, formato == "audio"),
            daemon=True,
        )
        hilo.start()

    def _progress_hook(self, d):
        """Hook llamado por yt-dlp en cada actualización de progreso."""
        status = d.get("status")

        if status == "downloading":
            percent   = d.get("_percent_str", "").strip()
            speed     = d.get("_speed_str",   "").strip()
            eta       = d.get("_eta_str",     "").strip()
            filename  = os.path.basename(d.get("filename", ""))
            msg = f"  ⬇  {filename[:55]}  {percent:>7}  vel: {speed}  ETA: {eta}"
            self.log.configure(state="normal")
            # Sobreescribe la última línea de progreso
            last_line_start = self.log.index("end-2l linestart")
            last_line_end   = self.log.index("end-1c")
            last_line       = self.log.get(last_line_start, last_line_end)
            if last_line.startswith("  ⬇ "):
                self.log.delete(last_line_start, last_line_end)
                self.log.insert(last_line_start, msg, "progress")
            else:
                self.log.insert(tk.END, msg + "\n", "progress")
            self.log.see(tk.END)
            self.log.configure(state="disabled")

        elif status == "finished":
            filename = os.path.basename(d.get("filename", "archivo"))
            self._log(f"  ✓  Procesando: {filename}", "success")

        elif status == "error":
            self._log(f"  ✗  Error en descarga", "error")

    def _descargar(self, url: str, carpeta: str, solo_audio: bool):
        os.makedirs(carpeta, exist_ok=True)

        opciones_base = {
            "outtmpl":        os.path.join(carpeta, "%(title).80s.%(ext)s"),
            "ignoreerrors":   True,
            "no_warnings":    False,
            "windowsfilenames": True,
            "logger":         GUILogger(self.log),
            "progress_hooks": [self._progress_hook],
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
                "format": (
                    "bestvideo[vcodec^=avc1][height<=720]+bestaudio[acodec^=mp4a]/"
                    "best[ext=mp4][vcodec^=avc1][acodec^=mp4a]/"
                    "best[ext=mp4]"
                ),
                "merge_output_format": "mp4",
                "postprocessors": [
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4",
                    }
                ],
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
                        self.after(0, lambda: self._log(
                            f"\n✓  Playlist completa: {total} videos descargados en '{carpeta}'",
                            "success",
                        ))
                    else:
                        titulo = info.get("title", "desconocido")
                        self.after(0, lambda t=titulo: self._log(
                            f"\n✓  Descargado: {t}\n   Guardado en: {carpeta}",
                            "success",
                        ))
        except Exception as e:
            self.after(0, lambda: self._log(f"\n✗  Error: {e}", "error"))
        finally:
            self.after(0, lambda: self._set_ui_descargando(False))


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
