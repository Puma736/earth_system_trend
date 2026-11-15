import type { Metadata } from "next";
import "@mantine/charts/styles.css";
import { Workstation } from "@/components/investigation/workstation";
import "./investigation.css";

export const metadata: Metadata = {
  title: "Investigación (datos simulados) · Trend Detective",
  description:
    "Pantalla de la rama velaxd: el motor de análisis sobre series simuladas por el servidor, no sobre datos de la NASA.",
};

export default function InvestigationPage() {
  return (
    <div className="investigation-page" lang="es">
      <Workstation />
    </div>
  );
}
