import Link from "next/link";
import { NalixNav } from "@/components/nalix-nav";

const SOURCES = [
  { name: "NASA POWER", detail: "Clima diario · MERRA-2" },
  { name: "NASA FIRMS", detail: "Focos de calor · MODIS" },
  { name: "Bolivia", detail: "Departamentos y municipios" },
] as const;

export default function Home() {
  return (
    <main className="cover">
      <video className="cover-video" autoPlay muted loop playsInline preload="auto" aria-hidden="true">
        <source src="/nalix-calor.mp4" type="video/mp4" />
      </video>
      <div className="cover-shade" aria-hidden="true" />
      <div className="cover-grain" aria-hidden="true" />

      <header className="cover-header">
        <Link href="/" className="cover-brand" aria-label="Nalix, inicio">
          <span className="cover-brand-mark" aria-hidden="true" />
          Nalix
        </Link>
        <NalixNav />
      </header>

      <section className="cover-copy">
        <p className="cover-badge">
          <span className="cover-badge-dot" aria-hidden="true" />
          Inteligencia climática
        </p>
        <h1 className="cover-title">
          Ver la sequía <span className="cover-title-accent">antes</span> de que llegue el fuego.
        </h1>
        <p className="cover-lead">
          Nalix es una plataforma de inteligencia climática que transforma datos ambientales en
          información para monitorear y prevenir la sequía y los focos de calor.
        </p>
        <div className="cover-actions">
          <Link href="/analisis" className="cover-btn cover-btn-primary">
            Explorar análisis
            <span aria-hidden="true">→</span>
          </Link>
          <Link href="/regiones" className="cover-btn cover-btn-ghost">
            Ver regiones
          </Link>
        </div>
      </section>

      <footer className="cover-sources">
        {SOURCES.map((source) => (
          <div key={source.name} className="cover-source">
            <span className="cover-source-name">{source.name}</span>
            <span className="cover-source-detail">{source.detail}</span>
          </div>
        ))}
      </footer>
    </main>
  );
}
