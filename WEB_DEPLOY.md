# Versión Web (Next.js + FastAPI)

Esta es la versión web del descargador, con frontend en GitHub Pages y backend
en un servidor con Python.

```
┌──────────────────────┐         ┌───────────────────────┐
│  Frontend (Next.js)  │  HTTPS  │  Backend (FastAPI)    │
│  GitHub Pages        │ ──────▶ │  Railway / Fly / VPS  │
│  (estático)          │         │  yt-dlp + ffmpeg      │
└──────────────────────┘         └───────────────────────┘
```

## Paso a paso

### 1) Desplegar el backend (UNA SOLA VEZ)

Seguí las instrucciones de [backend/README.md](backend/README.md).
Recomendado: **Railway** (gratis, Dockerfile auto-detectado).

Al final vas a tener una URL tipo `https://tu-app.up.railway.app`.

### 2) Configurar GitHub Pages

En tu repo en GitHub:

- **Settings → Pages → Source: GitHub Actions**
- **Settings → Secrets and variables → Actions → Variables tab → New variable**:
  - Name: `NEXT_PUBLIC_API_URL`
  - Value: la URL del backend del paso 1.

### 3) Push

```bash
git push
```

GitHub Actions construye y publica el sitio en:
`https://estebanjgg.github.io/descargar-video-youtube-script/`

## Desarrollo local

Terminal 1 (backend):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Terminal 2 (frontend):

```bash
cd web
cp .env.local.example .env.local
npm install
npm run dev
```

Abrir <http://localhost:3000>.

## Funcionalidades nuevas vs. la GUI de escritorio

- Calidades seleccionables: **144p / 240p / 360p / 480p / 720p / 1080p**.
- Misma lógica de listado de playlists con checkboxes.
- Misma conversión a MP4 H.264 + AAC y MP3 192k.
- Funciona en cualquier navegador, sin instalar nada.
