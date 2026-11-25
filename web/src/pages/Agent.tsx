/**
 * Espacio de trabajo del agente (spec 026, historia 2): selector de perfil, la conversación de
 * siempre (ChatView: citas, voz, dictado, aprobación) y los paneles de fuentes, memoria y
 * sugerencias del perfil. Cambiar de perfil conserva el hilo.
 */
import { useEffect, useState } from "react";

import { MemoryPanel } from "../components/agent/MemoryPanel";
import { ProfilePicker } from "../components/agent/ProfilePicker";
import { ProfileSuggestions } from "../components/agent/ProfileSuggestions";
import { SourcesPanel } from "../components/agent/SourcesPanel";
import { ChatView } from "../components/ChatView";
import { audienceCard } from "../data/profileSuggestions";
import { getProfiles } from "../lib/chat";
import { AUDIENCES, queueMessage, setAudience, takeOutbox, usePlatform } from "../lib/platform";
import { visitUser } from "../lib/session";
import type { ChatTurn, MemoryItem, Mode, ProfileItem, ProfileOption } from "../lib/types";

const FALLBACK: ProfileOption[] = AUDIENCES.map((item) => ({
  key: item.key,
  label: item.label,
  requires_authorization: item.key === "planificador",
  authorized: item.key !== "planificador",
}));

export function Agent({ mode }: { mode: Mode }) {
  const { audience, outbox } = usePlatform();
  const [options, setOptions] = useState<ProfileOption[]>(FALLBACK);
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [memory, setMemory] = useState<{ preferences: MemoryItem[]; profile: ProfileItem[] }>({
    preferences: [],
    profile: [],
  });
  const [forgetRequest, setForgetRequest] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    let active = true;
    void getProfiles(visitUser())
      .then((rows) => {
        if (active && Array.isArray(rows) && rows.length) setOptions(rows);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const allowed = options.find((option) => option.key === audience)?.authorized ?? false;
  const effective = allowed ? audience : "visitante";
  const card = audienceCard(effective);

  return (
    <div className="agent">
      <header className="area-head">
        <h1 className="type-display area-head__title">Habla con Valer-IA</h1>
        <p className="area-head__lead">
          Te atiende como {card.label.toLowerCase().replace("b2b", "B2B")}: {card.canAsk.charAt(0).toLowerCase()}
          {card.canAsk.slice(1)}
        </p>
      </header>
      <ProfilePicker onChange={setAudience} options={options} value={effective} />
      <div className="agent__grid" data-drawer={drawerOpen ? "open" : "closed"}>
        <div className="agent__chat">
          <ChatView
            audience={effective}
            forgetRequest={forgetRequest}
            initialVariant="agent"
            mode={mode}
            onMemory={setMemory}
            onOutboxTaken={takeOutbox}
            onTurn={(last, id) => {
              setTurn(last);
              setThreadId(id);
            }}
            outbox={outbox}
          />
        </div>
        <button
          aria-controls="agent-side"
          aria-expanded={drawerOpen}
          className="agent__drawer-toggle action action--quiet"
          onClick={() => setDrawerOpen((open) => !open)}
          type="button"
        >
          {drawerOpen ? "Ocultar fuentes y memoria" : "Fuentes y memoria"}
        </button>
        <aside aria-label="Fuentes, memoria y sugerencias" className="agent__side" id="agent-side">
          <ProfileSuggestions
            audience={effective}
            disabled={false}
            onPick={(text) => queueMessage(text, "draft")}
          />
          <SourcesPanel turn={turn} />
          <MemoryPanel
            canForget={threadId !== null}
            onForget={() => setForgetRequest((count) => count + 1)}
            preferences={memory.preferences}
            profile={memory.profile}
            requested={forgetRequest > 0 && memory.preferences.length + memory.profile.length > 0}
          />
        </aside>
      </div>
    </div>
  );
}
