# Data Model: Avatar con sincronización de labios (spec 017)

Todo vive en el navegador; nada se persiste en el servidor.

## AudioFeatures (por cuadro, `lipsync.ts::readFeatures`)

| Campo | Tipo | Regla |
|-------|------|-------|
| `rmsDb` | number | RMS del dominio temporal en dBFS. `-Infinity` en silencio digital; se acota a −100. |
| `b1` | number ≥ 0 | Energía media normalizada (0–1) de 300 a 900 Hz. |
| `b2` | number ≥ 0 | Igual, de 900 a 1800 Hz. |
| `b3` | number ≥ 0 | Igual, de 1800 a 3500 Hz. |

Los índices de bin se calculan con `sampleRate` del contexto y `fftSize`: `bin = round(f / (sampleRate / fftSize))`.

## MouthState (`lipsync.ts::mouthFromFeatures`)

| Campo | Tipo | Regla |
|-------|------|-------|
| `shape` | `"closed" \| "half" \| "open" \| "round" \| "wide"` | Ver las reglas de forma más abajo. |
| `openness` | number en [0, 1] | Apertura suavizada. |
| `pending` | `{ shape, frames }` | Histéresis: una forma nueva entre las abiertas se adopta solo si se repite 2 cuadros seguidos. |

**Apertura objetivo**:
- Si `rmsDb ≤ gateDb` (−45), el objetivo es 0.
- En otro caso, `(rmsDb − gateDb) / (fullDb − gateDb)` con `fullDb` = −15, acotado a [0, 1].

**Suavizado** con `dt` en ms y `α = 1 − exp(−dt/τ)`:
- `τ = attackMs` (30) si el objetivo es mayor que la apertura actual;
- `τ = releaseMs` (55) en otro caso.

**Reglas de forma**, evaluadas en orden:
1. `openness < 0.08` → `closed`.
2. `openness < 0.30` → `half`.
3. `b3 / (b1 + b2 + ε) > 0.45` → `wide`.
4. `b1 / (b1 + b2 + b3 + ε) > 0.40` y `b3 < 0.38` → `round`.
5. En otro caso → `open`.

`closed` y `half` se aplican sin histéresis, para no retrasar el cierre.

**Invariante de cierre** (FR-004): desde `openness = 1` y con un objetivo de 0, la apertura baja de 0,08 en
≤ 160 ms (con τ = 55 ms y cuadros de 16,7 ms: 9 cuadros = 150 ms → e^(−150/55) ≈ 0,065).

**Constantes** (`LIPSYNC_TUNING`, exportadas): `gateDb = −45`, `fullDb = −15`, `attackMs = 30`,
`releaseMs = 55`, `wideRatio = 0.45`, `roundRatio = 0.40`, `roundMaxB3 = 0.38`, `hysteresisFrames = 2`.
Calibrados con la voz Rebeca (research R3, «Calibración»); los iniciales (0,9 / 0,55 / 0,25) suponían
energía lineal, pero el analizador del navegador entrega bytes en escala dB.

## MouthGeometry (`lipsync.ts::mouthGeometry`)

Parámetros del `path` de la boca, en unidades del `viewBox` (0–200).

| Forma | Ancho | Alto máximo | Redondez | Comentario |
|-------|-------|-------------|----------|------------|
| `closed` | 28 | 0 | 0 | Línea con sonrisa leve. |
| `half` | 26 | 6 | 0,3 | |
| `open` | 26 | 16 | 0,5 | «a» |
| `round` | 16 | 14 | 1,0 | «o», «u» |
| `wide` | 34 | 8 | 0,2 | «e», «i» |

El alto efectivo es `alto máximo × openness`. Entre cuadros se interpolan el ancho y la redondez (lerp 0,35 por
cuadro) para que el cambio de forma sea suave.

## AvatarState

`"idle" | "thinking" | "speaking"` = `speaking ? "speaking" : busy ? "thinking" : "idle"`.

**Transiciones**:

```text
idle ──envío de pregunta──▶ thinking ──primer audio──▶ speaking ──cola vacía / stop──▶ idle
thinking ──fin del turno sin audio (silenciada, no disponible, error)──▶ idle
speaking ──nueva pregunta──▶ thinking   (la boca se cierra; la voz anterior se detiene)
```

## AvatarPreference

`localStorage["manuelita.avatar.hidden"]`: `"1"` significa oculto; si la clave no existe, el avatar está visible.
La lectura y la escritura van en `try/catch`; si el almacenamiento falla, la preferencia vale solo para la sesión.
