# Research — Frontend profesional y showcase del Módulo 1

**Feature**: `012-manuelita-rag-showcase`
**Fecha**: 2026-10-31
**Alcance**: experiencia web, API de acceso al RAG y narrativa visual del Módulo 1; no cambia corpus, prompts ni recuperación.

## Contexto

La app Streamlit actual demuestra el RAG, pero su lenguaje visual y su modelo de interacción no cumplen el encargo de una experiencia profesional de Manuelita. El RAG ya está implementado en Python y verificado con DeepSeek; la pieza faltante es una interfaz propia, una API pequeña que proteja la credencial y una página que explique el Módulo 1 con evidencia.

## Decisiones

### D1 — React + Vite + TypeScript para el frontend

**Decisión**: SPA de una sola ruta con React 19, Vite y TypeScript, sin router ni kit de UI.

**Rationale**: La consola RAG necesita estado local, carga asíncrona, reintento y componentes comprobables. React permite componer la página y probar estados con Vitest/RTL. Vite produce un build estático pequeño que FastAPI puede servir en el mismo origen.

**Alternativas consideradas**:

| Alternativa | Motivo para rechazarla |
|-------------|------------------------|
| Seguir con Streamlit | El encargo prohíbe su uso y su modelo visual no da la identidad buscada. |
| Next.js | Añade SSR, routing y servidor React para una sola página; no resuelve nada que el brief exija. |
| Astro + islas | Excelente para contenido, pero la consola y los estados interactivos quedan más fragmentados. |
| SvelteKit | Viable, pero el equipo y el ecosistema de pruebas están más alineados con React. |
| HTML + HTMX + Jinja | Menos toolchain, pero limita la composición, el estado y las pruebas de componentes. |

### D2 — FastAPI + Uvicorn como frontera del RAG

**Decisión**: API Python con endpoints `health`, `ask`, `summary`, `faq` y `showcase`. Reutiliza `tasks.py`, `retrieval.py` y `app_metrics.py`.

**Rationale**: La lógica ya existe en Python; una API delgada evita duplicarla en Node y mantiene la clave solo en el servidor. FastAPI ofrece validación Pydantic, OpenAPI y pruebas con `TestClient`.

**Alternativas consideradas**: Flask (menos tipado), un backend Node (duplica lógica y credenciales), llamada directa del navegador a DeepSeek (expondría la clave), Streamlit (prohibido).

### D3 — CSS propio con custom properties, sin kit de UI

**Decisión**: tokens CSS, composición editorial y componentes propios; fuentes variables autohospedadas. Sin Tailwind, sin shadcn, sin librería de componentes.

**Rationale**: El brief pide una identidad que no parezca plantilla. Un kit impondría radios, sombras y espaciados genéricos. Las custom properties permiten que la paleta corporativa viva en un solo lugar y se pruebe por contrato.

**Alternativas consideradas**: Tailwind (rápido, pero favorece el look de plantilla), shadcn/Radix (útil para accesibilidad, pero añade un sistema visual ajeno), CSS-in-JS (más runtime y ruido).

### D4 — Tipografía editorial autohospedada

**Decisión**: **Bricolage Grotesque Variable** para display y **Public Sans Variable** para cuerpo, servidas localmente desde `@fontsource-variable/*`.

**Rationale**: Bricolage aporta un gesto orgánico y contemporáneo, alejado de la serif cálida de plantilla; Public Sans mantiene legibilidad y neutralidad en cuerpo y datos. Autohospedarlas evita CDN, mejora privacidad y controla el subset.

**Alternativas consideradas**: system-ui (genérica), Inter (correcta pero ubicua), Fraunces + cream/terracotta (cliché de diseño generado), monospace para datos (tell de plantilla).

### D5 — “Cañaveral editorial” como dirección visual

**Decisión**: una línea de surco/caña recorre la página y conecta hero, consola, narrativa y métricas; cristales de azúcar separan bloques de datos; ondas de energía representan resultados; palma como cierre.

**Rationale**: Los motivos provienen del negocio real (caña, azúcar, etanol, palma, energía) y codifican información: la caña es el pipeline, el cristal es la unidad de conocimiento, la onda es la evaluación. Así se evita decoración arbitraria y se cumple la identidad sin copiar el sitio oficial.

**Alternativas consideradas**: fotos de productos (sin fuente y riesgo de falsedad), ilustración genérica de campo (no específica), gradientes y cards SaaS (plantilla).

### D6 — Clave solo en servidor y modo demo en la API

**Decisión**: la API lee `DEEPSEEK_API_KEY` del entorno; el frontend solo recibe `configured`, proveedor, modelo y estado. El modo demo se solicita a la API y usa el modelo falso determinista.

**Rationale**: Evita filtrar la clave al bundle, al HTML o a las DevTools. El modo demo permite revisión sin red, sin costo y sin clave, y se rotula en la UI.

**Alternativas consideradas**: clave en el cliente (inaceptable), demo solo en cliente (podría simular respuestas sin pasar por el contrato), servicio separado (infraestructura innecesaria).

### D7 — Showcase alimentado por datos reales

**Decisión**: `/api/showcase` construye las métricas desde `load_app_metrics()` y los reportes reales. La narrativa estática vive en `web/src/data/showcase.ts`; las cifras se inyectan, no se hardcodean.

**Rationale**: Evita que la página “mienta” cuando cambian los datos. Las afirmaciones narrativas quedan versionadas y las cifras conservan su fuente.

**Alternativas consideradas**: hardcodear cifras (se desactualizan), leer archivos desde el navegador (imposible y riesgoso), duplicar reportes (divergencia).

### D8 — Pruebas API + componentes + E2E

**Decisión**: `pytest`/`TestClient` para API y contratos; Vitest + RTL para componentes; Playwright Python para E2E, responsive y foco.

**Rationale**: Cada capa tiene una herramienta adecuada. Playwright ya está en el proyecto y puede reutilizarse; no se añade un segundo runner E2E.

**Alternativas consideradas**: solo E2E (lento y poco diagnóstico), solo componentes (no prueba integración real), Cypress (nuevo runtime sin ventaja).

### D9 — FastAPI sirve el build en producción

**Decisión**: en producción `uv run uvicorn proyecto_modelos_lenguaje.api:app` sirve `web/dist` y la API en el mismo origen. En desarrollo, Vite hace proxy de `/api`.

**Rationale**: Un solo proceso y un solo origen simplifican CORS, cookies, CSP y despliegue; no se necesita un CDN para una demo académica.

**Alternativas consideradas**: dos servicios separados (CORS y configuración extra), CDN estático (más piezas), Vercel + API externa (más superficie).

### D10 — Migración de Streamlit

**Decisión**: la nueva página es la entrada del producto. `app.py` y la dependencia `streamlit` se retiran al final de la migración, después de trasladar las pruebas útiles a API/componentes/E2E. `brand.py` se conserva como referencia de tokens hasta que `tokens.css` sea la fuente y se añade una prueba de paridad de colores.

**Rationale**: Retirar Streamlit de golpe rompería pruebas y la demo actual; hacerlo al final mantiene una red de seguridad. La prueba de paridad evita que la paleta corporativa se bifurque.

**Alternativas consideradas**: mantener Streamlit en paralelo (contradice el encargo), borrar todo de inmediato (riesgo de perder cobertura), reescribir la app en otro framework Python (no resuelve la experiencia).

## Incógnitas resueltas

| Incógnita | Resolución |
|-----------|------------|
| ¿Qué stack de frontend? | React + Vite + TypeScript, sin kit de UI. |
| ¿Cómo se protege la clave? | Solo en el servidor; la API nunca la devuelve. |
| ¿Cómo se accede al RAG? | API FastAPI que reutiliza `tasks.py`. |
| ¿Cómo se mantiene la identidad? | Tokens CSS con la paleta corporativa y motivos de producto. |
| ¿Cómo se prueba el diseño? | Vitest/RTL, Playwright, matriz responsive y checklist visual. |
| ¿Qué pasa con Streamlit? | Se retira al final de la migración. |
| ¿Cómo se evita inventar cifras? | `/api/showcase` desde `app_metrics` y reportes reales. |
| ¿Cómo se despliega? | FastAPI sirve `web/dist` en el mismo origen. |

## Referencias

- React 19: https://react.dev/
- Vite: https://vite.dev/
- FastAPI: https://fastapi.tiangolo.com/
- Vitest: https://vitest.dev/
- Testing Library: https://testing-library.com/
- Playwright Python: https://playwright.dev/python/
- Bricolage Grotesque: https://fonts.google.com/specimen/Bricolage+Grotesque
- Public Sans: https://fonts.google.com/specimen/Public+Sans
- WCAG 2.2: https://www.w3.org/WAI/WCAG22/quickref/
