import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Descargador de YouTube",
  description: "Descargá videos y audio de YouTube en distintas calidades",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
