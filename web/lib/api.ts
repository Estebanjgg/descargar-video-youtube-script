export interface VideoEntry {
  id: string | null;
  title: string;
  url: string;
  duration: number | null;
  thumbnail: string | null;
}

export interface InfoResponse {
  type: "video" | "playlist";
  title: string;
  count: number;
  entries: VideoEntry[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchInfo(url: string): Promise<InfoResponse> {
  const res = await fetch(`${API_URL}/api/info`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Error ${res.status}: ${txt}`);
  }
  return res.json();
}

export interface DownloadParams {
  url: string;
  formato: "video" | "audio";
  calidad: string;
}

/**
 * Descarga un único video. Devuelve un Blob y el nombre sugerido del archivo.
 * onProgress recibe (bytesRecibidos, bytesTotales|null).
 */
export async function downloadVideo(
  params: DownloadParams,
  onProgress?: (received: number, total: number | null) => void,
  signal?: AbortSignal,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${API_URL}/api/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    signal,
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Error ${res.status}: ${txt}`);
  }

  // Extraer nombre desde Content-Disposition
  const cd = res.headers.get("content-disposition") || "";
  let filename = "video";
  const m = cd.match(/filename\*?=(?:UTF-8'')?["]?([^";]+)["]?/i);
  if (m) filename = decodeURIComponent(m[1]);

  const totalHeader = res.headers.get("content-length");
  const total = totalHeader ? parseInt(totalHeader, 10) : null;

  if (!res.body || !onProgress) {
    const blob = await res.blob();
    return { blob, filename };
  }

  const reader = res.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) {
      chunks.push(value);
      received += value.length;
      onProgress(received, total);
    }
  }

  const blob = new Blob(chunks as BlobPart[]);
  return { blob, filename };
}

export function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
