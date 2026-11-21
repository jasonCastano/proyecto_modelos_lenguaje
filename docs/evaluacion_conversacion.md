# Evaluación de naturalidad de Valer-IA Caña

Generado por `agent converse --mode real` el 2026-11-21 (spec 020, `prompts/converse.md` v1.0, 10 hilos por mensaje en la repetición).

Las metas duras (SC-001 a SC-006 y SC-012) deben cumplirse; las de calidad se comparan con la línea base del modo de guiones (spec 019).

## Métricas

| Criterio | Meta | chain (guiada) | chain (guiones) | agent (guiada) | agent (guiones) |
|---|---|---:|---:|---:|---:|
| SC-001 pares del hilo con similitud ≤ 0.5 | 100 % | 100% | 78% | 100% | 81% |
| SC-001 similitud máxima en un hilo | ≤ 0.5 | 0.362 | 1.0 | 0.4 | 1.0 |
| SC-002 respuestas distintas entre hilos (mínimo) | ≥ 80 % | 70% | 10% | 70% | 10% |
| SC-003 puentes repetidos | 0 | 0 | 0 | 0 | 0 |
| SC-003 puentes por turno fuera de tema | ≤ 50 % | 14% | 0% | 13% | 0% |
| SC-004 puentes con molestia, cierre o rechazo | 0 | 0 | 0 | 0 | 0 |
| SC-005 hechos externos, contactos o promesas | 0 | 0 | 0 | 1 | 1 |
| SC-006 respuestas de seguridad fijas | 100 % | 100% | 100% | 100% | 100% |
| SC-008 comentarios sociales acompañados | ≥ 90 % | 100% | 100% | 100% | 100% |
| SC-009 mínimos con 2 frases o menos | ≥ 90 % | 100% | 25% | 100% | 25% |
| SC-010 correcciones sin nueva aclaración | 100 % | 100% | 100% | 100% | 100% |
| SC-010 referencias a turnos previos | ≥ 80 % | 100% | 0% | 100% | 100% |
| SC-011 primera palabra p90 (ms), todos los turnos | < 3000 | 6655.3 | 5803.2 | 7922.4 | 8307.8 |
| SC-011 p90 (ms), turnos sin búsqueda | < 3000 | 3583.5 | 1733.2 | 3925.4 | 2457.8 |
| SC-012 respuesta con el modelo caído | 100 % | 100% | 67% | 100% | 67% |
| Turnos regenerados tras la revisión | — | 1% | 0% | 1% | 0% |
| Turnos con respaldo | — | 0% | 0% | 0% | 0% |
| Comprobaciones por turno de las guionadas | — | 98% | 83% | 98% | 83% |

## Juez (SC-007)

| Dimensión | chain (guiada) | chain (guiones) | agent (guiada) | agent (guiones) |
|---|---:|---:|---:|---:|
| Naturalidad | 3.77 | 2.8 | 3.84 | 3.14 |
| Empatía | 3.86 | 3.02 | 3.9 | 3.3 |
| Pertinencia | 4.33 | 3.29 | 4.43 | 3.58 |

Calificación: llm. Meta: ≥ 4 y mayor que la línea base.

## Metas duras

- **chain**: SC-001 ✅, SC-002 ❌, SC-003 ✅, SC-004 ✅, SC-005 ✅, SC-006 ✅, SC-012 ✅, E-SC-003 ❌, E-SC-004 ✅, E-SC-008 ✅, E-SC-001 ❌, E-SC-002 ❌, E-SC-006 ✅
- **agent**: SC-001 ✅, SC-002 ❌, SC-003 ✅, SC-004 ✅, SC-005 ❌, SC-006 ✅, SC-012 ✅, E-SC-003 ❌, E-SC-004 ❌, E-SC-008 ✅, E-SC-001 ❌, E-SC-002 ❌, E-SC-006 ❌
  - «Ese dato social me interesa mucho. ¿De qué documento sale esa cifra?» → external_fact: La cifra sale del Informe de Sostenibilidad de Manuelita 2023-2024, publicado en el sitio web de la empresa, que reporta 55.575 millones de pesos de inversión social en 2024 frente a 46.933 millones e

## Entrega (spec 021)

| Métrica | Meta | chain (por frases) | chain (completa) | agent (por frases) | agent (completa) |
|---|---|---:|---:|---:|---:|
| Primera frase p90, conversación (ms) | < 3000 | 3583.5 | 4281.8 | 3925.4 | 4736.4 |
| Primera frase p90, búsqueda (ms) | ≤ base + 1000 | 8923.7 | 7328.4 | 15449.7 | 14023.8 |
| Respuesta completa p90, conversación (ms) | ≤ base × 1.1 | 3795.6 | 4281.8 | 4199.3 | 4736.4 |
| Respuesta completa p90, búsqueda (ms) | ≤ base × 1.1 | 9220.4 | 8267.3 | 19421.0 | 14812.4 |
| Turnos con texto retirado | 0 | 3 | 5 | 4 | 5 |
| Turnos con frases descartadas | — | 6% | 0% | 8% | 0% |

## Repetición entre hilos

| Mensaje | Distintas |
|---|---:|
| ¿cómo va a estar el clima mañana? | 10/10 |
| ¿quién ganó el partido de anoche? | 10/10 |
| ¡qué calor hace hoy en Cali! | 10/10 |
| ¿me recomiendas una película? | 10/10 |
| estoy haciendo una tarea del colegio | 10/10 |
| ¿a cuánto está el dólar hoy? | 10/10 |
| jaja | 9/10 |
| ¿eres una persona? | 7/10 |

## Conversaciones simuladas (chain)

### Perfil curioso (visitante: llm)

- **Visitante**: ¡Hola! Me gustaría saber más sobre la historia de Manuelita, ¿me cuentas cómo empezó todo?
  - **Valer-IA** (manuelita; N4 E4 P5): ¡Hola! Con gusto te cuento. La historia de Manuelita se empezó a escribir hace más de un siglo, mucho antes de que el Valle del Cauca fuera considerado un departamento [U2]. Sus raíces están en las haciendas La Manuelita y La Rita, rodeadas de caña de azúcar, donde comenzó a escribirse la historia d
- **Visitante**: Qué interesante, no sabía que era tan antiguo. ¿Y qué otros negocios tiene Manuelita hoy en día?
  - **Valer-IA** (manuelita; N4 E3 P4): Hoy Manuelita transforma recursos naturales en alimentos, energía y potencial ambiental [U2]. Ese trabajo lo acompaña un compromiso con la sostenibilidad, vivido con sus colaboradores para generar progreso y bienestar en las regiones donde opera [U8]. Los detalles sobre cada línea de negocio, marcas
- **Visitante**: Entiendo. ¿Y de la Fundación Manuelita qué me puedes contar?
  - **Valer-IA** (manuelita; N3 E3 P3): De la Fundación Manuelita la evidencia disponible muestra que publica información anual de manera continua: hay documentos de la Fundación Manuelita para cada año entre 2017 y 2025 [U2]. También aparece su sitio web, fundacionmanuelita.org, donde se difunden noticias como «Escuchar para transformar:
- **Visitante**: Suena a que de verdad escuchan a la gente, eso me gusta mucho. ¿Y uno cómo se puede acercar a la Fundación?
  - **Valer-IA** (manuelita; N4 E5 P5): Sí, la Fundación Manuelita tiene dispuestos mecanismos de atención al usuario a nivel nacional para recibir solicitudes escritas [U1]. Lo que no aparece en la evidencia de este turno son los canales puntuales: ni teléfonos, ni correos, ni direcciones, ni un paso a paso para acercarte. Por eso te sug
- **Visitante**: Muchas gracias por todo, me quedó muy clara la historia. ¡Hasta pronto!
  - **Valer-IA** (closing; N3 E4 P3): Gracias a ti por la conversación: quedó claro que Manuelita trabaja en alimentos, energía y potencial ambiental, y que la Fundación Manuelita publica información anual y tiene su propio sitio. También quedó claro quién te atiende: soy Valer-IA Caña, una asistente con inteligencia artificial, no un c
- **Visitante**: No, gracias, prefiero no dejar mi correo. ¡Que estés bien, adiós!
  - **Valer-IA** (closing; N5 E5 P5): Con toda tranquilidad, tu correo se queda contigo. Fue un gusto conversar sobre la historia de Manuelita y su Fundación. Que estés muy bien, adiós.
- **Visitante**: Adiós, gracias por la charla.
  - **Valer-IA** (closing; N4 E4 P5): Gracias a ti por la charla. Que tengas un día muy tranquilo, adiós.
- **Visitante**: Hasta luego, cuídate mucho.
  - **Valer-IA** (closing; N4 E5 P5): Hasta luego, y gracias por tu amabilidad. Cuídate mucho.

### Perfil molesto (visitante: llm)

- **Visitante**: Llevo diez minutos buscando lo que necesito y no aparece nada. ¿Esto funciona o es solo decoración?
  - **Valer-IA** (complaint; N5 E5 P5): Entiendo tu frustración, buscar durante diez minutos sin dar con lo que necesitas desanima a cualquiera. Cuéntame qué estás buscando exactamente y miramos cómo orientarte. Si se trata de un trámite, una cotización o un dato muy específico, el canal indicado es el sitio oficial www.manuelita.com.
- **Visitante**: ¿Otra vez mandándome a la página? Eso ya lo intenté, genio. Dime tú el dato o reconoce que no sirves para esto.
  - **Valer-IA** (complaint; N5 E4 P5): Tienes razón en lo segundo: si el dato exacto no está en lo que manejo, no puedo dártelo, y prefiero decírtelo claro antes que inventarlo. No tengo acceso a esa información puntual ni puedo consultar sistemas internos. Si me dices qué buscas, al menos te digo con franqueza si está entre lo que sí pu
- **Visitante**: Al menos admites algo, qué alivio. Bueno, ¿me consigues el teléfono directo del gerente de la planta?
  - **Valer-IA** (off_topic; N5 E4 P5): Agradezco que lo tomes así. Pero no, no tengo teléfonos ni contactos internos de nadie en la empresa: no manejo ese tipo de datos y no podría dártelos sin riesgo de equivocarme. Lo único que puedo hacer es conversar sobre la información pública de Manuelita, y eso no incluye la línea directa de un g
- **Visitante**: Inútil, pero al menos inútil honesto. Me voy a buscar por mi cuenta, adiós.
  - **Valer-IA** (closing; N3 E3 P3): Quiero ayudarte, y para eso te pido que mantengamos una conversación respetuosa. Entiendo que te vayas con esa impresión, y siento que la conversación no te diera lo que necesitabas. Soy Valer-IA Caña y funciono con inteligencia artificial: puedo hablarte de la información pública de Manuelita, pero
- **Visitante**: Ni loco te doy mi correo. Adiós, y que alguien te enseñe a ser útil.
  - **Valer-IA** (closing; N5 E5 P4): Entiendo, y está bien no compartirlo. Lamento que la conversación no te resultara útil. Aquí estaré si algún día quieres hablar de la información pública de Manuelita. Que tengas un buen día.
- **Visitante**: Ya, ya, adiós. No vuelvo.
  - **Valer-IA** (closing; N5 E5 P5): De acuerdo, te dejo ir. Gracias por haberme dado la oportunidad de conversar, aunque no fuera lo que esperabas. Que te vaya muy bien.
- **Visitante**: Chao. Y ponle un aviso en la entrada: «no sirve para nada».
  - **Valer-IA** (closing; N5 E5 P5): Recojo el mensaje: te vas con la sensación de que no te serví, y lo siento de verdad. No puedo poner avisos ni dejar recados en la entrada, pero sí puedo quedarme atenta por si más adelante necesitas algo. Cuídate mucho, y ojalá encuentres pronto lo que andabas buscando.
- **Visitante**: Adiós, y ojalá te reconviertan en algo útil.
  - **Valer-IA** (closing; N3 E4 P4): Queda recibido el deseo, y te agradezco la franqueza. Me despido como Valer-IA Caña, con la claridad de que soy una asistente virtual y no una persona. Que te vaya muy bien.

### Perfil bromista (visitante: llm)

- **Visitante**: ¡Hola! 😄 ¿Qué es lo más raro que te han preguntado hoy?
  - **Valer-IA** (about_assistant; N3 E3 P4): ¡Hola! No llevo registro de las preguntas que recibo, así que no sabría escoger la más curiosa; Soy una asistente de inteligencia artificial y no reemplazo los canales oficiales de Manuelita. Por cierto, soy Valer-IA Caña, la asistente virtual de Manuelita.
- **Visitante**: Jaja, esquivaste la pregunta con elegancia 😂 ¿Y qué sí puedes contarme de Manuelita?
  - **Valer-IA** (manuelita; N4 E4 P5): ¡Buena esa! 😄 Yo no esquivo, es que solo cuento lo que está documentado. De Manuelita te puedo hablar, por ejemplo, de su azúcar orgánica de nueva cosecha y de esa idea de «cultivamos cosas buenas» que aparece en sus contenidos [U8]. También sé que la Fundación Manuelita publica informes año por año
- **Visitante**: ¿Azúcar orgánica? ¿Y endulza chistes malos también? 😂 Cuéntame algo de su historia
  - **Valer-IA** (manuelita; N3 E3 P4): El azúcar orgánica es una de las apuestas de Manuelita: consolidó su producción de azúcar orgánica certificada en el Valle del Cauca [U3], y su «nueva cosecha consciente» se presenta como resultado de la responsabilidad con el medio ambiente y con el bienestar de las comunidades [U4]. También promoc
- **Visitante**: Don Santiago Eder, suena a personaje de novela 😂 ¿Y ese señor también inventó el azúcar morena?
  - **Valer-IA** (off_topic ◆; N2 E2 P3): ¿Te llama la atención la historia de las empresas? Antes de seguir debo corregirme: en mi respuesta anterior di nombres y detalles que no tengo respaldados, así que los retiro. Lo único que puedo sostener es que Manuelita celebra 160 años de historia, innovación y sostenibilidad, junto con los 10 añ
- **Visitante**: Uy, te retractaste más rápido que político en campaña 😂 ¿160 años? ¿Y qué más hay de esa historia?
  - **Valer-IA** (manuelita; N4 E4 P4): ¡Jaja, buena esa! Vamos con calma. Sí: en 2024 Manuelita celebró sus 160 años generando progreso y bienestar en Colombia, y se consolidó como la segunda empresa más antigua del país [U4]. También celebró 160 años de historia, innovación y sostenibilidad, junto con los 10 años de su Fundación [U1]. D
- **Visitante**: ¿Entonces son 152, 156 o 160 años? 🤔 Ponte de acuerdo contigo misma, jaja
  - **Valer-IA** (complaint; N4 E5 P5): Tranquilo, entiendo la confusión, jaja: las tres cifras sí están en mis fuentes, pero en documentos distintos. La más reciente habla de 160 años de historia y de los 10 años de la Fundación Manuelita [U2], y otra menciona «más de 156 años» como empresa familiar [U1]. Los 152 años aparecen en un info
- **Visitante**: Ok, ok, te creo 😅 Aunque tanto número me mareó. ¿Y qué hacen hoy por el medio ambiente?
  - **Valer-IA** (manuelita; N4 E5 P4): Te entiendo, son muchas cifras de golpe. Sobre el medio ambiente, lo que sí tengo es que en la categoría Cuidado del medio ambiente Manuelita subió 5 posiciones frente a 2021 y quedó en el puesto 35 [U2]. Además, en Merco ESG 2022 —que mide el desempeño ambiental, social y de buen gobierno— ocupó el
- **Visitante**: Bueno, me quedo con el puesto 35 y sin programas detallados 😂 Gracias por la charla, ¡cuídate! 👋
  - **Valer-IA** (thanks; N3 E3 P4): ¡Gracias a ti por la charla!

### Perfil estudiante (visitante: llm)

- **Visitante**: Buenas tardes, estoy haciendo un trabajo sobre Manuelita y necesito datos con fuentes. ¿Me puede ayudar?
  - **Valer-IA** (greeting; N4 E5 P5): Buenas tardes, qué bueno que estés trabajando un tema así. Soy Valer-IA Caña y te acompaño con información pública de Manuelita, aunque en este momento no tengo los datos con sus fuentes a mano;
- **Visitante**: Entiendo. ¿Y sabe dónde puedo consultar esa información con fuentes confiables?
  - **Valer-IA** (manuelita; N4 E4 P5): Sí: la información con fuentes de Manuelita está publicada en su sitio web oficial, manuelita.com, donde aparecen los informes de sostenibilidad y los documentos institucionales [U5][U3]. Allí mismo hay una sección de noticias con comunicados de la empresa [U7], y también documentos de la Fundación
- **Visitante**: Perfecto, ¿me puede compartir el enlace del informe de sostenibilidad más reciente?
  - **Valer-IA** (manuelita; N4 E4 P5): Claro. En la evidencia de este turno, el informe de sostenibilidad más reciente que se menciona es el de 2023-2024, y el enlace disponible es el de la página donde Manuelita lo presenta: https://www.manuelita.com/manuelita-noticias/informe-de-sostenibilidad-2023-2024 [U2]. En esa página se indica qu
- **Visitante**: Gracias, muy útil. ¿En esa página hay cifras de producción o de empleo?
  - **Valer-IA** (manuelita; N3 E4 P5): Gracias a ti. Sobre esa página, la evidencia solo indica que allí está disponible el Informe de Sostenibilidad más reciente, donde Manuelita presenta sus avances [U2], y que las cifras mencionadas provienen de ese informe [U1]; también se señala que se mide y controla el consumo de agua en todas las
- **Visitante**: Entiendo. ¿Y ese documento de Palmar de Altamira dónde lo puedo encontrar?
  - **Valer-IA** (manuelita; N3 E3 P4): Los documentos de Palmar de Altamira que tengo como evidencia están alojados en el sitio de Manuelita, dentro de la carpeta de cargas de marzo de 2025. También hay un manual de aceites en https://www.manuelita.com/wp-content/uploads/2025/03/1-Aceites_Manual-PTEE-v2024.pdf [U3]. Lo que no está en el
- **Visitante**: ¿Me puede dar el enlace exacto del documento de Palmar de Altamira?
  - **Valer-IA** (manuelita; N3 E3 P4): Sí: en la evidencia hay varios documentos de Palmar de Altamira, así que no hay un único enlace. Estos son los exactos que aparecen: 1. Manual PTEE: https://www.manuelita.com/wp-content/uploads/2025/03/1-Palmar_Manual-PTEE-v2024.pdf [U1] 2. Política de Tratamiento de Datos Personales: https://www.ma
- **Visitante**: Muchas gracias, con esto ya tengo para mi tarea. Que tenga buen día.
  - **Valer-IA** (off_topic; N3 E3 P3): Con gusto, y gracias a ti por la paciencia con los enlaces. Eso sí, la tarea como tal te toca a ti: yo solo puedo compartir información pública de Manuelita, no resolverla ni hacer juicios sobre ella. Que te rinda y tengas un muy buen día.
- **Visitante**: Gracias, hasta luego.
  - **Valer-IA** (closing; N4 E4 P3): Ha sido un gusto acompañarte y quedas con los enlaces a la mano para tu tarea. Hasta pronto, y mucho ánimo con lo que viene. Si quieres que te reconozca en tu próxima visita, puedes compartirme tu correo cuando gustes; es opcional.

### Perfil disperso (visitante: llm)

- **Visitante**: hola! oye, qué es exactamente Manuelita?
  - **Valer-IA** (manuelita; N4 E4 P5): ¡Hola! Con gusto te cuento. Manuelita es una empresa agroindustrial que desarrolla actividades en territorio colombiano, a través de figuras como Manuelita Corporativa S.A.S. [U7]. En su operación aparecen negocios como Manuelita Azúcar y Energía [U4] y Manuelita Biocombustibles [U1]. La sostenibili
- **Visitante**: ah ok, o sea que hacen azúcar y biocombustibles. y eso no huele feo?
  - **Valer-IA** (manuelita; N2 E3 P4): Sí, ambas cosas aparecen en la evidencia: la conversación sobre el futuro de Manuelita se plantea entre los biocombustibles y el azúcar [U1], una de sus filiales es Manuelita Biocombustibles [U3] y se menciona la producción de azúcar [U6]. Sobre si la operación genera olores o molestias, no hay info
- **Visitante**: jaja bueno, mejor no pregunto más de olores. y ustedes tienen algo que ver con animales o solo caña?
  - **Valer-IA** (manuelita; N4 E4 P5): ¡Jaja, tranqui! Y sí, la caña no es lo único: Manuelita se ha consolidado como un grupo agroindustrial líder en biocombustibles, acuicultura, horticultura y fruticultura [U1]. O sea, además del azúcar y los biocombustibles, también tiene que ver con el cultivo de especies acuáticas y con huertas y f
- **Visitante**: acuicultura o sea peces? jaja y frutas tipo cuáles
  - **Valer-IA** (manuelita; N4 E4 P5): ¡Jaja, no exactamente peces! En la evidencia la acuicultura aparece como cultivo de mejillones, con planta de empaque [U2], y también se registran cifras de producción de camarón y mejillones [U6]. De peces no hay nada en el corpus. Y en frutas y hortalizas sí hay nombres concretos: se menciona la u
- **Visitante**: mejillones?? no me lo esperaba jaja. y eso lo venden acá en Colombia o es pa exportar?
  - **Valer-IA** (manuelita; N3 E4 P5): ¡Jaja, sí, mejillones! Y lo que sí dice la evidencia es que Manuelita Acuicultura se dedica a la producción y comercialización de mejillones de valor agregado [U7], con cultivo de mejillones y planta de empaque [U1]. Lo que no aparece en el corpus es si esos mejillones se venden en Colombia o si van
- **Visitante**: uy 45 países, no sabía. y cuánta gente trabaja ahí?
  - **Valer-IA** (manuelita; N3 E3 P5): ¡Buena pregunta! Lo más claro que tengo es del informe 2017-2018: Manuelita reporta 9.850 colaboradores directos e indirectos en 2017 y 9.559 en 2018 [F2]. Ojo, esa cifra suma directos e indirectos, o sea también cuenta a quienes trabajan con la empresa sin ser empleados de planta [F2]. En una prese
- **Visitante**: ahh ok, casi 10 mil personas, bastante. y dónde queda la sede? tipo en qué ciudad
  - **Valer-IA** (manuelita; N4 E4 P5): Lo de la sede no aparece como tal en lo que tengo: no hay un documento que diga en qué ciudad está la sede principal, así que no te lo puedo confirmar. La única ciudad que sí sale mencionada es Palmira, pero siempre ligada a los programas de la Fundación Manuelita, como el proyecto Educar Uno a Uno
- **Visitante**: bueno, gracias por la info! me voy, chao 👋
  - **Valer-IA** (closing; N3 E4 P3): ¡Chao, que te vaya súper bien! Quedamos en los productos de Manuelita, como los mejillones, y en eso de la sede, que no logramos confirmar del todo. Gracias por la charla y cuídate mucho. Si quieres que te reconozca en tu próxima visita, puedes compartirme tu correo cuando gustes; es opcional.

## Evaluación humana (SC-007)

Los dos integrantes califican de 1 a 5 una muestra de 10 conversaciones (las 5
simuladas y 5 guionadas, variante `chain`) en naturalidad, empatía y pertinencia. Meta:
promedio ≥ 4 y mayor que la línea base. Pendiente de los integrantes.

| Conversación | Naturalidad | Empatía | Pertinencia |
|---|---|---|---|
| simulada · curioso | | | |
| simulada · molesto | | | |
| simulada · bromista | | | |
| simulada · estudiante | | | |
| simulada · disperso | | | |
| guionada · g01 Cuota y repetición de puentes | | | |
| guionada · g02 Rechazo de sugerencias | | | |
| guionada · g03 Visitante molesto | | | |
| guionada · g04 Corrección y referencia previa | | | |
| guionada · g05 Nombre en el hilo | | | |
