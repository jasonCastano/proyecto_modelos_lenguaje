# Implementation Plan: Pestaña «WhatsApp» para hablar con Valer-IA desde la web

**Branch**: `032-pestana-whatsapp-web` | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/032-pestana-whatsapp-web/spec.md`

## Summary

Se agrega una quinta área, **WhatsApp** (`/whatsapp`), a la plataforma web. La página muestra qué es el chat, el modo
del canal (abierto o solo números de prueba), la declaración académica, un botón «Abrir WhatsApp» que abre la
conversación en una pestaña nueva (WhatsApp Web en computador, la aplicación en teléfono) y un QR para pasar al
teléfono. El número nunca entra al repositorio: el backend lo lee de `VALERIA_WHATSAPP_NUMBER` en el `.env` externo,
lo valida en formato E.164 y expone por un endpoint público solo lo necesario para los enlaces y el QR (SVG generado
en el servidor con `segno`). Sin número válido, la página muestra el aviso de «no disponible» y lleva al Agente.
El diseño sigue el sistema de la spec 031 (skill `design-taste-frontend`, colores del logotipo, Archivo y una foto
de producto con licencia libre).

## Technical Context

**Language/Version**: Python 3.14 (backend FastAPI) y TypeScript 5.9 con React 19 (web, Vite 7)

**Primary Dependencies**: FastAPI (existente); **`segno`** (nueva, BSD-3-Clause, Python puro, sin dependencias) para
el QR en SVG; en la web, ninguna dependencia nueva

**Storage**: N/A. El número vive solo en el `.env` del proyecto (fuera de Git); el modo se lee del `.env` del
gateway como ya hace `ops.channel_mode`

**Testing**: pytest (contrato del endpoint y validación), Vitest + Testing Library (página, navegación y estados),
Playwright e2e (navegación, enlace en pestaña nueva, responsive y axe), gate de la skill `design-taste-frontend`

**Target Platform**: navegadores de escritorio y móviles (360 a 1920 px); servidor Windows del equipo y el de
respaldo

**Project Type**: aplicación web (backend FastAPI + SPA React)

**Performance Goals**: la pestaña responde en menos de 1 s en loopback; llegar al chat en ≤ 2 clics (SC-001)

**Constraints**: ningún número en archivos versionados ni en registros (constitución §9 y §10); el endpoint no
requiere token pero solo expone el enlace público; contraste AA, sin desplazamiento horizontal, foco visible,
movimiento reducido (§3.7); el QR no usa servicios externos (FR-006)

**Scale/Scope**: 1 área nueva, 1 endpoint, 1 variable de entorno, 1 dependencia; ~6 archivos nuevos y ~8 editados

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla | Cómo se cumple | Estado |
|---|---|---|
| §9 Número: ningún número entra al repositorio | `VALERIA_WHATSAPP_NUMBER` solo en el `.env` externo; `.env.example` lleva la línea vacía; prueba que el repositorio no contiene números E.164 de Colombia en `web/src` ni en la configuración | ✅ |
| §10 Seudónimos: el número no se registra | El endpoint no escribe registros con el número; un formato inválido se registra como «formato inválido» sin el valor | ✅ |
| §3.7 Aplicación web: identidad, accesibilidad, declaración | Sistema de la spec 031, contraste AA, foco, movimiento reducido, sin desplazamiento horizontal, declaración visible | ✅ |
| §3.7 Sitio de producto (spec 031): sin logotipo, figura ni tipografía de Manuelita; fotos con licencia citadas | Foto existente de `web/public/media/fotos/` con su crédito; ningún elemento de la marca | ✅ |
| La app no escribe en `data/` ni en el repositorio | El endpoint solo lee variables y el `.env` del gateway | ✅ |
| Dependencias por `uv`; `uv.lock` versionado | `uv add segno`; el lock se actualiza en el mismo commit | ✅ |
| Cambio tecnológico → `CONSTITUTION.md` en el mismo commit | Enmienda **MINOR 2.10.0** (§3.7: quinta área, endpoint público del enlace, `segno`) y ADR 0038; requiere la aprobación de ambos integrantes | ⚠️ pendiente de aprobación |
| Autoría (§4.3) | Commit, push y PR solo con autorización explícita del integrante, como Robertto48 | ✅ |

Sin violaciones injustificadas. La enmienda es un requisito del proceso, no una violación.

**Re-check post-diseño (Phase 1)**: el contrato expone `web_url`, `app_url` y `qr_svg`, que contienen el número
porque WhatsApp lo necesita para abrir el chat; es el número público del proyecto y no queda en el repositorio ni en
registros. Se mantiene ✅.

## Project Structure

### Documentation (this feature)

```text
specs/032-pestana-whatsapp-web/
├── spec.md
├── plan.md              # este archivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── api-whatsapp.md  # GET /api/channels/whatsapp
│   └── ui-contract.md   # área /whatsapp
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (no lo crea este comando)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── channels/whatsapp_link.py     # nuevo: validación E.164, enlaces, QR (segno) y modo
├── api.py                        # + GET /api/channels/whatsapp (público, sin token)
└── api_models.py                 # + WhatsAppLink

web/src/
├── lib/router.ts                 # + "/whatsapp" en Route y ROUTES
├── lib/api.ts                    # + fetchWhatsAppLink()
├── lib/types.ts                  # + WhatsAppLink
├── App.tsx                       # + título y render de <WhatsApp />
├── components/shell/AppShell.tsx # + área «WhatsApp» en AREAS
├── components/home/Faq.tsx       # + enlace a /whatsapp en «¿Puedo usarla por WhatsApp?»
├── pages/WhatsApp.tsx            # nuevo: la página
├── styles/whatsapp.css           # nuevo: estilos de la página con los tokens de site.css
└── test/WhatsAppPage.test.tsx    # nuevo

tests/
├── api/test_whatsapp_link.py     # nuevo: contrato del endpoint
├── unit/test_whatsapp_link.py    # nuevo: validación, enlaces, modo, sin número en registros
└── e2e/test_whatsapp.py          # nuevo: navegación, pestaña nueva, responsive y axe

.env.example                      # + VALERIA_WHATSAPP_NUMBER= (vacía)
docs/despliegue.md                # + fila de la variable en §2
docs/decisions/0038-pestana-whatsapp-web.md
CONSTITUTION.md                   # 2.10.0 (§3.7)
README.md                         # + fila /whatsapp en la tabla de áreas
```

**Structure Decision**: se mantiene la estructura existente (backend en `src/proyecto_modelos_lenguaje/`, SPA en
`web/`). La lógica del enlace va en `channels/` porque pertenece al canal de WhatsApp; la página sigue el patrón de
`pages/` de las otras cuatro áreas.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Nueva dependencia `segno` | El QR debe generarse en la plataforma sin servicios externos (FR-006) | Un QR hecho a mano es frágil y no verificable; un servicio externo recibiría el número |
