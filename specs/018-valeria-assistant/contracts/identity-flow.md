# Contrato: reconocimiento conversacional (spec 018)

Antes de redactar el mensaje, el servicio calcula un `identity_event`. Luego el nodo `identify`, al inicio de los
dos grafos, decide la respuesta. Ninguna de estas respuestas llama al modelo de lenguaje. Los textos salen de
`prompts/conduct.md` (sección «identidad»).

## Detección (servicio, antes de `redact_pii`)

| Mensaje | `identity_event` |
|---------|------------------|
| Contiene exactamente un correo válido y una frase de presentación o intención («soy», «mi correo es», «me registré», «recuérdame») o el correo solo | `{kind: "email", fingerprint, registered, locked}` |
| Contiene un correo de otra persona («el correo de mi jefe es…») o más de un correo | ninguno: el correo se redacta como hoy |
| «no soy X», «soy otra persona», «empecemos de nuevo», «nuevo cliente» | `{kind: "reset"}` |
| Llega con el `stage` en `awaiting_name_*` | `{kind: "name_reply"}` (el texto se compara en el nodo) |

## Máquina de estados (`identity.stage`)

```text
none ──email registrado (no bloqueado)──▶ awaiting_name_confirm
        respuesta: «Gracias. Para reconocerte, ¿me confirmas el nombre con el que te registraste?»
none ──email nuevo──▶ (perfil sin nombre) awaiting_name_new: «¿Cómo te llamas, para recordarte?»
                      (perfil con nombre) → acción remember_client (HITL)
none ──email bloqueado──▶ none: respuesta igual que la de «correo nuevo» (no revela nada)

awaiting_name_confirm ──nombre coincide──▶ recognized
        user_id del hilo := user_id vinculado; client = {user_id, recognized: true, name}
        respuesta: «¡Qué gusto verte de nuevo, {nombre}! ¿En qué te ayudo hoy?»
awaiting_name_confirm ──no coincide──▶ none (attempts+1; IdentityFailures+1)
        respuesta: «Gracias. Sigamos con tu consulta: ¿en qué te puedo ayudar sobre Manuelita?»  (no revela)
        attempts ≥ 3 ⇒ no se procesan más correos en este hilo (respuesta neutra)

awaiting_name_new ──nombre──▶ acción remember_client(name) (HITL, pregunta conversacional)
        aprobada ⇒ profile.name + IdentityLink; «Listo, {nombre}: te reconoceré en tu próxima visita.»
        rechazada ⇒ nada se guarda; «Entendido, no guardaré tus datos.»

cualquiera ──reset──▶ none; client = {reset: true}; «Claro, empecemos de nuevo. ¿En qué te ayudo?»
        el navegador crea un cliente anónimo nuevo y un hilo nuevo
```

- **Comparación de nombres**: se normalizan ambos (NFKD sin tildes, `casefold`, espacios colapsados). Coinciden si
  son iguales o si el primer nombre es igual.
- **Mensajes en otras etapas**: si un `name_reply` no parece un nombre (más de 5 palabras o una pregunta), se sale
  de la etapa con `attempts+1` y el mensaje se atiende como una pregunta normal.
- **Oferta de recordar** (`identity.offered`, una vez por hilo): en la despedida (`FAREWELL`) de un visitante
  anónimo, o cuando el agente propone `save_profile`, se agrega una línea que invita a compartir el correo.

## Olvidar

Cuando se aprueba `forget_memory`, además de las preferencias y el perfil se borran todos los `IdentityLink` del
`user_id` y la etapa vuelve a `none`.

## Garantías (pruebas)

- El correo en claro no aparece en el estado del hilo, el Store, `turns.jsonl`, `voice.jsonl` ni la respuesta HTTP.
  Solo `masked` aparece en la respuesta del mismo turno.
- Las respuestas ante un nombre incorrecto, un correo bloqueado o un correo nuevo no permiten saber si el correo
  existe: el texto es neutro y no se revela ningún dato del perfil.
- El `user_id` reconocido solo llega al navegador después de confirmar el nombre.
