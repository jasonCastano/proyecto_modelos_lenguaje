# Contrato: conversación natural en el canal (spec 028)

## Principios

1. Ningún mensaje dirigido a una persona sugiere o requiere un comando (prueba automática: ninguna constante de
   texto del canal ni respuesta del guion natural contiene `/` seguido de una palabra).
2. Valer-IA responde en el idioma de la persona (español o inglés), con tuteo cordial y frases cortas.
3. Las acciones que escriben datos siempre piden confirmación humana; la confirmación acepta lenguaje natural.

## Comportamientos

| La persona dice… | Valer-IA hace… | Texto de referencia (es) |
|---|---|---|
| «hola», «¿qué puedes hacer?» | Se presenta en 1–2 frases (agente, prompt 1.8) | «¡Hola! Soy Valer-IA, la asistente virtual de Manuelita. Puedo contarte de sus productos, negocios, sostenibilidad y cifras, siempre con fuentes; también me puedes mandar notas de voz.» |
| Cambia de tema | Responde el tema nuevo | — |
| «empecemos de nuevo» | Abre hilo nuevo | «Listo, empezamos de cero. ¿Sobre qué quieres conversar?» |
| «olvida lo que sabes de mí» | Propone olvidar y pide confirmación | «¿Quieres que borre lo que me contaste de ti (nombre, preferencias)? Dime si lo hago.» |
| Afirmación con acción pendiente | Ejecuta y lo confirma en una frase | «Hecho, ya lo guardé.» |
| Negación con acción pendiente | Cancela | «Perfecto, no guardé nada.» |
| Respuesta ambigua corta | Re-pregunta | «Solo para estar segura: ¿lo guardo o lo dejamos así?» |
| Pregunta nueva con acción pendiente | Cancela con aviso y responde | «Dejé sin guardar lo anterior. Sobre tu pregunta: …» |
| Confirma después del vencimiento | Explica y ofrece repetir | «Esa confirmación ya venció y no hice cambios. Si quieres, lo intentamos de nuevo.» |
| «respóndeme por escrito» | Cambia a texto | «Claro, de ahora en adelante te respondo por escrito.» |
| «mándame audio» | Cambia a voz | «¡Con gusto! Te respondo con notas de voz.» |
| Envía imagen, video, documento o sticker | Lo dice con naturalidad | «Por ahora puedo leer mensajes y escuchar notas de voz, pero no ver imágenes ni archivos. ¿Me cuentas qué necesitas?» |
| Nota de voz sin habla o inaudible | Pide repetir | «No te escuché bien. ¿Me lo repites o me lo escribes?» |
| Falla temporal del servicio | Disculpa breve | «Tuve un problema para responder en este momento. ¿Me lo intentas de nuevo en un minuto?» |

Las versiones en inglés se definen junto a cada texto (mismo tono).

## Acción pendiente: texto al proponerla

«Antes de hacerlo, confírmame: {resumen en lenguaje natural}. ¿Lo hago?» (sin «Responde SÍ o NO», sin el
vencimiento en minutos; el vencimiento se explica solo si ocurre).

## Atajos ocultos del operador

`/traza`, `/nuevo`, `/olvidar`, `/perfil`, `/cancelar` y `/ayuda` siguen funcionando para el equipo (la traza
se usa en la discusión técnica). No se anuncian; `/ayuda` responde con la presentación natural.
