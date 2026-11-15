import type { Metadata } from "next";
import { ColorSchemeScript } from "@mantine/core";
import "@mantine/core/styles.css";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nalix",
  description:
    "Nalix es una plataforma de inteligencia climática que transforma datos ambientales en información para monitorear y prevenir la sequía y los focos de calor.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ColorSchemeScript forceColorScheme="dark" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* Source Serif 4: la conclusión de /investigation. El navegador solo la descarga en esa pantalla. */}
        <link
          href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,480;8..60,600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
