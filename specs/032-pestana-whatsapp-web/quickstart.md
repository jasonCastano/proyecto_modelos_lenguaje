# Quickstart: validar la pestaña «WhatsApp» (spec 032)

## Requisitos

- Backend y web del proyecto (`make dev` o `uv sync` + `npm ci` en `web/`).
- Para el caso disponible: en el `.env` del proyecto, `VALERIA_WHATSAPP_NUMBER=+57` seguido de los 10 dígitos del
  número de la SIM. Lo llena el integrante; nunca se escribe en otro archivo.

## A. Pruebas automáticas

```powershell
$env:LANGSMITH_TRACING = "false"
uv run pytest tests/unit/test_whatsapp_link.py tests/api/test_whatsapp_link.py
cd web; npx vitest run src/test/WhatsAppPage.test.tsx; cd ..
make check
make e2e
```

Esperado: todo en verde; las pruebas cubren disponible, no disponible, formato inválido, modos y que el número no
aparece en registros.

## B. Contrato del endpoint

```powershell
make app
curl.exe -s http://127.0.0.1:8000/api/channels/whatsapp
```

- Con la variable válida: `available: true`, `web_url`, `app_url` y `qr_svg` presentes (ver
  [contracts/api-whatsapp.md](./contracts/api-whatsapp.md)).
- Sin la variable: `available: false` y los tres campos en `null`.

## C. Recorrido manual

1. Abrir `http://127.0.0.1:8000/` y pulsar **WhatsApp** en la navegación: la página carga en ≤ 2 clics (SC-001).
2. En el computador, pulsar «Abrir WhatsApp»: se abre WhatsApp Web en una pestaña nueva con «Hola, Valer-IA».
3. Escanear el QR con un teléfono: abre la app de WhatsApp con el mismo mensaje.
4. En el teléfono, abrir la web y pulsar «Abrir WhatsApp»: abre la app, no WhatsApp Web.
5. Quitar la variable, reiniciar el backend y recargar: aviso de no disponible y enlace al Agente, sin botón ni QR.

## D. Número fuera del repositorio (SC-003)

La prueba `test_no_colombian_mobile_number_in_versioned_sources` revisa que el código y la configuración
(`web/src/`, `config/`, `openclaw/`, sin carpetas de pruebas) no tengan números móviles colombianos. Para el número
real de la SIM, el integrante lo busca en su equipo (no se escribe en ningún archivo):

```powershell
git grep -n "<los 10 dígitos del número>"
```

Esperado: sin resultados. Una búsqueda genérica de `+57 3…` en todo el repositorio sí encuentra coincidencias
anteriores a esta spec: datos públicos raspados (`data/bronze`, `data/gold`), el número ficticio de pruebas
`+573001234567` y un decimal de `docs/evaluacion_conversacion.json`.

## E. Diseño (skill `design-taste-frontend`)

Desde `web/`, con la app servida: gate, copy-lint y capturas a 1440, 1024, 768 y 390 px, como en la spec 031.
Esperado: la sección cabe en una pantalla, sin desplazamiento horizontal, contraste AA y declaración visible.

## Resultados (2026-11-27)

| Prueba | Resultado |
|---|---|
| Pruebas nuevas de Python (`test_whatsapp_link.py`, unitarias y de contrato) | 31 en verde |
| `ruff check` y `ruff format --check` | En verde |
| Suite completa de Python | En verde (código de salida 0, sin fallos) |
| Vitest | 231 en verde (29 archivos), con `WhatsAppPage.test.tsx` y la navegación de cinco áreas |
| Build de la web | En verde |
| E2E completo (`tests/e2e`) | En verde, con `test_whatsapp.py` y `/whatsapp` en responsive y axe |
| Contrato del endpoint (servidor de prueba en otro puerto, número ficticio) | `available: true`, enlaces sin `+`, QR con `viewBox` |
| Capturas 1440, 1024, 768 y 390 | Sin desplazamiento horizontal; una pantalla a 1440 y 1024; en 768 y 390 la sección crece con el contenido |
| copy-lint de la skill sobre la página renderizada | 0 FAIL, 0 WARN (139 palabras) |
| Gate de la skill (3 rondas) | No se volvió a correr: sus rondas se usaron en la spec 031; se reemplazó por copy-lint, capturas, axe y la prueba de desbordamiento |

Correcciones durante la revisión visual:

- el QR de `segno` traía ancho y alto fijos sin `viewBox` y la web lo recortaba: ahora usa `omitsize=True`;
- con cinco áreas la barra de navegación no cabía entre 1024 y 1279 px: el menú pasa a 1279 px; además, el `<nav>`
  ya no ocupa una columna cuando sus enlaces se ocultan y el botón «Menú» ya no queda oculto por la regla de
  `.btn` (dos fallas que venían de la spec 031 por debajo de 1024 px);
- la barra «Perfil: Visitante» no se muestra en `/whatsapp`, como en la entrada.

Pendiente del integrante: `VALERIA_WHATSAPP_NUMBER` en el `.env` de cada servidor, el recorrido manual C con el
teléfono y la validación con 5 personas (SC-002).
