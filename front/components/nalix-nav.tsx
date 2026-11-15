"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Inicio" },
  { href: "/analisis", label: "Análisis" },
  { href: "/regiones", label: "Regiones" },
] as const;

export function NalixNav() {
  const path = usePathname();
  return (
    <nav className="nalix-nav" aria-label="Secciones">
      {LINKS.map((link) => {
        const active = link.href === "/" ? path === "/" : path.startsWith(link.href);
        return (
          <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}>
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
