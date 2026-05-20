"use client";

import { useMemo, useState } from "react";
import {
  downloadVideo,
  fetchInfo,
  triggerBrowserDownload,
  type VideoEntry,
} from "@/lib/api";
import styles from "./page.module.css";

type Formato = "video" | "audio";
type LogTag = "info" | "success" | "error" | "warning" | "dim";

const CALIDADES: { value: string; label: string }[] = [
  { value: "144",  label: "144p" },
  { value: "240",  label: "240p" },
  { value: "360",  label: "360p" },
  { value: "480",  label: "480p" },
  { value: "720",  label: "720p" },
  { value: "1080", label: "1080p" },
  { value: "mp5",  label: "📼 MP5 (720p 30fps H.264+AAC)" },
];

function formatDur(secs: number | null): string {
  if (!secs) return "";
  const s = Math.floor(secs);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return h
    ? `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`
    : `${m}:${String(r).padStart(2, "0")}`;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [formato, setFormato] = useState<Formato>("video");
  const [calidad, setCalidad] = useState<string>("720");

  const [entries, setEntries] = useState<VideoEntry[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [playlistTitle, setPlaylistTitle] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const [currentIdx, setCurrentIdx] = useState(0);
  const [currentTotal, setCurrentTotal] = useState(0);
  const [currentTitle, setCurrentTitle] = useState<string>("");
  const [progress, setProgress] = useState(0);   // 0-100
  const [downloadedBytes, setDownloadedBytes] = useState(0);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const [logs, setLogs] = useState<{ msg: string; tag: LogTag }[]>([]);
  const [cancelToken, setCancelToken] = useState<AbortController | null>(null);

  const log = (msg: string, tag: LogTag = "info") =>
    setLogs((prev) => [...prev, { msg, tag }]);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const toggleAll = (value: boolean) => {
    setSelected(value ? new Set(entries.map((_, i) => i)) : new Set());
  };

  const toggleOne = (i: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  const handleListar = async () => {
    if (!url.trim()) {
      log("⚠ Ingresá una URL primero.", "warning");
      return;
    }
    setLoading(true);
    setEntries([]);
    setSelected(new Set());
    setPlaylistTitle("");
    log(`🔍 Listando: ${url}`, "info");
    try {
      const info = await fetchInfo(url.trim());
      setEntries(info.entries);
      setSelected(new Set(info.entries.map((_, i) => i)));
      setPlaylistTitle(
        info.type === "playlist"
          ? `Playlist: ${info.title} (${info.count} videos)`
          : `Video: ${info.title}`,
      );
      log(`✓ ${info.count} elemento(s) listados.`, "success");
    } catch (e: any) {
      log(`✗ Error: ${e?.message || e}`, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDescargar = async () => {
    const items =
      entries.length > 0
        ? [...selected].sort((a, b) => a - b).map((i) => entries[i])
        : url.trim()
        ? [{ id: null, title: url.trim(), url: url.trim(), duration: null, thumbnail: null } as VideoEntry]
        : [];

    if (items.length === 0) {
      log("⚠ Seleccioná al menos un video (o pegá una URL).", "warning");
      return;
    }

    setDownloading(true);
    setCurrentTotal(items.length);
    log("─".repeat(50), "dim");
    log(`📋 Iniciando ${items.length} descarga(s)`, "info");
    log(`🎞 Formato: ${formato === "video" ? (calidad === "mp5" ? "Video MP4 — preset MP5 (720p)" : `Video MP4 ${calidad}p`) : "Audio MP3"}`, "info");
    log("─".repeat(50), "dim");

    const ac = new AbortController();
    setCancelToken(ac);

    let ok = 0;
    let err = 0;

    for (let i = 0; i < items.length; i++) {
      if (ac.signal.aborted) break;
      const item = items[i];
      setCurrentIdx(i + 1);
      setCurrentTitle(item.title);
      setProgress(0);
      setDownloadedBytes(0);
      setTotalBytes(null);
      log(`\n[${i + 1}/${items.length}] ▶ ${item.title}`, "info");
      try {
        const { blob, filename } = await downloadVideo(
          { url: item.url, formato, calidad },
          (received, total) => {
            setDownloadedBytes(received);
            setTotalBytes(total);
            if (total) setProgress((received / total) * 100);
          },
          ac.signal,
        );
        triggerBrowserDownload(blob, filename);
        log(`  ✓ Descargado: ${filename}`, "success");
        ok++;
      } catch (e: any) {
        if (ac.signal.aborted) {
          log("⚠ Descarga cancelada por el usuario.", "warning");
          break;
        }
        log(`  ✗ Error: ${e?.message || e}`, "error");
        err++;
      }
    }

    setDownloading(false);
    setCancelToken(null);
    setProgress(0);
    setCurrentTitle("");
    log(`\n${"═".repeat(50)}`, "dim");
    log(`Resultado: ${ok} ok / ${err} con error`, err === 0 ? "success" : "warning");
    log("═".repeat(50), "dim");
  };

  const handleCancelar = () => {
    if (cancelToken) {
      cancelToken.abort();
      log("⚠ Cancelando…", "warning");
    }
  };

  const selectedCount = selected.size;

  const progressLabel = useMemo(() => {
    if (!downloading) return "";
    const pct = progress.toFixed(1);
    const bytes = totalBytes
      ? `${formatBytes(downloadedBytes)} / ${formatBytes(totalBytes)}`
      : `${formatBytes(downloadedBytes)} (tamaño desconocido)`;
    return `${pct}%  ·  ${bytes}`;
  }, [downloading, progress, downloadedBytes, totalBytes]);

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1>▶ Descargador de YouTube</h1>
      </header>

      <section className={styles.card}>
        <label className={styles.label}>URL del video / playlist</label>
        <div className={styles.row}>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=…"
            className={styles.urlInput}
            disabled={loading || downloading}
          />
          <button
            onClick={handleListar}
            disabled={loading || downloading}
            className={styles.btnSecondary}
          >
            {loading ? "Buscando…" : "🔍 Listar"}
          </button>
        </div>

        <div className={styles.grid2}>
          <div>
            <label className={styles.label}>Formato</label>
            <div className={styles.radioRow}>
              <label className={styles.radio}>
                <input
                  type="radio"
                  checked={formato === "video"}
                  onChange={() => setFormato("video")}
                  disabled={downloading}
                />
                🎬 Video MP4
              </label>
              <label className={styles.radio}>
                <input
                  type="radio"
                  checked={formato === "audio"}
                  onChange={() => setFormato("audio")}
                  disabled={downloading}
                />
                🎵 Audio MP3
              </label>
            </div>
          </div>

          <div>
            <label className={styles.label}>Calidad (video)</label>
            <select
              value={calidad}
              onChange={(e) => setCalidad(e.target.value)}
              disabled={formato === "audio" || downloading}
              className={styles.select}
            >
              {CALIDADES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {entries.length > 0 && (
        <section className={styles.card}>
          <div className={styles.listHeader}>
            <span>{playlistTitle} · {selectedCount}/{entries.length} marcados</span>
            <div>
              <button onClick={() => toggleAll(true)}  className={styles.btnGhost} disabled={downloading}>☑ Todos</button>
              <button onClick={() => toggleAll(false)} className={styles.btnGhost} disabled={downloading}>☐ Ninguno</button>
            </div>
          </div>
          <div className={styles.videoList}>
            {entries.map((e, i) => (
              <label key={i} className={styles.videoItem}>
                <input
                  type="checkbox"
                  checked={selected.has(i)}
                  onChange={() => toggleOne(i)}
                  disabled={downloading}
                />
                <span className={styles.videoTitle}>
                  {String(i + 1).padStart(3, " ")}. {e.title}
                </span>
                {e.duration && <span className={styles.videoDur}>[{formatDur(e.duration)}]</span>}
              </label>
            ))}
          </div>
        </section>
      )}

      <section className={styles.actions}>
        <button
          onClick={handleDescargar}
          disabled={downloading || (!url.trim() && entries.length === 0)}
          className={styles.btnPrimary}
        >
          {downloading ? "Descargando…" : "⬇ DESCARGAR"}
        </button>
        {downloading && (
          <button onClick={handleCancelar} className={styles.btnDanger}>
            ✕ Cancelar
          </button>
        )}
      </section>

      {downloading && (
        <section className={styles.statusCard}>
          <div className={styles.statusTitle}>
            ⬇ ({currentIdx}/{currentTotal}) {currentTitle}
          </div>
          <div className={styles.statusSub}>{progressLabel}</div>
          <div className={styles.progressBar}>
            <div className={styles.progressFill} style={{ width: `${progress}%` }} />
          </div>
        </section>
      )}

      <section className={styles.card}>
        <div className={styles.logHeader}>
          <span>Registro</span>
          <button className={styles.btnGhost} onClick={() => setLogs([])}>🗑 Limpiar</button>
        </div>
        <pre className={styles.log}>
          {logs.length === 0
            ? "Pegá una URL y hacé clic en 'Listar' o 'Descargar'."
            : logs.map((l, i) => (
                <div key={i} className={styles[`log_${l.tag}`]}>{l.msg}</div>
              ))}
        </pre>
      </section>

      <footer className={styles.footer}>
        Backend: <code>{apiUrl}</code>
        {" · "}
        <a href="https://github.com/Estebanjgg/descargar-video-youtube-script" target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
      </footer>
    </main>
  );
}
