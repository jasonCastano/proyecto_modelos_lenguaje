# Tasks: Pestaña «WhatsApp» para hablar con Valer-IA desde la web

**Input**: Design documents from `/specs/032-pestana-whatsapp-web/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-whatsapp.md, contracts/ui-contract.md,
quickstart.md

**Tests**: incluidas. La spec las pide en SC-006 (pruebas nuevas para las tres historias) y la constitución exige
`make check` en verde antes de cada commit.

**Organization**: tareas agrupadas por historia para implementar y probar cada una por separado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1, US2, US3)

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/`; pruebas en `tests/unit/`, `tests/api/`, `tests/e2e/`
- Web: `web/src/`; pruebas en `web/src/test/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencia, variable y ruta nueva.

- [X] T001 Agregar la dependencia `segno` con `uv add segno` (actualiza `pyproject.toml` y `uv.lock`; nunca `pip`)
- [X] T002 [P] Agregar la línea vacía `VALERIA_WHATSAPP_NUMBER=` con un comentario «número de la SIM en formato
  E.164, `+57` y 10 dígitos; nunca en otro archivo» en `.env.example`
- [X] T003 [P] Agregar `"/whatsapp"` a `Route` y a `ROUTES` en `web/src/lib/router.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el contrato del endpoint, que necesitan las tres historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T004 [P] Escribir pruebas unitarias (deben fallar primero) en `tests/unit/test_whatsapp_link.py`:
  - `normalize_number`: acepta `+57` + 10 dígitos y quita espacios; rechaza sin `+`, con letras, con guiones y con
    menos de 8 dígitos (regla `^\+[1-9]\d{7,14}$`);
  - `build_link`: `web_url` = `https://web.whatsapp.com/send?phone=<dígitos>&text=Hola%2C%20Valer-IA` y `app_url` =
    `https://wa.me/<dígitos>?text=Hola%2C%20Valer-IA`, sin `+`;
  - invariante: si `available` es `false`, `web_url`, `app_url` y `qr_svg` son `None`;
  - un número inválido registra `whatsapp_link: formato inválido` y el valor no aparece en el registro (`caplog`);
  - usar solo números ficticios generados en la prueba, nunca uno real.
- [X] T005 [P] Escribir pruebas de contrato (deben fallar primero) en `tests/api/test_whatsapp_link.py`:
  `GET /api/channels/whatsapp` responde 200 sin `X-Channel-Token`, con `Cache-Control: no-store`, y los casos de
  `contracts/api-whatsapp.md` (variable válida, ausente, vacía e inválida; `mode` `open`, `closed` y `unknown` con
  un `OPENCLAW_STATE_DIR` temporal y su `.env`)
- [X] T006 Implementar `src/proyecto_modelos_lenguaje/channels/whatsapp_link.py`:
  - `ENV_VAR = "VALERIA_WHATSAPP_NUMBER"` y `MESSAGE = "Hola, Valer-IA"`;
  - `normalize_number(raw) -> str | None` con la regla E.164 de `research.md` R2;
  - `build_link(env=os.environ) -> WhatsAppLinkData` con `available`, `mode`, `message`, `web_url`, `app_url` y
    `qr_svg`;
  - modo con `ops.channel_mode()`: `"open"` si la política es abierta, `"closed"` si hay `.env` del gateway con otra
    política, `"unknown"` sin `.env`;
  - QR con `segno.make(app_url, error="m")` y SVG con borde 4, `dark="#14240f"`, `light="#ffffff"`, sin
    declaración XML;
  - registro `whatsapp_link: formato inválido` sin el valor cuando el número no pasa la regla.
- [X] T007 Agregar el modelo `WhatsAppLink` (campos de `data-model.md`; `mode` como
  `Literal["open", "closed", "unknown"]`; `web_url`, `app_url` y `qr_svg` opcionales) en
  `src/proyecto_modelos_lenguaje/api_models.py`
- [X] T008 Agregar `GET /api/channels/whatsapp` (público, sin `_channel_guard`, `Cache-Control: no-store`) en
  `src/proyecto_modelos_lenguaje/api.py`, que devuelve `build_link()`
- [X] T009 [P] Agregar el tipo `WhatsAppLink` en `web/src/lib/types.ts` y `fetchWhatsAppLink()` en
  `web/src/lib/api.ts`, con el mismo manejo de errores que las otras llamadas

**Checkpoint**: `uv run pytest tests/unit/test_whatsapp_link.py tests/api/test_whatsapp_link.py` en verde.

---

## Phase 3: User Story 1 - Abrir el chat de WhatsApp desde la web (Priority: P1) 🎯 MVP

**Goal**: quinta área «WhatsApp» con el botón que abre el chat en una pestaña nueva.

**Independent Test**: desde la navegación, abrir `/whatsapp`, pulsar «Abrir WhatsApp» y comprobar la pestaña nueva
hacia WhatsApp con «Hola, Valer-IA».

### Tests for User Story 1

- [X] T010 [P] [US1] Escribir pruebas (deben fallar primero) en `web/src/test/WhatsAppPage.test.tsx`:
  - con `available: true`: h1 «Habla con Valer-IA por WhatsApp», lead, estado del canal, declaración «Proyecto
    académico con IA. No es un canal oficial de Manuelita.» y requisitos;
  - el botón `[data-testid=wa-open]` es un `<a>` con `target="_blank"`, `rel="noopener noreferrer"` y el texto oculto
    «(se abre en una pestaña nueva)»;
  - en escritorio su `href` es `web_url`; con `navigator.userAgentData.mobile = true` o un agente `iPhone`, `app_url`;
  - `mode: "open"` muestra «Abierto: cualquier número puede escribir»; `"closed"`, «Solo números de prueba del
    equipo»; `"unknown"`, nada.
- [X] T011 [P] [US1] Actualizar `web/src/test/App.test.tsx` (o la prueba de navegación existente): `AREAS` tiene cinco
  entradas en el orden Entrada, Agente, Planificación, Evidencia, WhatsApp; `/whatsapp` marca `aria-current="page"`
  y el título es «WhatsApp · Valer-IA»

### Implementation for User Story 1

- [X] T012 [US1] Crear `web/src/pages/WhatsApp.tsx` según `contracts/ui-contract.md`:
  - `main > section#whatsapp` con `data-enter` y hero split;
  - h1 `#whatsapp-title` con `tabIndex -1`;
  - estados cargando (`aria-busy`), disponible, no disponible y error de red;
  - elección del enlace por dispositivo (`research.md` R3);
  - ícono real `/media/iconos/whatsapp.svg` junto al botón;
  - foto `PHOTOS.cana` con `data-source="stand-in"`, `width`, `height` y `sizes`.
- [X] T013 [P] [US1] Crear `web/src/styles/whatsapp.css` con los tokens de `site.css` y `tokens.css` (verde
  `--p-action` para el botón, Archivo, `--wrap`, `--gutter`, una sección por pantalla, `min-height` en móvil, sin
  desplazamiento horizontal de 360 a 1920 y sin animación con movimiento reducido), e importarlo en
  `web/src/main.tsx` después de `home.css`
- [X] T014 [US1] Agregar `{ route: "/whatsapp", label: "WhatsApp" }` al final de `AREAS` en
  `web/src/components/shell/AppShell.tsx`
- [X] T015 [US1] En `web/src/App.tsx`, agregar el título «WhatsApp · Valer-IA» y renderizar `<WhatsApp />` en
  `/whatsapp`
- [X] T016 [P] [US1] En `web/src/components/home/Faq.tsx`, hacer que la respuesta de «¿Puedo usarla por WhatsApp?»
  enlace a `/whatsapp` con el `Link` del router («Ve a la pestaña WhatsApp»), y ajustar `web/src/test/HomePage.test.tsx`
  si la prueba revisa ese texto

**Checkpoint**: la pestaña funciona sola con el número configurado; `npx vitest run` en verde.

---

## Phase 4: User Story 2 - Pasar del computador al teléfono (Priority: P2)

**Goal**: el QR del chat junto al botón.

**Independent Test**: escanear el QR con un teléfono y comprobar que abre el chat con «Hola, Valer-IA».

### Tests for User Story 2

- [X] T017 [P] [US2] Ampliar `web/src/test/WhatsAppPage.test.tsx`: con `available: true`, `[data-testid=wa-qr]` tiene
  `role="img"`, `aria-label="Código QR para abrir el chat en tu teléfono"`, contiene el SVG recibido y la leyenda
  «Escanéalo con la cámara de tu teléfono»
- [X] T018 [P] [US2] Ampliar `tests/unit/test_whatsapp_link.py`: el SVG de `qr_svg` decodifica el `app_url`
  (comprobar con `segno` que el contenido codificado es exactamente `app_url`) y no lleva declaración XML

### Implementation for User Story 2

- [X] T019 [US2] Agregar a `web/src/pages/WhatsApp.tsx` la tarjeta del QR sobre la foto (`.wa-visual`), insertando el
  SVG del servidor (solo si `available`), con la leyenda y la etiqueta accesible del contrato
- [X] T020 [US2] Agregar a `web/src/styles/whatsapp.css` el estilo de la tarjeta del QR (fondo blanco, radio de la
  spec 031, QR de al menos 200 px en escritorio y 180 px en móvil, contraste suficiente para escanear)

**Checkpoint**: US1 y US2 funcionan; el QR se lee con un teléfono.

---

## Phase 5: User Story 3 - Canal no disponible (Priority: P3)

**Goal**: sin número válido, aviso y enlace al Agente, nunca un enlace roto.

**Independent Test**: arrancar sin `VALERIA_WHATSAPP_NUMBER` y comprobar el aviso, el enlace a `/agente` y la ausencia
de botón y QR.

### Tests for User Story 3

- [X] T021 [P] [US3] Ampliar `web/src/test/WhatsAppPage.test.tsx`:
  - con `available: false`: «El chat de WhatsApp no está disponible en este momento», enlace «Habla con Valer-IA
    aquí» a `/agente`, sin `[data-testid=wa-open]`, sin `[data-testid=wa-qr]` y sin `[data-testid=wa-mode]`;
  - con error de red: el mismo aviso y el botón «Reintentar», que vuelve a llamar a `fetchWhatsAppLink()`.

### Implementation for User Story 3

- [X] T022 [US3] Completar en `web/src/pages/WhatsApp.tsx` los estados no disponible y error de red (aviso, enlace
  al Agente con el `Link` del router y «Reintentar»)

**Checkpoint**: las tres historias funcionan por separado.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T023 [P] Crear `tests/e2e/test_whatsapp.py`:
  - la navegación muestra «WhatsApp» y llega a `/whatsapp` en un clic;
  - el enlace tiene `target="_blank"`;
  - sin desplazamiento horizontal en 360, 768, 1024, 1440 y 1920;
  - axe sin violaciones serias;
  - el servidor de prueba no tiene la variable, así que se valida el estado no disponible; el disponible se cubre
    con Vitest.
- [X] T024 [P] Agregar en `tests/unit/test_whatsapp_link.py` una prueba de SC-003: ningún archivo de `web/src/`,
  `config/` ni `openclaw/` contiene un número móvil colombiano (`\+?57 ?3\d{2} ?\d{3} ?\d{4}`)
- [X] T025 [P] Escribir `docs/decisions/0038-pestana-whatsapp-web.md` con las decisiones R1 a R8 de `research.md`
  (autor Roberto José Guerrero; requiere la aprobación de ambos integrantes)
- [X] T026 Enmendar `CONSTITUTION.md` a **2.10.0** (MINOR) en §3.7 con la quinta área `/whatsapp`, el endpoint público
  `GET /api/channels/whatsapp` (solo el enlace y el QR, número desde `VALERIA_WHATSAPP_NUMBER` fuera de Git) y la
  dependencia `segno`; actualizar la versión en las dos líneas y agregar la fila del historial
- [X] T027 [P] Agregar `VALERIA_WHATSAPP_NUMBER` (backend, formato E.164 con `+57`) a la tabla del §2 de
  `docs/despliegue.md`
- [X] T028 [P] Agregar la fila `/whatsapp` a la tabla de áreas de `README.md`
- [X] T029 Correr el gate, copy-lint y capturas de la skill `design-taste-frontend` desde `web/` (1440, 1024, 768 y
  390 px) y corregir lo que corresponda en `web/src/pages/WhatsApp.tsx` y `web/src/styles/whatsapp.css`
  (hecho con copy-lint, capturas, axe y desbordamiento; el gate de 3 rondas no se volvió a correr, ver quickstart)
- [X] T030 Correr `make check` y `make e2e` con `LANGSMITH_TRACING=false`, más el recorrido manual de `quickstart.md`
  (secciones B a D), y anotar los resultados en `specs/032-pestana-whatsapp-web/quickstart.md`
- [X] T031 Preparar el mensaje del commit `feat(web): pestaña WhatsApp para hablar con Valer-IA (spec 032)` y la
  descripción del PR (aviso de la enmienda 2.10.0 y el ADR 0038). El commit, el push y el PR solo se hacen con
  autorización explícita del integrante, como Robertto48 y sin coautor (preparados; falta la autorización)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de T001 (segno); bloquea las tres historias.
- **US1 (Phase 3)**: depende de la Phase 2 y de T003.
- **US2 (Phase 4)**: depende de T012 (la página existe).
- **US3 (Phase 5)**: depende de T012.
- **Polish (Phase 6)**: después de las historias; T029 y T030 al final; T031 lo último.

### User Story Dependencies

- **US1 (P1)**: independiente; es el MVP.
- **US2 (P2)**: agrega el QR a la página de US1; se prueba por separado.
- **US3 (P3)**: agrega los estados sin número a la página de US1; se prueba por separado. US2 y US3 pueden hacerse en
  paralelo si no editan el mismo bloque de `WhatsApp.tsx` al mismo tiempo.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- Backend antes que la página; la página antes que los estilos finos.

### Parallel Opportunities

- T002 y T003; T004, T005 y T009.
- En US1: T010, T011, T013 y T016.
- En Polish: T023, T024, T025, T027 y T028.

---

## Parallel Example: User Story 1

```text
T010 Pruebas de la página en web/src/test/WhatsAppPage.test.tsx
T011 Prueba de la navegación en web/src/test/App.test.tsx
T013 Estilos en web/src/styles/whatsapp.css
T016 Enlace de la pregunta frecuente en web/src/components/home/Faq.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 y Phase 2 (endpoint probado).
2. Phase 3 (pestaña y botón).
3. **Parar y validar**: con el número en el `.env`, abrir el chat desde el computador.

### Incremental Delivery

1. MVP con US1.
2. US2: el QR para la sustentación con teléfonos de invitados.
3. US3: el aviso cuando el canal no está configurado (servidor de respaldo).
4. Polish: e2e, ADR, constitución, gate de diseño y verificación completa.

## Notes

- Ningún número real en pruebas, ejemplos ni documentos: solo números ficticios generados en la prueba o el marcador
  `57XXXXXXXXXX`.
- El `.env` lo llena el integrante; la implementación solo toca `.env.example`.
- Marcar cada tarea con `[X]` al terminarla.
