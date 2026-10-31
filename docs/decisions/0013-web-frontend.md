# ADR 0013 — Frontend web propio sobre FastAPI

- **Estado**: aceptada
- **Fecha**: 2026-10-31
- **Autores**: Jason Alejandro Castaño
- **Contexto**: feature 012, reemplazo de Streamlit

## Contexto

La app Streamlit demostró el RAG, pero el encargo pide una experiencia web profesional de Manuelita, con identidad visual propia, consola RAG, recorrido del Módulo 1 y despliegue como sitio. La lógica del RAG ya vive en Python y usa DeepSeek con una clave que no debe llegar al navegador.

## Decisión

1. **Frontend**: React 19 + Vite + TypeScript en `web/`, sin kit de UI ni Tailwind.
2. **Backend**: FastAPI + Uvicorn en `src/proyecto_modelos_lenguaje/api.py`, reutilizando `tasks.py`, `retrieval.py` y `app_metrics.py`.
3. **Contrato**: API JSON `/api/health`, `/api/ask`, `/api/summary`, `/api/faq` y `/api/showcase`.
4. **Identidad**: tokens CSS con la paleta corporativa y dirección “Cañaveral editorial”; motivos de caña, azúcar, etanol, palma y energía.
5. **Producción**: FastAPI sirve `web/dist` y la API en el mismo origen; Vite hace proxy en desarrollo.
6. **Seguridad**: la clave DeepSeek solo se lee en el servidor; el cliente recibe `configured`, nunca el valor.
7. **Migración**: `app.py` y `streamlit` se retiraron; la cobertura útil vive en API, componentes y E2E.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| Mantener Streamlit | El encargo prohíbe su uso y no permite la identidad buscada. |
| Next.js | Añade SSR y servidor React para una sola página. |
| Jinja + HTMX | Menos toolchain, pero limita la composición y el estado de la consola. |
| Clave en el cliente | Exposición inaceptable del secreto. |
| Backend Node | Duplicaría el RAG y la lógica de errores. |
| Tailwind/UI kit | Favorece un aspecto de plantilla contrario al brief. |

## Consecuencias

- Se añade un toolchain Node solo para desarrollo y build.
- El frontend se prueba con Vitest/RTL y Playwright.
- El repositorio gana `web/package.json` y `web/package-lock.json`.
- `make check` incluye Python y web; CI separa ambos jobs.
- Streamlit deja de ser la entrada documentada; el código legado se retira al final.

## Validación

- `npm run test`, `npm run build`, `pytest tests/api`, `pytest tests/e2e`.
- Matriz responsive 360–1920 y `prefers-reduced-motion`.
- `/api/ask` real y demo; cero claves en respuestas o bundle.
