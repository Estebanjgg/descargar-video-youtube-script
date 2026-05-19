import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import yt_dlp


# ── Colores y estilos ──────────────────────────────────────────────────────────
BG        = "#1e1e2e"
BG2       = "#2a2a3e"
BG3       = "#0f0f1a"
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


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _clean(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


class GUILogger:
    """Redirige los mensajes de yt-dlp al widget de log."""

    def __init__(self, app: "DownloaderApp"):
        self.app = app

    def debug(self, msg):
        msg = _clean(msg)
        if msg.startswith("[download]"):
            self.app.log_async(msg, "dim")
        elif msg.startswith("[info]") or msg.startswith("[youtube]"):
            self.app.log_async(msg, "info")
        else:
            self.app.log_async(msg, "dim")

    def info(self, msg):
        self.app.log_async(_clean(msg), "info")

    def warning(self, msg):
        self.app.log_async(f"⚠  {_clean(msg)}", "warning")

    def error(self, msg):
        self.app.log_async(f"✗  {_clean(msg)}", "error")


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Descargador de YouTube")
        self.resizable(True, True)
        self.minsize(820, 700)
        self.configure(bg=BG)

        # Estado
        self.playlist_entries = []
        self.check_vars       = []
        self.current_total    = 0
        self.current_index    = 0
        self.cancel_flag      = False

        self._build_ui()
        self._center_window(880, 740)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = tk.Frame(self, bg=ACCENT, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text="▶  Descargador de YouTube",
            font=("Segoe UI", 14, "bold"), bg=ACCENT, fg="white",
        ).pack()

        form = tk.Frame(self, bg=BG)
        form.pack(fill="x", padx=16, pady=(10, 4))

        tk.Label(form, text="URL del video / playlist:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(
            form, textvariable=self.url_var, font=FONT_MAIN,
            bg=BG2, fg=FG, insertbackground=FG, relief="flat", bd=6,
        )
        url_entry.grid(row=1, column=0, sticky="ew", ipady=5)

        self.btn_listar = tk.Button(
            form, text="🔍  Listar playlist", font=FONT_MAIN,
            bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="white",
            relief="flat", cursor="hand2", padx=12,
            command=self._iniciar_listar,
        )
        self.btn_listar.grid(row=1, column=1, padx=(8, 0), sticky="ns")
        form.columnconfigure(0, weight=1)

        tk.Label(form, text="Formato:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=2, column=0, sticky="w", pady=(10, 2)
        )
        self.formato_var = tk.StringVar(value="video")
        fmt_frame = tk.Frame(form, bg=BG)
        fmt_frame.grid(row=3, column=0, columnspan=2, sticky="w")

        for label, val in [("🎬  Video MP4 (H.264 + AAC)", "video"),
                           ("🎵  Solo Audio (MP3 192k)",   "audio")]:
            tk.Radiobutton(
                fmt_frame, text=label, variable=self.formato_var, value=val,
                font=FONT_MAIN, bg=BG, fg=FG,
                activebackground=BG, activeforeground=ACCENT,
                selectcolor=BG2, relief="flat",
            ).pack(side="left", padx=(0, 20))

        tk.Label(form, text="Carpeta de destino:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=4, column=0, sticky="w", pady=(10, 2)
        )
        dest_row = tk.Frame(form, bg=BG)
        dest_row.grid(row=5, column=0, columnspan=2, sticky="ew")
        dest_row.columnconfigure(0, weight=1)

        self.carpeta_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "descargas"))
        tk.Entry(
            dest_row, textvariable=self.carpeta_var, font=FONT_MAIN,
            bg=BG2, fg=FG, insertbackground=FG, relief="flat", bd=6,
        ).grid(row=0, column=0, sticky="ew", ipady=5)

        tk.Button(
            dest_row, text="📁 Examinar", font=FONT_MAIN,
            bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="white",
            relief="flat", cursor="hand2", padx=8,
            command=self._elegir_carpeta,
        ).grid(row=0, column=1, padx=(6, 0))

        # ── Lista de videos ───────────────────────────────────────────────────
        list_header = tk.Frame(self, bg=BG)
        list_header.pack(fill="x", padx=16, pady=(12, 2))

        self.lbl_playlist = tk.Label(
            list_header, text="Videos encontrados: (pegá una URL y hacé clic en 'Listar playlist')",
            font=FONT_MAIN, bg=BG, fg=FG_DIM, anchor="w",
        )
        self.lbl_playlist.pack(side="left", fill="x", expand=True)

        tk.Button(
            list_header, text="☑ Todos", font=("Segoe UI", 9),
            bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="white",
            relief="flat", cursor="hand2", padx=8,
            command=lambda: self._marcar_todos(True),
        ).pack(side="left", padx=(6, 0))

        tk.Button(
            list_header, text="☐ Ninguno", font=("Segoe UI", 9),
            bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="white",
            relief="flat", cursor="hand2", padx=8,
            command=lambda: self._marcar_todos(False),
        ).pack(side="left", padx=(6, 0))

        list_wrapper = tk.Frame(self, bg=BG3, bd=0)
        list_wrapper.pack(fill="both", expand=False, padx=16, pady=(0, 8))

        self.list_canvas = tk.Canvas(
            list_wrapper, bg=BG3, height=180, highlightthickness=0, bd=0,
        )
        scrollbar = ttk.Scrollbar(list_wrapper, orient="vertical", command=self.list_canvas.yview)
        self.list_inner = tk.Frame(self.list_canvas, bg=BG3)

        self.list_inner.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")),
        )
        self.list_canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        self.list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.list_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.list_canvas.bind_all("<Button-4>",   lambda e: self.list_canvas.yview_scroll(-1, "units"))
        self.list_canvas.bind_all("<Button-5>",   lambda e: self.list_canvas.yview_scroll( 1, "units"))

        # ── Botones acción ────────────────────────────────────────────────────
        action_row = tk.Frame(self, bg=BG)
        action_row.pack(fill="x", padx=16, pady=(4, 4))

        self.btn_download = tk.Button(
            action_row, text="⬇  DESCARGAR SELECCIONADOS",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="white",
            activebackground=ACCENT_H, activeforeground="white",
            relief="flat", cursor="hand2", pady=10,
            command=self._iniciar_descarga,
        )
        self.btn_download.pack(side="left", fill="x", expand=True)

        self.btn_cancel = tk.Button(
            action_row, text="✕ Cancelar",
            font=FONT_MAIN, bg=BG2, fg=FG,
            activebackground=RED, activeforeground="white",
            relief="flat", cursor="hand2", padx=14,
            state="disabled",
            command=self._cancelar,
        )
        self.btn_cancel.pack(side="left", padx=(8, 0))

        # ── Estado actual ─────────────────────────────────────────────────────
        status_frame = tk.Frame(self, bg=BG)
        status_frame.pack(fill="x", padx=16, pady=(8, 2))

        self.lbl_status = tk.Label(
            status_frame, text="Listo.", font=FONT_BIG,
            bg=BG, fg=FG, anchor="w",
        )
        self.lbl_status.pack(fill="x")

        self.lbl_status_sub = tk.Label(
            status_frame, text="", font=("Segoe UI", 9),
            bg=BG, fg=FG_DIM, anchor="w",
        )
        self.lbl_status_sub.pack(fill="x")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=BG2, background=ACCENT, thickness=14,
            bordercolor=BG2, lightcolor=ACCENT, darkcolor=ACCENT,
        )

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(
            self, style="Custom.Horizontal.TProgressbar",
            mode="determinate", maximum=100, variable=self.progress_var,
        )
        self.progress.pack(fill="x", padx=16, pady=(2, 4))

        self.lbl_global = tk.Label(
            self, text="", font=("Segoe UI", 9),
            bg=BG, fg=FG_DIM, anchor="w",
        )
        self.lbl_global.pack(fill="x", padx=16)

        # ── Log ───────────────────────────────────────────────────────────────
        tk.Label(self, text="Registro detallado:", font=FONT_MAIN, bg=BG, fg=FG_DIM).pack(
            anchor="w", padx=16, pady=(10, 0)
        )
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(2, 8))

        self.log = scrolledtext.ScrolledText(
            log_frame, font=FONT_MONO, bg=BG3, fg=FG,
            insertbackground=FG, relief="flat", bd=0,
            state="disabled", wrap="word", height=8,
        )
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("info",     foreground=FG)
        self.log.tag_config("progress", foreground=ACCENT)
        self.log.tag_config("dim",      foreground=FG_DIM)
        self.log.tag_config("warning",  foreground=YELLOW)
        self.log.tag_config("error",    foreground=RED)
        self.log.tag_config("success",  foreground=GREEN)
        self.log.tag_config("normal",   foreground=FG)

        tk.Button(
            self, text="🗑  Limpiar registro", font=("Segoe UI", 9),
            bg=BG2, fg=FG_DIM, activebackground=BG2, activeforeground=FG,
            relief="flat", cursor="hand2",
            command=self._limpiar_log,
        ).pack(anchor="e", padx=16, pady=(0, 10))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center_window(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        try:
            self.list_canvas.yview_scroll(delta, "units")
        except tk.TclError:
            pass

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

    def log_async(self, msg: str, tag: str = "normal"):
        self.after(0, lambda: self._log(msg, tag))

    def _set_status(self, main: str, sub: str = ""):
        self.lbl_status.configure(text=main)
        self.lbl_status_sub.configure(text=sub)

    def _set_ui_descargando(self, descargando: bool):
        state_btn = "disabled" if descargando else "normal"
        self.btn_download.configure(state=state_btn, bg=BG2 if descargando else ACCENT)
        self.btn_listar.configure(state=state_btn)
        self.btn_cancel.configure(state="normal" if descargando else "disabled")
        if not descargando:
            self.progress_var.set(0)

    def _marcar_todos(self, valor: bool):
        for v in self.check_vars:
            v.set(valor)

    def _limpiar_lista(self):
        for child in self.list_inner.winfo_children():
            child.destroy()
        self.playlist_entries.clear()
        self.check_vars.clear()

    def _format_dur(self, secs):
        if not secs:
            return ""
        secs = int(secs)
        h, rem = divmod(secs, 3600)
        m, s   = divmod(rem, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def _render_lista(self):
        self._limpiar_lista()

        if not self.playlist_entries:
            self.lbl_playlist.configure(text="No se encontraron videos.", fg=YELLOW)
            return

        self.lbl_playlist.configure(
            text=f"Videos encontrados: {len(self.playlist_entries)}  (marcá los que querés descargar)",
            fg=FG,
        )

        for i, entry in enumerate(self.playlist_entries, start=1):
            var = tk.BooleanVar(value=True)
            self.check_vars.append(var)

            row = tk.Frame(self.list_inner, bg=BG3)
            row.pack(fill="x", padx=8, pady=1)

            dur = self._format_dur(entry.get("duration"))
            titulo = entry.get("title") or entry.get("url") or "(sin título)"
            txt = f"{i:>3}.  {titulo}"
            if dur:
                txt += f"   [{dur}]"

            tk.Checkbutton(
                row, text=txt, variable=var,
                font=FONT_MAIN, bg=BG3, fg=FG,
                activebackground=BG3, activeforeground=ACCENT,
                selectcolor=BG2, anchor="w", relief="flat",
                wraplength=720, justify="left",
            ).pack(fill="x", anchor="w")

    def _cancelar(self):
        self.cancel_flag = True
        self._log("⚠  Cancelando… (terminará el archivo actual)", "warning")

    # ── Listar playlist ───────────────────────────────────────────────────────

    def _iniciar_listar(self):
        url = self.url_var.get().strip()
        if not url:
            self.log_async("⚠  Ingresá una URL primero.", "warning")
            return

        self.btn_listar.configure(state="disabled")
        self.btn_download.configure(state="disabled")
        self._set_status("Obteniendo información…", url)
        self._log(f"\n🔍  Listando: {url}", "info")

        threading.Thread(target=self._listar, args=(url,), daemon=True).start()

    def _listar(self, url: str):
        opts = {
            "quiet":         True,
            "no_warnings":   True,
            "extract_flat":  True,
            "skip_download": True,
            "ignoreerrors":  True,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            entries = []
            if not info:
                pass
            elif "entries" in info:
                for e in info["entries"]:
                    if not e:
                        continue
                    entries.append({
                        "title":    e.get("title"),
                        "url":      e.get("url") or e.get("webpage_url") or e.get("id"),
                        "id":       e.get("id"),
                        "duration": e.get("duration"),
                    })
                titulo_pl = info.get("title", "Playlist")
                self.after(0, lambda: self._set_status(
                    f"Playlist: {titulo_pl}", f"{len(entries)} videos encontrados",
                ))
            else:
                entries.append({
                    "title":    info.get("title"),
                    "url":      info.get("webpage_url") or url,
                    "id":       info.get("id"),
                    "duration": info.get("duration"),
                })
                self.after(0, lambda: self._set_status(
                    "Video individual", info.get("title", ""),
                ))

            self.playlist_entries = entries
            self.after(0, self._render_lista)
            self.after(0, lambda: self._log(
                f"✓  {len(entries)} elemento(s) listados.", "success"
            ))
        except Exception as e:
            self.after(0, lambda: self._log(f"✗  Error al listar: {e}", "error"))
            self.after(0, lambda: self._set_status("Error al listar.", str(e)))
        finally:
            self.after(0, lambda: self.btn_listar.configure(state="normal"))
            self.after(0, lambda: self.btn_download.configure(state="normal"))

    # ── Descarga ──────────────────────────────────────────────────────────────

    def _iniciar_descarga(self):
        url     = self.url_var.get().strip()
        carpeta = self.carpeta_var.get().strip() or "descargas"
        formato = self.formato_var.get()

        if not url and not self.playlist_entries:
            self._log("⚠  Por favor ingresá una URL.", "warning")
            return

        urls_a_descargar = []
        if self.playlist_entries:
            for entry, var in zip(self.playlist_entries, self.check_vars):
                if var.get():
                    u = entry.get("url")
                    if u and not u.startswith("http"):
                        u = f"https://www.youtube.com/watch?v={u}"
                    urls_a_descargar.append((entry.get("title") or u, u))
            if not urls_a_descargar:
                self._log("⚠  No marcaste ningún video.", "warning")
                return
        else:
            urls_a_descargar = [(url, url)]

        self.cancel_flag = False
        self.current_total = len(urls_a_descargar)
        self.current_index = 0

        self._set_ui_descargando(True)
        self.progress_var.set(0)
        self._log(f"\n{'─'*70}", "dim")
        self._log(f"📁  Carpeta : {carpeta}", "info")
        self._log(f"🎞  Formato : {'Video MP4' if formato == 'video' else 'Audio MP3'}", "info")
        self._log(f"📋  Total   : {self.current_total} archivo(s)", "info")
        self._log(f"{'─'*70}", "dim")

        threading.Thread(
            target=self._descargar_lote,
            args=(urls_a_descargar, carpeta, formato == "audio"),
            daemon=True,
        ).start()

    def _progress_hook(self, d):
        status = d.get("status")

        if status == "downloading":
            if self.cancel_flag:
                raise yt_dlp.utils.DownloadError("Cancelado por el usuario.")

            downloaded = d.get("downloaded_bytes") or 0
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percent    = (downloaded / total * 100) if total else 0
            speed      = (d.get("_speed_str") or "").strip()
            eta        = (d.get("_eta_str")   or "").strip()
            filename   = os.path.basename(d.get("filename", ""))

            def _update():
                self.progress_var.set(percent)
                self.lbl_status.configure(text=f"⬇  Descargando: {filename[:70]}")
                self.lbl_status_sub.configure(
                    text=f"{percent:5.1f}%   velocidad: {speed or '—'}   ETA: {eta or '—'}"
                )
                self.lbl_global.configure(
                    text=f"Archivo {self.current_index} de {self.current_total}"
                )
            self.after(0, _update)

        elif status == "finished":
            filename = os.path.basename(d.get("filename", "archivo"))
            self.after(0, lambda: self.progress_var.set(100))
            self.after(0, lambda: self.lbl_status_sub.configure(
                text=f"Procesando (convirtiendo formato)…  {filename[:60]}"
            ))
            self.log_async(f"  ✓  Descarga completa: {filename}", "success")

    def _opciones_ydl(self, carpeta: str, solo_audio: bool):
        base = {
            "outtmpl":          os.path.join(carpeta, "%(title).80s.%(ext)s"),
            "ignoreerrors":     True,
            "no_warnings":      False,
            "windowsfilenames": True,
            "logger":           GUILogger(self),
            "progress_hooks":   [self._progress_hook],
            "noprogress":       True,
        }

        if solo_audio:
            return {
                **base,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        return {
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

    def _descargar_lote(self, items, carpeta: str, solo_audio: bool):
        os.makedirs(carpeta, exist_ok=True)
        opciones = self._opciones_ydl(carpeta, solo_audio)

        exitos = 0
        errores = 0

        for idx, (titulo, url) in enumerate(items, start=1):
            if self.cancel_flag:
                self.log_async("⚠  Descarga cancelada por el usuario.", "warning")
                break

            self.current_index = idx
            self.after(0, lambda t=titulo, i=idx: (
                self.progress_var.set(0),
                self.lbl_status.configure(text=f"⬇  ({i}/{self.current_total}) {t[:65]}"),
                self.lbl_status_sub.configure(text="Conectando…"),
                self.lbl_global.configure(text=f"Archivo {i} de {self.current_total}"),
            ))
            self.log_async(f"\n[{idx}/{self.current_total}] ▶  {titulo}", "info")

            try:
                with yt_dlp.YoutubeDL(opciones) as ydl:
                    ydl.download([url])
                exitos += 1
            except yt_dlp.utils.DownloadError as e:
                if self.cancel_flag:
                    break
                errores += 1
                self.log_async(f"✗  Error con '{titulo}': {e}", "error")
            except Exception as e:
                errores += 1
                self.log_async(f"✗  Error inesperado con '{titulo}': {e}", "error")

        def _finalizar():
            self.progress_var.set(0)
            if self.cancel_flag:
                self._set_status("Cancelado.", f"Descargados {exitos} antes de cancelar.")
            else:
                self._set_status(
                    f"✓ Terminado: {exitos} ok / {errores} errores",
                    f"Guardado en: {carpeta}",
                )
            self.lbl_global.configure(text="")
            self._set_ui_descargando(False)
            self._log(
                f"\n{'═'*70}\n"
                f"  Resultado: {exitos} descargados  |  {errores} con error\n"
                f"  Carpeta: {carpeta}\n"
                f"{'═'*70}",
                "success" if errores == 0 else "warning",
            )

        self.after(0, _finalizar)


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
