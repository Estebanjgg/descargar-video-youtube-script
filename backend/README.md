# Backend — YouTube Downloader API

API FastAPI con `yt-dlp` que el frontend usa para listar y descargar videos.

## Desarrollo local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Probar:

```bash
curl http://localhost:8000/
curl -X POST http://localhost:8000/api/info \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

> Necesitás `ffmpeg` instalado y en el `PATH` (`brew install ffmpeg` /
> `apt install ffmpeg` / Windows: descargar desde gyan.dev).

## Endpoints

| Método | Ruta             | Descripción |
|--------|------------------|-------------|
| GET    | `/`              | Health check |
| POST   | `/api/info`      | Lista videos (acepta playlists) |
| POST   | `/api/download`  | Descarga un video → devuelve el archivo |

`/api/download` recibe:

```json
{ "url": "...", "formato": "video|audio", "calidad": "144|240|360|480|720|1080" }
```

## Deploy

### Opción 1 — Railway (recomendado, gratis con límites)

1. Crear cuenta en <https://railway.app>.
2. **New Project → Deploy from GitHub Repo** → seleccionar este repo.
3. Settings → **Root Directory**: `backend`.
4. Railway detecta el `Dockerfile` automáticamente y compila.
5. Settings → **Variables** → agregar:
   - `ALLOWED_ORIGINS=https://estebanjgg.github.io,http://localhost:3000`
6. Settings → **Networking** → **Generate Domain**. Copiar la URL pública
   (algo como `https://tu-app.up.railway.app`).
7. En el frontend (`web/.env.local` o variable de entorno de GitHub Pages),
   configurar `NEXT_PUBLIC_API_URL` con esa URL.

### Opción 2 — Fly.io

```bash
cd backend
fly launch --no-deploy
fly secrets set ALLOWED_ORIGINS=https://estebanjgg.github.io
fly deploy
```

### Opción 3 — Render

- New → Web Service → Docker → root dir `backend`.
- Free plan funciona; se duerme tras inactividad.
