# Quickstart — Frontend profesional y showcase del Módulo 1

**Feature**: `012-manuelita-rag-showcase`
**Fecha**: 2026-10-31

Guía para validar la experiencia web completa: API, consola RAG, narrativa del Módulo 1, modo demo, responsive y accesibilidad.

## 1. Requisitos

- Python 3.14 y `uv`.
- Node.js 24 y npm (solo para el frontend).
- Datos de oro materializados por Git LFS:

```bash
git lfs install
git lfs pull
```

- Para el modo real: `DEEPSEEK_API_KEY` en `.env`.
- Para revisar sin red: modo demostración.

## 2. Instalación

```bash
uv sync --frozen
cd web
npm ci
cd ..
```

## 3. Desarrollo local

Terminal 1 — API:

```bash
uv run uvicorn proyecto_modelos_lenguaje.api:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd web
npm run dev
```

Vite sirve la página y hace proxy de `/api` hacia `http://localhost:8000`. Abrir la URL que indique Vite.

## 4. Producción local

```bash
cd web
npm run build
cd ..
uv run uvicorn proyecto_modelos_lenguaje.api:app --host 127.0.0.1 --port 8000
```

FastAPI sirve `web/dist` y la API en el mismo origen. Abrir `http://127.0.0.1:8000`.

## 5. Escenarios de validación

### 5.1 Consulta real

1. Abrir el hero.
2. Escribir “¿Qué productos ofrece Manuelita?”.
3. Pulsar **Preguntar al corpus**.

Resultado esperado:

- Estado de carga visible.
- Respuesta con al menos una cita `[U#]`.
- Fuentes con título, sección y enlace.
- Metadatos de modelo, latencia y citas.
- Sin claves ni rutas absolutas.

### 5.2 Fallback

Preguntar por un dato fuera del corpus, por ejemplo un precio actual no documentado.

Resultado esperado: “No hay evidencia suficiente…”, sin citas y sin respuesta inventada.

### 5.3 Modo demostración

1. Pulsar **Usar modo demostración** o activar el modo desde el banner.
2. Enviar una pregunta.

Resultado esperado: banner visible de modo demo, respuesta rotulada como simulada, sin llamada a DeepSeek.

### 5.4 Sin clave

1. Quitar `DEEPSEEK_API_KEY` del entorno.
2. Intentar una consulta real.

Resultado esperado: aviso accionable, CTA de demo y `health.configured=false`; sin excepción visible.

### 5.5 Resumen y FAQ

1. Cambiar a **Resumen** y generar el paquete 8000.
2. Cambiar a **FAQ** y generar 12 preguntas.

Resultado esperado: respuestas con citas o `missing_evidence`; la consola no pierde la pregunta anterior.

### 5.6 Showcase del Módulo 1

Recorrer la página hasta el final.

Resultado esperado:

- Problema, datos, medallion, prompts, tareas, app, métricas y límites.
- Cifras coincidentes con `/api/showcase`.
- Enlaces a specs, reportes y ADR.
- Aviso académico no afiliado.

## 6. Matriz responsive

| Ancho | Comprobación |
|-------|--------------|
| 360×640 | Hero legible, consola usable, sin scroll horizontal |
| 390×844 | CTA y teclado accesibles |
| 768×1024 | Narrativa y métricas en una columna |
| 1024×768 | Hero asimétrico y consola visible |
| 1440×900 | Composición editorial completa |
| 1920×1080 | Contenido centrado, líneas de lectura cómodas |

## 7. Accesibilidad

- Recorrer con `Tab`: hero → CTA → consola → tareas → respuesta → fuentes.
- Foco visible en todos los controles.
- Probar zoom 200 %.
- Activar `prefers-reduced-motion` y confirmar que no hay animaciones esenciales.
- Verificar contraste 4.5:1 en texto normal.
- Probar lector de pantalla en el campo de pregunta y en el estado de carga.

## 8. Pruebas automatizadas

```bash
make check            # Python + web: Ruff + pytest + Vitest + build
make e2e              # Playwright E2E (modo demo, PML_E2E=1)
```

Resultado esperado:

- API y contratos en verde.
- Componentes con estados de carga, error y fallback.
- Build sin claves ni rutas absolutas.
- E2E sin red, sin DeepSeek y sin claves.

### 8.1 Presupuesto del bundle

Medición local del build de producción (`npm run build`):

| Recurso | Tamaño | Gzip |
|---------|--------|------|
| JS inicial (`index-*.js`) | 250,29 kB | 78,10 kB |
| CSS (`index-*.css`) | 22,40 kB | 5,49 kB |
| Fuentes | `woff2` autohospedadas en `dist/assets/` | — |

El presupuesto es JS inicial < 250 kB gzip: se cumple con margen. No hay peticiones a CDNs ni claves en el
bundle; para verificarlo:

```bash
grep -r "DEEPSEEK_API_KEY" web/dist   # no debe devolver resultados
grep -r "http://localhost" web/dist   # no debe devolver resultados
```

## 9. Contratos

- [`contracts/api.md`](contracts/api.md) — endpoints y errores.
- [`contracts/ui.md`](contracts/ui.md) — composición, tokens, estados y accesibilidad.
- [`contracts/answer.schema.json`](contracts/answer.schema.json) — respuesta citada.
- [`contracts/showcase.schema.json`](contracts/showcase.schema.json) — narrativa y métricas.
- [`data-model.md`](data-model.md) — entidades y transiciones.

## 10. Solución de problemas

| Problema | Acción |
|----------|--------|
| API no responde | Verificar `uv run uvicorn ... --port 8000` y el proxy de Vite. |
| `config_missing_key` | Crear `.env` con `DEEPSEEK_API_KEY` o usar demo. |
| Respuesta lenta | El timeout es 90 s; revisar red/cuota y reintentar. |
| Datos incompletos | `git lfs pull` y recargar `/api/showcase`. |
| Fuente no abre | Mantener título y URL visibles; no ocultar la cita. |
| Scroll horizontal | Revisar la matriz responsive y el ancho de la consola. |

## 11. Evidencias

- Capturas de 360, 768, 1440 y 1920 px.
- Reporte de pruebas API/componentes/E2E.
- Resultado de `npm run build`.
- Comparación de cifras de `/api/showcase` con los reportes reales.

No se inventan capturas ni resultados: las evidencias se generan al ejecutar la página y la API.
