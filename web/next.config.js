/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === "production";

// Nombre del repo: necesario para GitHub Pages porque la app sirve en /<repo>/
const repoName = "descargar-video-youtube-script";

const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath:    isProd ? `/${repoName}` : "",
  assetPrefix: isProd ? `/${repoName}/` : "",
};

module.exports = nextConfig;
