/**
 * Los cinco públicos como filas de un libro de registro (spec 026, design.md §5), no como tarjetas
 * iguales. La consulta de ejemplo abre el agente con ese perfil y el mensaje listo para revisar.
 */
import { AUDIENCE_CARDS } from "../../data/profileSuggestions";
import { queueMessage, setAudience } from "../../lib/platform";
import { navigate } from "../../lib/router";
import { PRODUCT_GLYPHS } from "../brand/ProductGlyphs";

export function ProfileLedger({ plannerAuthorized }: { plannerAuthorized: boolean }) {
  function open(key: string, example: string) {
    setAudience(key);
    queueMessage(example, "draft");
    navigate("/agente");
  }

  return (
    <section aria-labelledby="ledger-heading" className="profile-ledger">
      <h2 className="section-title" id="ledger-heading">
        ¿Quién eres?
      </h2>
      <ul className="profile-ledger__rows">
        {AUDIENCE_CARDS.map((card) => {
          const Glyph = PRODUCT_GLYPHS[card.glyph];
          const locked = card.key === "planificador" && !plannerAuthorized;
          return (
            <li className="profile-ledger__row" data-profile={card.key} key={card.key}>
              <Glyph className="profile-ledger__glyph" size={30} />
              <h3 className="profile-ledger__name">{card.label}</h3>
              <p className="profile-ledger__ask">{card.canAsk}</p>
              {locked ? (
                <p className="profile-ledger__locked">Solo equipo de planta autorizado</p>
              ) : (
                <button
                  className="profile-ledger__example"
                  onClick={() => open(card.key, card.example)}
                  type="button"
                >
                  {card.example}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
