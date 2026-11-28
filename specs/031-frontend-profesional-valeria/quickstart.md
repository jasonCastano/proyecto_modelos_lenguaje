# Quickstart: Frontend profesional de Valer-IA (spec 031)

## Requisitos

- `make dev` hecho; Node 22+ y Chrome o Chromium (scripts de la skill `design-taste-frontend`).
- `S=~/.claude/skills/design-taste-frontend` (la skill instalada; sus archivos no se copian al repositorio).

## A. Ver la plataforma

```bash
make app                    # http://127.0.0.1:8000
```

Recorrer `/`, `/agente`, `/planificacion` y `/evidencia` a 1440, 1024, 768 y 390 px.

## B. Gate de la skill sobre la entrada

```bash
node $S/scripts/gate.mjs --start http://127.0.0.1:8000/ --kind software \
  --category "plataforma de agentes de IA" --primary "Habla con Valer-IA"
node $S/scripts/copy-lint.mjs web/dist/index.html --kind software
node $S/scripts/gate.mjs http://127.0.0.1:8000/
```

Resultado esperado: `GATE: PASS` (o `OPEN` con cada exención en `.taste-skill/waivers.json` y su motivo).

## C. Capturas de las áreas de aplicación

```bash
for r in agente planificacion evidencia; do
  for w in 1440 1024 768 390; do
    node $S/scripts/shoot.mjs --url http://127.0.0.1:8000/$r --w $w --out shots/$r-$w.png --profile .taste-skill/chrome-check
  done
done
```

Revisar: sin scroll horizontal, texto legible, colores de producto fijos, sin el logotipo de Manuelita.

## D. Pruebas

```bash
cd web && npx vitest run          # componentes, créditos de fotos completos
make e2e                          # recorridos, axe, responsive 360–1920, video pitch
LANGSMITH_TRACING=false make check
```

## E. Validación con personas (SC-001, SC-002)

- 5 personas ven la entrada 10 s y explican qué es, para quién y cómo empezar (≥ 4 de 5).
- Una persona nueva elige Cliente B2B, pregunta por certificaciones y abre una fuente en < 2 min.

## F. Resultados (2026-11-27)

| Verificación | Resultado |
|---|---|
| `copy-lint` sobre `copy.md` | 0 FAIL, 0 WARN |
| Gate de la skill (entrada, 3 rondas) | `GATE: OPEN 29`, desde 65 FAIL; 5 exenciones en `web/.taste-skill/waivers.json` |
| Abiertos del gate | 21 de rejilla (`edge-left`, `container-edges`, `split-pair`, `row-lines`, `off-grid`): el gate reconoce la rejilla de su kit, no la reimplementada; 5 de visual (`no-visual`, `text-only`) en secciones con íconos propios o UI viva; 2 `section-gaps`, 2 `neighbour` a 390 px, 2 de altura |
| `perf.mjs` (entrada) | LCP 532 ms, FCP 532 ms, CLS 0,000, bloqueo 199 ms; FAIL de transferencia total por el video pitch (9,8 MB, spec 028) y fotos de 700 px más grandes de lo mostrado en teléfono |
| Vitest | 28 archivos en verde, con `photos.test.ts` (créditos, licencias, productos) |
| Validación con personas (SC-001, SC-002) | Pendiente del integrante |
