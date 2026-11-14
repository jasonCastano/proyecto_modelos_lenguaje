# Contrato de UI: vista de visitante y vista técnica (spec 018)

## Selección de vista

- `?vista=tecnica` activa la vista técnica y la guarda en `sessionStorage["manuelita.view"]`.
- `?vista=normal` vuelve a la vista normal.
- Por defecto se usa la vista normal.

## Elementos por vista

| Elemento | Normal | Técnica |
|----------|:------:|:-------:|
| Bienvenida de Valer-IA (`data-testid="welcome-message"`) | ✅ | ✅ |
| Conversación, campo de mensaje, avatar, controles de voz | ✅ | ✅ |
| Fuentes citadas por respuesta | ✅ | ✅ |
| Respuestas rápidas de consentimiento (`quick-replies`) | ✅ | — |
| Tarjeta técnica de aprobación (`ApprovalCard`) | — | ✅ |
| Selector de variante, «Nueva conversación», trazas, Qdrant/numpy | — | ✅ |
| Conversaciones recientes, casos de demo | — | ✅ |
| Chip de ruta, fragmentos recuperados, métricas por turno, aviso de anomalías | — | ✅ |
| Perfil y preferencias guardados («Tu perfil…», «Olvidar») | — | ✅ (en la normal se gestiona conversando) |

## Bienvenida (`WelcomeMessage`)

- **Carga y visualización**: al montar el chat se consulta `/api/welcome` y se muestra como primer mensaje de
  Valer-IA, con sus fuentes, aunque haya un hilo restaurado en la misma visita: queda arriba del historial.
- **Voz**: si `sessionStorage["manuelita.visit.welcomed"]` no existe, se llama a `voice.speak(text)` y se marca.
  - Si el navegador bloquea el audio, se reproduce en el primer `pointerdown` o `keydown`, salvo que ya se haya
    enviado un mensaje.
  - Enviar un mensaje detiene la bienvenida.
- **Sin `/api/welcome`**: se muestra un saludo mínimo local: «¡Hola! Soy Valer-IA Caña, la asistente virtual de
  Manuelita. ¿En qué te ayudo?».

## `QuickReplies` (acciones pendientes en vista normal)

| Acción | Botón aprobar | Botón rechazar |
|--------|---------------|----------------|
| `remember_client` | «Sí, recuérdame» | «No, gracias» |
| `save_profile` | «Sí, guárdalo» | «No, gracias» |
| `save_preference` | «Sí, guárdala» | «No» |
| `forget_memory` | «Sí, olvida mis datos» | «Cancelar» |
| `export_conversation` | «Sí, descárgala» | «No» |

- La pregunta de Valer-IA aparece como mensaje.
- Los botones llaman a `resume(approve | reject)`; la vista normal no ofrece «editar».
- Mientras la acción está pendiente, el campo de mensaje se deshabilita con el texto «Responde a la pregunta de
  Valer-IA».

## Identidad en el navegador

- `ChatResponse.client.user_id` distinto del actual se guarda en `sessionStorage["manuelita.visit.user"]`.
- `client.reset` genera un `anon-…` nuevo, limpia el hilo y deja la bienvenida visible sin volver a decirla.
- La clave antigua `localStorage["manuelita.chat.user"]` se elimina al cargar.

## Textos visibles

Los encabezados y etiquetas del chat dicen «Valer-IA Caña», no «asistente RAG». Los demás textos de la interfaz
del chat no se cambian.
