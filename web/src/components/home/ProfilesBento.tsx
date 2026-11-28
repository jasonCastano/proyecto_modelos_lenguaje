/**
 * Los cinco perfiles en una rejilla bento (spec 031): glifo y color de cada uno, para quién es, qué puede
 * preguntar y su consulta de ejemplo, que abre el agente con ese perfil y el mensaje listo para revisar
 * (comportamiento de la spec 026). Los cinco son de libre elección en la web (spec 027).
 */
import { AUDIENCE_CARDS } from "../../data/profileSuggestions";
import { queueMessage, setAudience } from "../../lib/platform";
import { navigate } from "../../lib/router";
import { PRODUCT_GLYPHS } from "../brand/ProductGlyphs";

export function ProfilesBento() {
  function open(key: string, example: string) {
    setAudience(key);
    queueMessage(example, "draft");
    navigate("/agente");
  }

  return (
    <section aria-labelledby="perfiles-title" className="site-section site-section--surface" id="perfiles">
      <div className="wrap">
        <div className="sec-head">
          <h2 className="site-h2" id="perfiles-title">
            Un agente para cada perfil
          </h2>
          <p className="site-lead">
            Elige con quién hablas o preséntate. Valer-IA ajusta su foco y sus herramientas a tu perfil.
          </p>
        </div>
        <ul className="bento">
          {AUDIENCE_CARDS.map((card) => {
            const Glyph = PRODUCT_GLYPHS[card.glyph];
            return (
              <li className="bento__cell" data-profile={card.key} key={card.key}>
                <button
                  className="site-card bento__card"
                  onClick={() => open(card.key, card.example)}
                  type="button"
                >
                  <span className="bento__glyph">
                    <Glyph size={30} />
                  </span>
                  <h3>{card.label}</h3>
                  <span className="bento__for">{card.forWhom}</span>
                  <span className="bento__ask">{card.canAsk}</span>
                  <span className="bento__example">{card.example}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
