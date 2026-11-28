/**
 * Pestaña WhatsApp (spec 032, contracts/ui-contract.md). Dos secciones, una por pantalla:
 *
 * 1. `#whatsapp`: qué es chatear con Valer-IA por WhatsApp y qué se le puede preguntar.
 * 2. `#conectar`: las dos formas de entrar al chat, lado a lado: el enlace a WhatsApp Web (en el teléfono, la
 *    aplicación) y el QR para escanear la pantalla con el celular.
 *
 * El número vive en el `.env` del servidor, nunca en el repositorio: la página pide el enlace y el QR al
 * backend. Sin número válido, sin red o con una respuesta inesperada, explica que el chat no está disponible y
 * lleva al Agente.
 */
import { useCallback, useEffect, useState } from "react";

import { photoSrc, photoSrcSet } from "../data/photos";
import { fetchWhatsAppLink } from "../lib/api";
import { Link } from "../lib/router";
import type { WhatsAppLink, WhatsAppMode } from "../lib/types";

export const WA_NOTICE = "Proyecto académico con IA. No es un canal oficial de Manuelita.";
export const WA_UNAVAILABLE = "El chat de WhatsApp no está disponible en este momento";

const MODE_TEXT: Record<Exclude<WhatsAppMode, "unknown">, string> = {
  open: "Abierto: cualquier número puede escribir",
  closed: "Solo números de prueba del equipo",
};

const POINTS = [
  "Pregunta lo mismo que en la web: productos, sostenibilidad, proveedores o la planificación.",
  "Cada respuesta trae la fuente del dato, como en la web.",
  "Escribe o manda una nota de voz, en español o en inglés.",
];

type State =
  | { kind: "loading" }
  | { kind: "ready"; link: WhatsAppLink }
  | { kind: "error" };

type NavigatorWithUAData = Navigator & { userAgentData?: { mobile?: boolean } };

/** Teléfono o tableta: WhatsApp Web no funciona en navegadores móviles (research R3). */
export function isMobileDevice(nav: NavigatorWithUAData = window.navigator): boolean {
  if (nav.userAgentData?.mobile === true) return true;
  return /Android|iPhone|iPad|iPod|Mobile/i.test(nav.userAgent ?? "");
}

function step(index: number) {
  return { "--step": index } as React.CSSProperties;
}

export function WhatsApp() {
  const [state, setState] = useState<State>({ kind: "loading" });

  const load = useCallback(() => {
    setState({ kind: "loading" });
    let active = true;
    fetchWhatsAppLink()
      .then((link) => {
        if (active) setState({ kind: "ready", link });
      })
      .catch(() => {
        if (active) setState({ kind: "error" });
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => load(), [load]);

  const link = state.kind === "ready" && state.link.available ? state.link : null;
  const mobile = isMobileDevice();
  const href = link ? (mobile ? link.app_url : link.web_url) : null;
  const unavailable = state.kind === "error" || (state.kind === "ready" && !state.link.available);

  return (
    <>
      <section aria-labelledby="whatsapp-title" className="site-section wa" data-enter id="whatsapp">
        <div className="wrap wa__grid">
          <div className="wa__text">
            <p className="wa__notice wa-notice" data-enter-step style={step(0)}>
              {WA_NOTICE}
            </p>
            <h1 className="wa__title" data-enter-step id="whatsapp-title" style={step(1)} tabIndex={-1}>
              Habla con Valer-IA por WhatsApp
            </h1>
            <p className="wa__lead wa-lead" data-enter-step style={step(2)}>
              El mismo agente de esta web te responde en WhatsApp, desde el computador o desde tu celular.
            </p>
            <ul className="wa__points" data-enter-step style={step(3)}>
              {POINTS.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
            <a className="btn wa__to-options" data-enter-step href="#conectar" style={step(4)}>
              Ver cómo conectarte
            </a>
          </div>
          <div className="wa__visual" data-enter-step style={step(5)}>
            <img
              alt=""
              className="wa__photo"
              data-source="stand-in"
              height={525}
              sizes="(min-width: 1024px) 640px, 100vw"
              src={photoSrc("cana", 700)}
              srcSet={photoSrcSet("cana")}
              width={700}
            />
          </div>
        </div>
      </section>

      <section
        aria-busy={state.kind === "loading"}
        aria-labelledby="conectar-title"
        className="site-section site-section--surface wa-connect"
        id="conectar"
      >
        <div className="wrap">
          <div className="wa-connect__head">
            <h2 className="site-h2" id="conectar-title">
              Elige cómo conectarte
            </h2>
            {link && link.mode !== "unknown" ? (
              <p className="wa__mode" data-mode={link.mode} data-testid="wa-mode">
                {MODE_TEXT[link.mode]}
              </p>
            ) : null}
          </div>

          {link ? (
            <div className="wa-connect__options">
              <article className="wa-option" aria-labelledby="wa-option-web">
                <h3 className="wa-option__title" id="wa-option-web">
                  {mobile ? "Desde este celular" : "Desde este computador"}
                </h3>
                <p className="wa-option__text">
                  {mobile
                    ? "Abre la aplicación de WhatsApp con el chat de Valer-IA y el saludo listo para enviar."
                    : "Abre WhatsApp Web con el chat de Valer-IA y el saludo listo para enviar."}
                </p>
                <a
                  className="btn wa__open"
                  data-testid="wa-open"
                  href={href ?? undefined}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  <img alt="" className="wa__icon" height={22} src="/media/iconos/whatsapp.svg" width={22} />
                  {mobile ? "Abrir WhatsApp" : "Abrir WhatsApp Web"}
                  <span className="visually-hidden"> (se abre en una pestaña nueva)</span>
                </a>
                <p className="wa-option__needs wa-needs">
                  {mobile
                    ? "Necesitas la aplicación de WhatsApp instalada."
                    : "Necesitas WhatsApp Web vinculado a tu celular."}
                </p>
              </article>

              {link.qr_svg ? (
                <article className="wa-option wa-option--qr" aria-labelledby="wa-option-qr">
                  <h3 className="wa-option__title" id="wa-option-qr">
                    {mobile ? "Desde otro celular" : "Desde tu celular"}
                  </h3>
                  <div
                    aria-label="Código QR para abrir el chat en tu teléfono"
                    className="wa__qr"
                    dangerouslySetInnerHTML={{ __html: link.qr_svg }}
                    data-testid="wa-qr"
                    role="img"
                  />
                  <p className="wa-option__text wa-option__qr-text">
                    Escanea el código con la cámara de tu celular y se abre el chat.
                  </p>
                </article>
              ) : null}
            </div>
          ) : null}

          {state.kind === "loading" ? <p className="wa-connect__loading">Cargando el enlace…</p> : null}

          {unavailable ? (
            <div className="wa__unavailable" role="status">
              <p className="wa__unavailable-text">{WA_UNAVAILABLE}</p>
              <div className="wa__unavailable-actions">
                <Link className="btn" to="/agente">
                  Habla con Valer-IA aquí
                </Link>
                {state.kind === "error" ? (
                  <button className="btn btn--line" onClick={load} type="button">
                    Reintentar
                  </button>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}
