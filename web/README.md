# Frontend — Descargador de YouTube (Next.js)

Interfaz web estática (Next.js + TypeScript) que consume el backend FastAPI
en [../backend](../backend). Diseñada para desplegarse en **GitHub Pages**.

## Funcionalidades

- Pegar URL de video o playlist y listar todos los videos.
- Marcar individualmente cuáles descargar (checkboxes, "Todos" / "Ninguno").
- Elegir formato (Video MP4 / Audio MP3).
- Elegir calidad (144p, 240p, 360p, 480p, 720p, 1080p).
- Barra de progreso en tiempo real con porcentaje + MB descargados.
- Log detallado de todo el proceso.
- Botón cancelar.

## Desarrollo local

Necesitás el backend corriendo en otra terminal (ver [../backend/README.md](../backend/README.md)).

```bash
cd web
cp .env.local.example .env.local
# editar NEXT_PUBLIC_API_URL si tu backend no está en localhost:8000

npm install
npm run dev
# abrir http://localhost:3000
```

## Build estático

```bash
npm run build
# salida → web/out/  (HTML/JS/CSS listo para subir a cualquier hosting estático)
```

## Deploy a GitHub Pages

1. **Configurar Pages** en el repo:
   - GitHub → Settings → **Pages** → Source: **GitHub Actions**.
2. **Variable del backend**:
   - Settings → Secrets and variables → Actions → **Variables** → New variable:
     - Name: `NEXT_PUBLIC_API_URL`
     - Value: la URL pública de tu backend (ej: `https://tu-app.up.railway.app`)
3. **Push a `main`**: el workflow [.github/workflows/deploy-web.yml](../.github/workflows/deploy-web.yml)
   se ejecuta automáticamente y publica en
   `https://estebanjgg.github.io/descargar-video-youtube-script/`.

> Si cambiás el nombre del repo, actualizá `repoName` en `next.config.js`.

## Estructura

```
web/
  app/
    layout.tsx        # layout raíz
    page.tsx          # UI principal
    page.module.css   # estilos del componente
    globals.css       # estilos globales (tema oscuro)
  lib/
    api.ts            # cliente HTTP del backend
  public/
    .nojekyll
  next.config.js      # output: "export" + basePath para GH Pages
  tsconfig.json
  package.json
```
