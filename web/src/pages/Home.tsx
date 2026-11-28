/**
 * Entrada pública de la plataforma (spec 031, research R6): una sección por pantalla. El hero lleva el
 * video pitch (spec 028) como visual; siguen la app en grande, los perfiles, los negocios, la frase, la
 * planificación, las garantías, la evidencia y las preguntas. El cierre vive en el pie (AppShell).
 * La consulta, el resumen y la FAQ de los Módulos 1 y 2 pasaron a la vista de evidencia.
 */
import { AppFrame } from "../components/home/AppFrame";
import { Businesses } from "../components/home/Businesses";
import { EvidenceTools } from "../components/home/EvidenceTools";
import { Faq } from "../components/home/Faq";
import { Guarantees } from "../components/home/Guarantees";
import { Hero } from "../components/home/Hero";
import { PlanningBand } from "../components/home/PlanningBand";
import { ProfilesBento } from "../components/home/ProfilesBento";
import { Statement } from "../components/home/Statement";

export function Home() {
  return (
    <>
      <Hero />
      <AppFrame />
      <ProfilesBento />
      <Businesses />
      <Statement />
      <PlanningBand />
      <Guarantees />
      <EvidenceTools />
      <Faq />
    </>
  );
}
