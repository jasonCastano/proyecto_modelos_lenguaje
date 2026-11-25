/**
 * Selector de perfil del espacio de trabajo (spec 026): píldoras en un grupo de radio. Cambiar de
 * perfil no reinicia la conversación; el planificador solo se ofrece a personas autorizadas.
 */
import type { KeyboardEvent } from "react";

import type { ProfileOption } from "../../lib/types";

interface ProfilePickerProps {
  options: ProfileOption[];
  value: string;
  onChange: (key: string) => void;
}

export function ProfilePicker({ options, value, onChange }: ProfilePickerProps) {
  const enabled = options.filter((option) => option.authorized);

  function move(event: KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"].includes(event.key)) return;
    event.preventDefault();
    const index = enabled.findIndex((option) => option.key === value);
    const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
    const next = enabled[(index + step + enabled.length) % enabled.length];
    if (next) {
      onChange(next.key);
      const target = event.currentTarget.querySelector<HTMLButtonElement>(`[data-key="${next.key}"]`);
      target?.focus();
    }
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
        return (
          <button
            aria-checked={checked}
            className="profile-picker__pill"
            data-key={option.key}
            disabled={!option.authorized}
            key={option.key}
            onClick={() => onChange(option.key)}
            role="radio"
            tabIndex={checked ? 0 : -1}
            title={option.authorized ? undefined : "Solo equipo de planta autorizado"}
            type="button"
          >
            {option.label}
            {option.authorized ? null : <span className="visually-hidden"> (solo autorizados)</span>}
          </button>
        );
      })}
    </div>
  );
}
