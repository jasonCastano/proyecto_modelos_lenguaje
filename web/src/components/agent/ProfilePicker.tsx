/**
 * Selector de perfil del espacio de trabajo (spec 026; rediseño de la spec 027, design.md). Es un
 * registro de cinco columnas, un grupo de radio: cada opción muestra el glifo de su producto, el
 * nombre y para quién es. En la web los cinco perfiles son de libre elección, incluido el
 * planificador: la persona escoge el que le conviene. Cambiar de perfil no reinicia la conversación.
 */
import type { KeyboardEvent } from "react";

import { audienceCard } from "../../data/profileSuggestions";
import type { ProfileOption } from "../../lib/types";
import { PRODUCT_GLYPHS } from "../brand/ProductGlyphs";

interface ProfilePickerProps {
  options: ProfileOption[];
  value: string;
  onChange: (key: string) => void;
}

const KEYS = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];

export function ProfilePicker({ options, value, onChange }: ProfilePickerProps) {
  function move(event: KeyboardEvent<HTMLDivElement>) {
    if (!KEYS.includes(event.key) || options.length === 0) return;
    event.preventDefault();
    const index = options.findIndex((option) => option.key === value);
    let target = index;
    if (event.key === "Home") target = 0;
    else if (event.key === "End") target = options.length - 1;
    else {
      const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
      target = (index + step + options.length) % options.length;
    }
    const next = options[target];
    if (!next) return;
    onChange(next.key);
    event.currentTarget.querySelector<HTMLButtonElement>(`[data-key="${next.key}"]`)?.focus();
  }

  return (
    <div
      aria-label="Perfil con el que te atiende el agente"
      className="profile-picker"
      onKeyDown={move}
      role="radiogroup"
    >
      {options.map((option) => {
        const checked = option.key === value;
        const card = audienceCard(option.key);
        const Glyph = PRODUCT_GLYPHS[card.glyph];
        return (
          <button
            aria-checked={checked}
            className="profile-picker__option"
            data-key={option.key}
            data-product={card.glyph}
            key={option.key}
            onClick={() => onChange(option.key)}
            role="radio"
            tabIndex={checked ? 0 : -1}
            type="button"
          >
            <Glyph className="profile-picker__glyph" size={22} />
            <span className="profile-picker__name">{option.label}</span>
            <span className="profile-picker__for">{card.forWhom}</span>
          </button>
        );
      })}
    </div>
  );
}
