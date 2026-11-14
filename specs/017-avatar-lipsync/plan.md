# Implementation Plan: Avatar del agente con sincronización de labios

**Branch**: `017-avatar-lipsync` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-avatar-lipsync/spec.md`

## Summary

El chat ya reproduce la voz del agente (Rebeca) por oraciones con Web Audio (spec 016). Esta feature le agrega un
avatar ilustrado que mueve la boca con ese mismo audio:

1. **US1 (P1)**: `VoicePlayer` intercala un `AnalyserNode` entre cada oración y los parlantes. Una función pura,
   `lipsync.ts`, convierte en cada cuadro el volumen y la energía por bandas (formantes) en una de cinco formas de
   boca, con apertura suavizada. `AgentAvatar` dibuja un SVG cuya boca se interpola a 60 fps mientras el agente
   habla.
2. **US2 (P2)**: estados de reposo (respiración y parpadeo), pensando y hablando, derivados de `busy` y de
   `speaking`.
3. **US3 (P3)**: respeta el movimiento reducido, tiene un diseño compacto para el teléfono y se puede ocultar con
   una preferencia persistente. Con la voz silenciada o no disponible, queda con la boca cerrada.

Todo ocurre en el navegador: no cambian el servidor ni los contratos HTTP, y no hay dependencias nuevas. Las
decisiones están en [research.md](./research.md) R1–R7.

## Technical Context

**Language/Version**: TypeScript 5.9 + React 19 (frontend). No hay cambios en Python.

**Primary Dependencies**: Web Audio API (`AnalyserNode`), SVG y CSS del navegador. **Sin dependencias npm ni
Python nuevas.**

**Storage**: `localStorage["manuelita.avatar.hidden"]` guarda la preferencia de visibilidad.

**Testing**: Vitest + Testing Library:
- función pura de lip-sync con características sintéticas;
- `VoicePlayer` con un `AudioContext` simulado;
- `AgentAvatar` con un analizador y un `requestAnimationFrame` simulados;
- `ChatView` integrado.

**Target Platform**: navegadores modernos con Web Audio, en escritorio y teléfono, servidos por `make app`.

**Project Type**: aplicación web (SPA React servida por FastAPI); el cambio es solo del frontend.

**Performance Goals**:
- Animación a la tasa de refresco, unos 60 fps, sin saltos durante respuestas de hasta 2 minutos (SC-003).
- Cierre de la boca en menos de 200 ms tras el silencio o la detención (FR-004, SC-002).
- El trabajo por cuadro se limita a leer el analizador y fijar 3 o 4 atributos SVG.

**Constraints**:
- Sin red ni servicios externos (FR-008).
- Sin cambios de comportamiento en el chat ni en la voz cuando el avatar está oculto o la voz está silenciada
  (SC-005).
- Accesible: `aria-hidden` y `prefers-reduced-motion`.

**Scale/Scope**: un avatar, cinco formas de boca y tres estados; solo en el chat del agente.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Integridad y autoría | Los commits los hace el equipo (§4.3). La ilustración es original y no imita a ninguna persona real (FR-011). | ✅ |
| II. Reproducibilidad | No hay dependencias nuevas; los umbrales están versionados en `LIPSYNC_TUNING`. | ✅ |
| III. Ética y legalidad | No usa la marca de Manuelita ni la imagen de una persona. No se envía audio a terceros. | ✅ |
| V. Evaluación empírica | SC-001 a SC-005 se verifican con el procedimiento de `quickstart.md`, el modo `?avatarDebug=1` y pruebas con señales sintéticas. | ✅ |
| VII. Simplicidad | Usa solo SVG y Web Audio nativos; la alternativa en la nube queda descartada en el ADR. | ✅ |
| 3.7 App web | Sigue la paleta corporativa (`tokens.css`), funciona en modo demo y no cambia los errores accionables. | ✅ |
| 3.8 Pruebas sin red | Todo con Vitest, sin audio real. | ✅ |
| 3.9 Seguridad | No hay claves ni datos nuevos. | ✅ |

**Resultado**: PASS. No hay violaciones que justificar.

**Re-check post-diseño (Phase 1)**: PASS. Los contratos son solo de UI y de módulos del frontend; la API no cambia.

## Project Structure

### Documentation (this feature)

```text
specs/017-avatar-lipsync/
├── plan.md              # Este archivo
├── research.md          # Phase 0: decisiones R1–R7
├── data-model.md        # Phase 1: características, forma de boca, estado, preferencia
├── quickstart.md        # Phase 1: guía de validación
├── contracts/
│   ├── lipsync.md       # API de lipsync.ts y del analizador en VoicePlayer
│   └── ui-avatar.md     # Componente AgentAvatar: estados, data-testid, diseño y accesibilidad
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
web/src/
├── lib/voice.ts                 # + AnalyserNode compartido: source → analyser → destination; analyser()
├── lib/useVoice.ts              # + expone analyser y speaking al avatar
├── lib/lipsync.ts               # NUEVO: features(analyser), mouthFromFeatures(), LIPSYNC_TUNING, mouthGeometry()
├── components/AgentAvatar.tsx   # NUEVO: SVG, bucle rAF mientras habla, estados, ocultar/mostrar
├── components/ChatView.tsx      # + rejilla con el avatar; avatarState = speaking | thinking | idle
├── styles/global.css            # + .agent-avatar, keyframes de respiración/parpadeo/mirada, reduced-motion, móvil
└── test/
    ├── lipsync.test.ts          # NUEVO
    ├── AgentAvatar.test.tsx     # NUEVO
    ├── voice.test.ts            # + el analizador queda en el grafo
    └── ChatViewVoice.test.tsx   # + estados del avatar con la voz simulada

docs/decisions/0021-avatar-local.md   # NUEVO: ADR (local vs. LiveAvatar, técnica de lip-sync)
CONSTITUTION.md, README.md, docs/demo.md   # avatar en §3.7, recorrido de la demo
```

**Structure Decision**: Todo vive en el frontend. La lógica de señal a boca es una función pura y aislada
(`lipsync.ts`) para poder probarla sin navegador. El avatar es un componente de presentación que solo lee el
analizador y el estado, así que el flujo del chat y de la voz no se toca, salvo para intercalar el analizador en el
grafo de audio.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
