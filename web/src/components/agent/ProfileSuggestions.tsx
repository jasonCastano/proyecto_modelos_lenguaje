/** Consultas de ejemplo del perfil activo (spec 026, FR-009): quedan en el campo para revisarlas. */
import { audienceCard } from "../../data/profileSuggestions";

interface ProfileSuggestionsProps {
  audience: string;
  disabled: boolean;
  onPick: (text: string) => void;
}

export function ProfileSuggestions({ audience, disabled, onPick }: ProfileSuggestionsProps) {
  const card = audienceCard(audience);
  return (
    <section aria-labelledby="suggestions-title" className="side-panel">
      <h2 className="panel-title" id="suggestions-title">
        Para empezar como {card.label.toLowerCase().replace("b2b", "B2B")}
      </h2>
      <ul className="suggestions">
        {card.suggestions.map((text) => (
          <li key={text}>
            <button
              className="suggestions__item"
              disabled={disabled}
              onClick={() => onPick(text)}
              type="button"
            >
              {text}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
