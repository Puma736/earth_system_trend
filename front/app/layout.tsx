import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NASA Space",
  description: "Aplicación web de NASA Space",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
