# Contrato: cambios en la API HTTP

Solo se agregan **campos opcionales con valor por defecto**. No hay endpoints nuevos ni cambios incompatibles.

## `GET /api/health` → `HealthStatus`

| Campo nuevo | Tipo | Por defecto | Significado |
|-------------|------|-------------|-------------|
| `adversarial_corpus` | bool | `false` | `true` si el servidor arrancó con `MANUELITA_DEMO_CORPUS=malicious`; aplica a los modos demo y real |

## `GET /api/observability`

```json
{ "langsmith": true, "project": "manuelita-modulo2", "structured_log": "…/turns.jsonl", "adversarial_corpus": false }
```

## Fragmentos del turno (`ChatFragmentModel` en `/api/chat`, `/api/chat/stream` → `done`, `/api/threads/{id}`)

| Campo nuevo | Tipo | Por defecto | Regla |
|-------------|------|-------------|-------|
| `neutralized_sentences` | int ≥ 0 | `0` | > 0 solo si `anomalous = true` |

## Trazas

- `run_config(...)["tags"]` incluye `corpus:adversarial` cuando el corpus adversarial está activo.
- Cada línea de `turns.jsonl` incluye `"corpus": "adversarial" | "real" | "demo"`.

## Frontend (`web/src/lib/types.ts`)

- `HealthStatus.adversarial_corpus?: boolean`
- `ObservabilityStatus.adversarial_corpus?: boolean`
- `ChatFragment.neutralized_sentences?: number`

`DemoBanner` muestra «Corpus de prueba adversarial activo: las respuestas usan documentos con instrucciones
inyectadas» cuando `adversarial_corpus` es `true`.
