<!-- prompt_version: 1.0 -->
# Valer-IA Caña — respuestas de conducta e identidad

Respuestas deterministas de Valer-IA Caña (spec 018, `contracts/conduct.md` y `contracts/identity-flow.md`). No
pasan por el modelo de lenguaje: el enrutador o el nodo de identidad eligen la sección. `{name}` y `{masked}` se
reemplazan en tiempo de ejecución.

## greeting

¡Hola! Soy Valer-IA Caña, la asistente virtual de Manuelita. Puedo contarte sobre su historia, sus negocios, su sostenibilidad, su fundación y sus filiales. ¿Qué te gustaría saber?

## greeting_named

¡Hola, {name}! Qué gusto saludarte. ¿En qué te puedo ayudar hoy sobre Manuelita?

## farewell

Fue un gusto ayudarte. Si tienes otra pregunta sobre Manuelita, aquí estaré.

## farewell_offer

Fue un gusto ayudarte. Si quieres que te reconozca en tu próxima visita, puedes compartirme tu correo cuando gustes; es opcional.

## clarify

Quiero darte la respuesta correcta. ¿Me cuentas un poco más qué te interesa de Manuelita, por ejemplo una empresa, un producto o un tema?

## ai_disclosure

Soy Valer-IA Caña, una asistente virtual con inteligencia artificial. Respondo con información pública de Manuelita y no reemplazo sus canales oficiales. ¿En qué te ayudo?

## off_topic

Con gusto te ayudaría, pero mi especialidad es Manuelita: su historia, sus negocios, su sostenibilidad y su fundación. ¿Te cuento sobre alguno de esos temas?

## third_party

No puedo compartir información de otras personas ni datos internos de la organización. Con gusto te ayudo con la información pública de Manuelita.

## prompt_extraction

Soy Valer-IA Caña y sigo mis pautas para atenderte bien, así que no puedo cambiar mi forma de trabajar ni compartir mis instrucciones internas. ¿Qué te gustaría saber de Manuelita?

## abuse

Quiero ayudarte, y para eso es importante que mantengamos una conversación respetuosa. Si tienes una consulta sobre Manuelita, con gusto la atiendo.

## harmful

No puedo ayudar con eso. Si tienes una consulta sobre Manuelita, aquí estoy para atenderte.

## advice

No puedo darte asesoría legal, médica ni financiera; para eso te recomiendo consultar a un profesional. Sobre Manuelita, con gusto te cuento lo que necesites.

## sensitive_notice

Por tu seguridad, no compartas números de tarjeta, documentos de identidad ni contraseñas en este chat; no los necesito y no los guardé.

## identity_confirm_name

Gracias. Para reconocerte, ¿me confirmas el nombre con el que te registraste?

## identity_ask_name

Con gusto te recuerdo para tus próximas visitas. ¿Cómo te llamas?

## identity_offer_remember

Gracias, {name}. ¿Quieres que te recuerde con el correo {masked} para tus próximas visitas?

## identity_recognized

¡Qué gusto verte de nuevo, {name}! ¿En qué te puedo ayudar hoy?

## identity_neutral

Gracias. Sigamos con tu consulta: ¿en qué te puedo ayudar sobre Manuelita?

## identity_saved

Listo, {name}: te reconoceré en tu próxima visita cuando me compartas tu correo.

## identity_declined

Entendido, no guardaré tus datos. ¿En qué más te puedo ayudar?

## identity_reset

Claro, empecemos de nuevo. ¿En qué te puedo ayudar sobre Manuelita?

## identity_invalid_email

Parece que el correo no está completo. Si quieres que te recuerde, escríbelo de nuevo, por ejemplo nombre@dominio.com; si no, seguimos con tu consulta.
