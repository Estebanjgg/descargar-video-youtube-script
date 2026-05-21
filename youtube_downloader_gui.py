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

_DARK_THEME  = {"BG": "#1e1e2e", "BG2": "#2a2a3e", "BG3": "#0f0f1a", "FG": "#e2e8f0", "FG_DIM": "#94a3b8"}
_LIGHT_THEME = {"BG": "#f1f5f9", "BG2": "#e2e8f0", "BG3": "#ffffff", "FG": "#1e293b", "FG_DIM": "#64748b"}

# MB estimados por minuto de video según resolución (re-encoded H.264 CRF23 + AAC 128k)
_MB_PER_MIN = {"144p": 2.0, "360p": 5.0, "480p": 8.0, "720p": 15.0, "audio": 1.5}


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
        self.theme_name       = "dark"
        self._colors          = _DARK_THEME.copy()

        self._build_ui()
        self._center_window(880, 740)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = tk.Frame(self, bg=ACCENT, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text="▶  Descargador de YouTube",
            font=("Segoe UI", 14, "bold"), bg=ACCENT, fg="white",
        ).pack(side="left", padx=16, fill="x", expand=True)
        self.btn_theme = tk.Button(
            header, text="☀  Claro", font=("Segoe UI", 9),
            bg=ACCENT_H, fg="white",
            activebackground=ACCENT_H, activeforeground="white",
            relief="flat", cursor="hand2", padx=10,
            command=self._toggle_theme,
        )
        self.btn_theme.pack(side="right", padx=12)

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

        tk.Label(form, text="Resolución (solo video):", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=4, column=0, sticky="w", pady=(10, 2)
        )
        self.resolucion_var = tk.StringVar(value="720p")
        res_frame = tk.Frame(form, bg=BG)
        res_frame.grid(row=5, column=0, columnspan=2, sticky="w")

        for label, val in [("144p", "144p"), ("360p", "360p"), ("480p", "480p"), ("720p", "720p")]:
            tk.Radiobutton(
                res_frame, text=label, variable=self.resolucion_var, value=val,
                font=FONT_MAIN, bg=BG, fg=FG,
                activebackground=BG, activeforeground=ACCENT,
                selectcolor=BG2, relief="flat",
            ).pack(side="left", padx=(0, 12))

        tk.Label(form, text="Carpeta de destino:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=6, column=0, sticky="w", pady=(10, 2)
        )
        dest_row = tk.Frame(form, bg=BG)
        dest_row.grid(row=7, column=0, columnspan=2, sticky="ew")
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
        tk.Label(form, text="🍪  Cookies del navegador:", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=8, column=0, sticky="w", pady=(10, 2)
        )
        cookies_frame = tk.Frame(form, bg=BG)
        cookies_frame.grid(row=9, column=0, columnspan=2, sticky="w")

        self.browser_var = tk.StringVar(value="none")
        for lbl, val in [("Ninguno", "none"), ("Chrome", "chrome"), ("Firefox", "firefox"),
                         ("Safari", "safari"), ("Brave", "brave"), ("Edge", "edge")]:
            tk.Radiobutton(
                cookies_frame, text=lbl, variable=self.browser_var, value=val,
                font=FONT_MAIN, bg=BG, fg=FG,
                activebackground=BG, activeforeground=ACCENT,
                selectcolor=BG2, relief="flat",
            ).pack(side="left", padx=(0, 8))
        tk.Label(
            cookies_frame, text="  (cerrá el navegador antes)",
            font=("Segoe UI", 9), bg=BG, fg=FG_DIM,
        ).pack(side="left")

        tk.Label(form, text="📄  Archivo cookies.txt (opcional, más confiable):", font=FONT_MAIN, bg=BG, fg=FG).grid(
            row=10, column=0, sticky="w", pady=(10, 2)
        )
        cookies_file_row = tk.Frame(form, bg=BG)
        cookies_file_row.grid(row=11, column=0, columnspan=2, sticky="ew")
        cookies_file_row.columnconfigure(0, weight=1)

        self.cookies_file_var = tk.StringVar(value="")
        tk.Entry(
            cookies_file_row, textvariable=self.cookies_file_var, font=FONT_MAIN,
            bg=BG2, fg=FG, insertbackground=FG, relief="flat", bd=6,
        ).grid(row=0, column=0, sticky="ew", ipady=5)

        tk.Button(
            cookies_file_row, text="📁 Elegir", font=FONT_MAIN,
            bg=BG2, fg=FG, activebackground=ACCENT, activeforeground="white",
            relief="flat", cursor="hand2", padx=8,
            command=self._elegir_cookies_file,
        ).grid(row=0, column=1, padx=(6, 0))
        tk.Button(
            cookies_file_row, text="✕", font=FONT_MAIN,
            bg=BG2, fg=FG_DIM, activebackground=RED, activeforeground="white",
            relief="flat", cursor="hand2", padx=6,
            command=lambda: self.cookies_file_var.set(""),
        ).grid(row=0, column=2, padx=(4, 0))
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
        # ── Resumen estimado ─────────────────────────────────────────────────────────────────────────────
        self.lbl_resumen = tk.Label(
            self, text="", font=("Segoe UI", 9, "bold"),
            bg=BG, fg=FG_DIM, anchor="w",
        )
        self.lbl_resumen.pack(fill="x", padx=16, pady=(2, 4))
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
        # Actualizar resumen cuando cambia formato o resolución
        self.formato_var.trace_add("write",    lambda *_: self.after(0, self._actualizar_resumen))
        self.resolucion_var.trace_add("write", lambda *_: self.after(0, self._actualizar_resumen))
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

    def _elegir_cookies_file(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo cookies.txt",
            filetypes=[("Cookies file", "*.txt"), ("Todos los archivos", "*.*")],
        )
        if archivo:
            self.cookies_file_var.set(archivo)

    def _limpiar_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")

    def _toggle_theme(self):
        old = _DARK_THEME  if self.theme_name == "dark"  else _LIGHT_THEME
        new = _LIGHT_THEME if self.theme_name == "dark"  else _DARK_THEME
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self._colors = new.copy()

        color_map = {old[k]: new[k] for k in old}
        self._remap_widget(self, color_map)

        # Actualizar tags del log que usan FG / FG_DIM
        self.log.tag_config("info",   foreground=new["FG"])
        self.log.tag_config("normal", foreground=new["FG"])
        self.log.tag_config("dim",    foreground=new["FG_DIM"])

        # Actualizar estilo ttk de la barra de progreso
        ttk.Style(self).configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=new["BG2"],
            bordercolor=new["BG2"],
        )

        self.btn_theme.configure(
            text="🌙  Oscuro" if self.theme_name == "light" else "☀  Claro"
        )

    def _remap_widget(self, widget, color_map):
        """Recorre el árbol de widgets actualizando colores según color_map."""
        for opt in ("background", "foreground", "selectcolor",
                    "activebackground", "activeforeground",
                    "insertbackground", "highlightbackground"):
            try:
                current = widget.cget(opt)
                if current in color_map:
                    widget.configure(**{opt: color_map[current]})
            except tk.TclError:
                pass
        for child in widget.winfo_children():
            self._remap_widget(child, color_map)

    def _actualizar_resumen(self):
        if not self.playlist_entries or not self.check_vars:
            self.lbl_resumen.configure(text="")
            return

        seleccionados = [
            entry for entry, var in zip(self.playlist_entries, self.check_vars)
            if var.get()
        ]
        n = len(seleccionados)

        if n == 0:
            self.lbl_resumen.configure(text="⚠  Ningún video seleccionado.")
            return

        total_secs = sum(e.get("duration") or 0 for e in seleccionados)
        total_min  = total_secs / 60

        if self.formato_var.get() == "audio":
            mb_por_min = _MB_PER_MIN["audio"]
        else:
            mb_por_min = _MB_PER_MIN.get(self.resolucion_var.get(), 15.0)

        mb_est = total_min * mb_por_min
        size_str = f"~{mb_est / 1024:.2f} GB" if mb_est >= 1024 else f"~{mb_est:.0f} MB"

        h, rem  = divmod(int(total_secs), 3600)
        m, s    = divmod(rem, 60)
        dur_str = f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"

        has_unknown = any(not e.get("duration") for e in seleccionados)
        nota = "  (estimado¹)" if has_unknown else "  (estimado)"

        self.lbl_resumen.configure(
            text=f"📊  {n} video(s) seleccionado(s)  ·  duración: {dur_str}  ·  tamaño aprox.: {size_str}{nota}"
        )

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
        """Limpia sólo los widgets visuales (NO la lista de datos)."""
        for child in self.list_inner.winfo_children():
            child.destroy()
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
        c = self._colors  # colores del tema activo

        if not self.playlist_entries:
            self.lbl_playlist.configure(text="No se encontraron videos.", fg=YELLOW)
            return

        self.lbl_playlist.configure(
            text=f"Videos encontrados: {len(self.playlist_entries)}  (marcá los que querés descargar)",
            fg=c["FG"],
        )

        for i, entry in enumerate(self.playlist_entries, start=1):
            var = tk.BooleanVar(value=True)
            var.trace_add("write", lambda *_: self.after(0, self._actualizar_resumen))
            self.check_vars.append(var)

            row = tk.Frame(self.list_inner, bg=c["BG3"])
            row.pack(fill="x", padx=8, pady=1)

            dur = self._format_dur(entry.get("duration"))
            titulo = entry.get("title") or entry.get("url") or "(sin título)"
            txt = f"{i:>3}.  {titulo}"
            if dur:
                txt += f"   [{dur}]"

            tk.Checkbutton(
                row, text=txt, variable=var,
                font=FONT_MAIN, bg=c["BG3"], fg=c["FG"],
                activebackground=c["BG3"], activeforeground=ACCENT,
                selectcolor=c["BG2"], anchor="w", relief="flat",
                wraplength=720, justify="left",
            ).pack(fill="x", anchor="w")

        self.after(0, self._actualizar_resumen)

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

    def _extraer_entries(self, url: str, flat: bool):
        """Extrae la información de la URL. Devuelve (info_dict, entries_list)."""
        opts = {
            "quiet":         True,
            "no_warnings":   True,
            "skip_download": True,
            "ignoreerrors":  True,
            "retries":                 5,
            "sleep_interval_requests": 2,
        }
        if flat:
            opts["extract_flat"] = "in_playlist"

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = []
        if not info:
            return info, entries

        raw_entries = info.get("entries")

        # entries puede ser un generador en algunas versiones
        if raw_entries is not None:
            raw_list = list(raw_entries)
            self.log_async(f"   yt-dlp devolvió {len(raw_list)} entradas crudas", "dim")

            for e in raw_list:
                if not e:
                    continue
                vid_id = e.get("id")
                u = e.get("url") or e.get("webpage_url")
                if u and not u.startswith("http"):
                    # url puede venir como ID o como path
                    if "watch?v=" in u:
                        pass
                    elif vid_id:
                        u = f"https://www.youtube.com/watch?v={vid_id}"
                    else:
                        u = f"https://www.youtube.com/watch?v={u}"
                elif not u and vid_id:
                    u = f"https://www.youtube.com/watch?v={vid_id}"

                # Si no hay ni id ni url, lo descartamos
                if not u and not vid_id:
                    continue

                entries.append({
                    "title":    e.get("title") or e.get("fulltitle") or vid_id or "(sin título)",
                    "url":      u or f"https://www.youtube.com/watch?v={vid_id}",
                    "id":       vid_id,
                    "duration": e.get("duration"),
                })
        else:
            vid_id = info.get("id")
            entries.append({
                "title":    info.get("title") or vid_id or "(sin título)",
                "url":      info.get("webpage_url") or url,
                "id":       vid_id,
                "duration": info.get("duration"),
            })
        return info, entries

    def _normalizar_url_playlist(self, url: str) -> str:
        """Si la URL tiene list=XXX, devuelve la URL canónica de la playlist."""
        m = re.search(r"[?&]list=([^&]+)", url)
        if m:
            list_id = m.group(1)
            if list_id.startswith(("RD", "UL", "OL")):
                # Mix / Radio: hay que mantener el video v= para que YouTube
                # genere la mezcla. Devolvemos la URL tal cual.
                return url
            return f"https://www.youtube.com/playlist?list={list_id}"
        return url

    def _listar(self, url: str):
        try:
            url_pl = self._normalizar_url_playlist(url)
            if url_pl != url:
                self.log_async(f"   usando URL de playlist: {url_pl}", "dim")

            self.log_async("   intentando extracción rápida (flat)…", "dim")
            info, entries = self._extraer_entries(url_pl, flat=True)

            es_playlist = bool(info and (
                info.get("_type") in ("playlist", "multi_video")
                or "entries" in info
            ))

            # Fallback 1: playlist sin entries -> reintentar sin flat
            if es_playlist and not entries:
                self.log_async(
                    "   la extracción rápida no devolvió videos; "
                    "reintentando con extracción completa (más lenta)…",
                    "warning",
                )
                info, entries = self._extraer_entries(url_pl, flat=False)

            # Detectar Mix de YouTube y avisar limitación
            list_id = ""
            m = re.search(r"[?&]list=([^&]+)", url)
            if m:
                list_id = m.group(1)
            if list_id.startswith("RD"):
                self.log_async(
                    "ℹ  Detectado un Mix/Radio de YouTube (lista RD…). "
                    "Estos son generados dinámicamente y suelen mostrar "
                    "sólo unos pocos videos al inicio.",
                    "warning",
                )

            if info and es_playlist:
                titulo_pl = info.get("title", "Playlist")
                count = len(entries)
                self.after(0, lambda t=titulo_pl, c=count: self._set_status(
                    f"Playlist: {t}", f"{c} videos listados",
                ))
            elif entries:
                titulo_v = entries[0].get("title", "")
                self.after(0, lambda t=titulo_v: self._set_status("Video individual", t))
            else:
                self.after(0, lambda: self._set_status("Sin resultados.", ""))

            self.playlist_entries = entries
            self.after(0, self._render_lista)
            count_final = len(entries)
            self.after(0, lambda c=count_final: self._log(
                f"✓  {c} elemento(s) listados.",
                "success" if c > 0 else "warning",
            ))

            if count_final == 0:
                self.after(0, lambda: self._log(
                    "ℹ  Sugerencia: si es un Mix (RD…), probá copiando la URL "
                    "de una playlist creada por usuario (empieza con PL…), "
                    "o pegá el link directo del video que querés.",
                    "dim",
                ))
        except Exception as e:
            self.after(0, lambda err=e: self._log(f"✗  Error al listar: {err}", "error"))
            self.after(0, lambda err=e: self._set_status("Error al listar.", str(err)))
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
        resolucion   = self.resolucion_var.get()
        browser      = self.browser_var.get()
        cookies_file = self.cookies_file_var.get().strip()
        fmt_label = f"Video MP4 ({resolucion})" if formato == "video" else "Audio MP3"
        self._log(f"🎞  Formato : {fmt_label}", "info")
        if cookies_file:
            self._log(f"📄  Cookies : {os.path.basename(cookies_file)}", "info")
        elif browser != "none":
            self._log(f"🍪  Cookies : {browser}", "info")
        self._log(f"📋  Total   : {self.current_total} archivo(s)", "info")
        self._log(f"{'─'*70}", "dim")

        threading.Thread(
            target=self._descargar_lote,
            args=(urls_a_descargar, carpeta, formato == "audio", resolucion, browser),
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

    _RES_MAP = {
        "144p": (144,  256),
        "360p": (360,  640),
        "480p": (480,  854),
        "720p": (720, 1280),
    }

    def _opciones_ydl(self, carpeta: str, solo_audio: bool, resolucion: str = "720p", browser: str = "none", cookies_file: str = ""):
        height, width = self._RES_MAP.get(resolucion, (720, 1280))
        base = {
            "outtmpl":          os.path.join(carpeta, "%(title).80s.%(ext)s"),
            "ignoreerrors":     True,
            "no_warnings":      False,
            "windowsfilenames": True,
            "logger":           GUILogger(self),
            "progress_hooks":   [self._progress_hook],
            "noprogress":       True,
            "retries":                  10,
            "fragment_retries":         10,
            "sleep_interval":            3,
            "max_sleep_interval":        6,
            "sleep_interval_requests":   2,
        }
        if cookies_file and os.path.isfile(cookies_file):
            base["cookiefile"] = cookies_file
        elif browser != "none":
            base["cookiesfrombrowser"] = (browser,)

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
                f"bestvideo[vcodec^=avc1][height<={height}]+bestaudio[acodec^=mp4a]/"
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
                "-vf", f"scale='min({width},iw)':-2",
                "-r", "30",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-movflags", "+faststart",
            ],
        }

    def _descargar_lote(self, items, carpeta: str, solo_audio: bool, resolucion: str = "720p", browser: str = "none", cookies_file: str = ""):
        os.makedirs(carpeta, exist_ok=True)
        opciones = self._opciones_ydl(carpeta, solo_audio, resolucion, browser, cookies_file)

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
                    ret = ydl.download([url])
                if ret == 0:
                    exitos += 1
                else:
                    errores += 1
                    self.log_async(f"✗  Falló la descarga de '{titulo}'", "error")
            except yt_dlp.utils.DownloadError as e:
                err_str = str(e)
                if self.cancel_flag:
                    break
                # Si falló por cookies, reintentar sin ellas
                if "cookiesfrombrowser" in opciones and (
                    "failed to load cookies" in err_str.lower()
                    or "could not copy" in err_str.lower()
                    or "cookie" in err_str.lower()
                ):
                    self.log_async("⚠  Error al leer cookies del navegador — reintentando sin cookies…", "warning")
                    opts_sin_cookies = {k: v for k, v in opciones.items() if k != "cookiesfrombrowser"}
                    try:
                        with yt_dlp.YoutubeDL(opts_sin_cookies) as ydl:
                            ret = ydl.download([url])
                        if ret == 0:
                            exitos += 1
                            continue
                    except Exception:
                        pass
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
