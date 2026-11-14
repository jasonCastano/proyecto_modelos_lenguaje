# ADR 0022 — Valer-IA Caña: asistente para visitantes, identidad conversacional y conducta

- **Estado**: aceptada
- **Fecha**: 2026-11-14
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0018 (memoria de perfil), ADR 0019 (blindaje), ADR 0020 (voz), ADR 0021 (avatar);
  `specs/018-valeria-assistant/` (spec, plan, research R1–R9, contracts, tasks).

## Contexto

El chat se veía y se comportaba como una demostración académica:
- casos de demo, selector de variante, trazas, chips de ruta y tarjetas técnicas de aprobación;
- el navegador reutilizaba para siempre el mismo cliente anónimo (`localStorage`), así que cada visitante heredaba
  la memoria del anterior y no había forma de empezar desde cero.

El equipo pidió:
- un agente conversacional y natural, con nombre propio, **Valer-IA Caña**;
- que se presente al entrar;
- que reconozca a un cliente que vuelve por su correo, sin hacerlo obligatorio;
- que maneje con profesionalismo las preguntas fuera de tema y las solicitudes malintencionadas.

## Decisión

1. **Personaje y transparencia**:
   - Valer-IA Caña (`prompts/agent.md` 1.4, `prompts/conduct.md` 1.0) tiene el tono de un agente oficial, pero se
     declara IA y no se presenta como canal autorizado (CONSTITUTION §10).
   - La bienvenida (`prompts/welcome.md` 1.0, `GET /api/welcome`) es determinista, no usa el LLM y cita dos unidades
     del oro verificadas por prueba.
2. **Visita limpia**: el cliente anónimo y el hilo viven en `sessionStorage`, así que cada visita nueva empieza
   desde cero. La clave antigua de `localStorage` se borra.
3. **Identidad conversacional determinista** (`agent/identity.py`, nodo `identify` al inicio de los dos grafos):
   - **Huella del correo**: el correo se detecta antes de redactar el mensaje y se convierte en
     `HMAC-SHA256(clave, correo normalizado)`. El correo en claro no llega al hilo, al modelo, a las trazas, a
     los registros ni al Store.
   - **Correo registrado**: se pide confirmar el nombre registrado. Si coincide, el hilo adopta al cliente
     reconocido.
   - **Correo nuevo**: se ofrece recordarlo con la acción `remember_client`, que requiere aprobación humana en
     forma de respuestas rápidas.
   - **Ante un fallo**, la respuesta es neutra y no revela nada:
     - 3 fallos por hilo cierran el reconocimiento en ese hilo;
     - 5 fallos en 1 hora bloquean la huella y la tratan como un correo nuevo.
   - «Empecemos de nuevo» o «No soy Ana» (si estaba reconocido) inician un cliente anónimo nuevo.
   - «Olvidar» también borra el vínculo del correo.
4. **Conducta por reglas**:
   - El enrutador agrega `scope_reason` (`off_topic`, `third_party`, `prompt_extraction`, `abuse`, `harmful`,
     `advice`), detectado con patrones que no bloquean el vocabulario de la industria («quema de caña», «demanda
     de azúcar», «política antifraude»).
   - Cada motivo tiene una respuesta determinista y hay un aviso cuando el visitante comparte datos sensibles.
   - La batería `agent conduct`, de 24 casos, lo mide.
5. **Vista normal y vista técnica**: la vista normal muestra solo lo del visitante. `?vista=tecnica` conserva toda la
   demostración de la rúbrica.

## Alternativas consideradas

- **Herramienta del LLM `identify_client(email)`**: rechazada. Expone el correo al modelo y deja la seguridad a su
  criterio.
- **PIN o código de un solo uso**: es más seguro, pero exige recordar un PIN o enviar correos (servicio externo).
  Queda como mejora si el perfil llega a guardar datos más sensibles.
- **Botón «Nuevo cliente»**: rechazado por el equipo; la interacción debe ser conversacional.
- **Generar la bienvenida con el LLM**: rechazada por latencia, costo y riesgo de afirmar datos sin cita.
- **Solo instrucciones en el prompt para la conducta**: insuficiente para garantizar respuestas estables ante datos
  de terceros o la extracción del prompt.

## Consecuencias

- La verificación al reconocer es ligera (correo + nombre). Es adecuada para el perfil actual (nombre, trabajo,
  cargo, ciudad y preferencias), pero no es una autenticación fuerte.
- La clave HMAC (`MANUELITA_IDENTITY_KEY` o `identity.key` en el directorio de estado) no debe cambiar: si cambia,
  los registros previos dejan de reconocerse.
- Los turnos de identidad y de conducta no llaman al LLM: son instantáneos y sin costo.
- El enrutador se vuelve a evaluar para descartar regresiones (`docs/evaluacion_conducta.md`).
