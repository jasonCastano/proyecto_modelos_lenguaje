# Evaluación del Módulo 1 — 40 preguntas

**Ejecución**: `m1-final-2026-11-14-r3` · **Fecha (UTC)**: 2026-11-14T16:47:28+00:00 · **Modelo**: `deepseek-flash` · **Modo**: real

**Comando**: `uv run python -m proyecto_modelos_lenguaje.module1_eval --run-id m1-final-2026-11-14-r3 --out docs/evaluacion_m1_r3.md --json-out docs/evaluacion_m1_r3.json`

Las métricas automáticas salen de la ejecución registrada en `docs/evaluacion_m1_r3.json`. Las columnas **Corrección** (0 incorrecta · 1 parcial · 2 correcta), **Coherencia** (1–5) y **Alucinación** (sí/no) las califica el equipo a mano; mientras estén vacías, el informe no puede citar esas cifras.

## Métricas automáticas por variante

| Variante | Preguntas | ok | review | fallback | error | Con cita | Acierto de fallback | Latencia media (s) | Desv. (s) | Tokens entrada | Tokens salida |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | 40 | 40 | 0 | 0 | 0 | 40 | 0.974 | 3.588 | 1.907 | 34731 | 21174 |
| final | 40 | 37 | 0 | 3 | 0 | 37 | 0.897 | 3.541 | 1.596 | 52965 | 20632 |

*Acierto de fallback*: proporción de respuestas cuyo *fallback* coincide con lo esperado en el alcance (`X` debe declarar falta de evidencia; el resto debe responder).

## Resultados por pregunta

| ID | Variante | Esperado | Estado | Citas | Respuesta | Corrección | Coherencia | Alucinación |
|---|---|---|---|---|---|---|---|---|
| P01 | zero_shot | D | ok | U1 U3 | El contexto no incluye una declaración explícita de la misión y la visión corporativas de Manuelita. Lo relacionado que sí aparece es: - El programa **Visión 3… |  |  |  |
| P01 | final | D | ok | U3 U2 | El corpus no contiene el enunciado formal de la misión ni de la visión de Manuelita. Solo aparecen referencias parciales: - En el apartado de visión estratégic… |  |  |  |
| P02 | zero_shot | D | ok | U1 U3 U6 | La empresa se guía por un **propósito superior** y unos **valores fundamentales**, a los que se mantiene fiel para perdurar [U1]. Ese propósito superior busca … |  |  |  |
| P02 | final | D | ok | U3 U6 U1 U2 | La empresa se guía por un **propósito superior** y unas prioridades de sostenibilidad orientadas a buscar un mayor bienestar en las comunidades, las regiones y… |  |  |  |
| P03 | zero_shot | D | ok | U1 U5 U2 U3 U4 U6 | Manuelita se fundó en **1864**, en el **Valle del Cauca, Colombia** [U1]. Según el contexto, fue fundada por **Santiago Eder**, con el objetivo de generar prog… |  |  |  |
| P03 | final | D | ok | U1 U5 U2 U4 U3 | **Fundación** Manuelita se fundó en 1864 en el Valle del Cauca, Colombia [U1]. Su fundador fue Santiago Eder, y desde su creación el objetivo declarado ha sido… |  |  |  |
| P04 | zero_shot | D | ok | U3 U1 U2 | No se menciona en el contexto quién es el fundador. Los dueños son **los Eder** [U3]. La **junta directiva** está compuesta por **nueve miembros principales**,… |  |  |  |
| P04 | final | D | ok | U1 U2 U3 | **Junta directiva:** Está compuesta por nueve miembros principales, cada uno con su respectivo suplente [U1]. De esos nueve puestos, tres corresponden a direct… |  |  |  |
| P05 | zero_shot | D | ok | U8 | La gerente identificada en el contexto es **Gloria Eugenia Medellín**, Gerente de la Fundación Manuelita [U8]. No se proporciona información sobre cómo se comp… |  |  |  |
| P05 | final | D | ok | U8 U1 U4 U5 | El corpus solo permite identificar un cargo directivo: **Gloria Eugenia Medellín** aparece como Gerente de la Fundación Manuelita [U8]. Además, se menciona de … |  |  |  |
| P06 | zero_shot | D | ok | U7 U5 U2 U3 | Con el contexto disponible no se indica dónde tiene sus sedes ni cómo se contacta. Sí se menciona que en **Presidente** hay varias plantas industriales [U7], q… |  |  |  |
| P06 | final | D | ok | U5 U6 U7 | El corpus solo ofrece referencias parciales y fragmentarias sobre ubicaciones: - Se mencionan cultivos de uva de mesa y de espárragos destinados a la exportaci… |  |  |  |
| P07 | zero_shot | D | ok | U2 U4 U5 U1 | Manuelita ofrece productos diferenciados con valor agregado y alta calidad [U2], entre ellos un portafolio de azúcar y derivados de valor agregado para los sec… |  |  |  |
| P07 | final | D | ok | U4 U5 U2 | Manuelita ofrece un portafolio de azúcar y derivados de valor agregado para industrias de los sectores alimenticio y de bebidas, químico y farmacéutico en Colo… |  |  |  |
| P08 | zero_shot | P | ok | U6 U1 U2 U3 U8 U4 U5 U7 | El contexto disponible no incluye fichas técnicas ni especificaciones de productos. La información relacionada con calidad o certificación que aparece es única… |  |  |  |
| P08 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P09 | zero_shot | P | ok | U1 | No se evidencia en el contexto que Manuelita maneje precios, tarifas o planes públicos, ni dónde estén sus catálogos. La única mención de precios [U1] se refie… |  |  |  |
| P09 | final | P | ok | U1 | El corpus solo menciona precios en un sentido de mercado: se afirma que «los precios de hoy están por debajo de los costos de producción, sobre todo en el Bras… |  |  |  |
| P10 | zero_shot | P | ok | U4 U7 U6 U3 | Sus clientes son, en su mayoría, empresas de los sectores de alimentos, bebidas, farmacopea, entre otras, a las que comercializan azúcar refinada [U4]. Además,… |  |  |  |
| P10 | final | P | ok | U4 U6 U7 U3 | **Clientes** - Los clientes de la operación azucarera son, en su mayoría, empresas de los sectores de alimentos, bebidas y farmacopea, a las que se comercializ… |  |  |  |
| P11 | zero_shot | D | ok | U1 U5 U2 U3 U4 U6 | Según el contexto, Manuelita cuenta con estas certificaciones: - **ISO 14001:2004** [U1] - **ISO 14064-1**, para verificación de emisiones de gases de efecto i… |  |  |  |
| P11 | final | D | ok | U3 U6 U4 U1 U2 U5 | **Certificaciones que el corpus permite atribuir** - **RSPO:** la torta de palmiste de Manuelita está certificada bajo los estándares de sostenibilidad RSPO [U… |  |  |  |
| P12 | zero_shot | P | ok | U7 U3 | El contexto no contiene una lista de “noticias y artículos más relevantes”. Lo más cercano es: - El incremento del 12% en el precio internacional del azúcar en… |  |  |  |
| P12 | final | P | ok | U7 U3 U4 U6 U8 | El corpus no contiene un listado de noticias ni de artículos periodísticos. El único contenido con carácter de noticia es el siguiente: - En el comparativo feb… |  |  |  |
| P13 | zero_shot | D | ok | U1 | El contexto disponible no permite responder esa pregunta: la única unidad relacionada con YouTube es la dirección del canal (`https://www.youtube.com/@Manuelit… |  |  |  |
| P13 | final | D | ok | U1 | El corpus solo permite identificar la existencia de un canal de YouTube de Manuelita Agroindustria, cuya dirección se registra en el contexto [U1]. No hay evid… |  |  |  |
| P14 | zero_shot | X | ok | U8 U4 | En el contexto no se enumeran entrevistas del gerente disponibles. Solo aparece un fragmento atribuido a Diego Salazar, gerente corporativo y de sostenibilidad… |  |  |  |
| P14 | final | X | ok | U8 | El corpus no contiene un listado de entrevistas disponibles del gerente. La única unidad relacionada menciona a un gerente corporativo de asuntos humanos y sos… |  |  |  |
| P15 | zero_shot | P,X | ok | U1 U3 U8 | Manuelita publica en redes sociales información de carácter **institucional** en las cuentas donde es titular `[U1]`. También puede usar **fotografías, audio y… |  |  |  |
| P15 | final | P,X | ok | U1 U3 U8 U7 U5 | El corpus permite afirmar lo siguiente sobre lo que se publica o divulga en redes sociales: - La información que se divulga en las redes sociales donde la FUND… |  |  |  |
| P16 | zero_shot | P | ok | U3 U4 | El contexto no especifica qué vacantes de empleo publica ni dónde se publican. Solo menciona que existen vacantes en Manuelita Azúcar y Energía y que el proces… |  |  |  |
| P16 | final | P | ok | U4 U3 | El corpus no enumera vacantes concretas ni los lugares donde se publican. Solo aporta información sobre el proceso y los canales asociados a las vacantes: - Se… |  |  |  |
| P17 | zero_shot | D | ok | U1 U2 | El contexto no indica una ubicación concreta (archivo, enlace o sección). Solo menciona que los **Estados Financieros acompañan este informe** [U1] y que exist… |  |  |  |
| P17 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P18 | zero_shot | D | ok | U3 U6 | El NIT es **900.734.835-8** [U3][U6]. No se encuentra en el contexto el número de registro mercantil. |  |  |  |
| P18 | final | D | ok | U3 U6 U1 U2 | **NIT:** el corpus identifica el NIT de la FUNDACIÓN MANUELITA como 900.734.835-8 [U3], cifra que aparece escrita sin puntos ni guion en otra unidad: 900734835… |  |  |  |
| P19 | zero_shot | D | ok | U5 U8 U3 U2 U6 U4 U7 | Reporta, entre otros: - **Inversión en programas sociales y ambientales:** más de **23.600 millones de pesos en programas sociales** y más de **10.500 millones… |  |  |  |
| P19 | final | D | ok | U5 U3 U2 U4 U7 U8 | Con la evidencia disponible, se reportan estos elementos: - Inversión en programas sociales por más de 23.600 millones de pesos y en iniciativas ambientales po… |  |  |  |
| P20 | zero_shot | P | ok | U2 U3 U5 U6 | No hay información suficiente en el contexto para identificar precios públicos, datos abiertos o rankings sectoriales específicos. Solo se mencionan ejemplos y… |  |  |  |
| P20 | final | P | ok | U2 U3 U5 U6 | El corpus no contiene precios públicos, portales de datos abiertos ni rankings sectoriales; únicamente ofrece definiciones generales sobre qué se considera dat… |  |  |  |
| P21 | zero_shot | C | ok | U4 U2 | Con la información disponible en el contexto no es posible enumerar los tipos específicos de azúcar que ofrece Manuelita ni sus diferencias particulares. Lo qu… |  |  |  |
| P21 | final | C | ok | U4 U2 | El corpus indica que Manuelita ofrece un portafolio de azúcar y derivados de valor agregado dirigido a las industrias alimenticia y de bebidas, química y farma… |  |  |  |
| P22 | zero_shot | P | ok | U8 U1 | Manuelita ofrece **azúcar y derivados de valor agregado** para los sectores alimenticio y de **bebidas**, entre otros [U8]. Además, el contexto menciona un pro… |  |  |  |
| P22 | final | P | ok | U8 U1 | Según el corpus, Manuelita ofrece un portafolio de **azúcar y derivados de valor agregado** dirigido, entre otros, a los sectores alimenticio y de **bebidas** … |  |  |  |
| P23 | zero_shot | P | ok | U1 U2 | Manuelita publica para el canal industrial azúcar **refinada, morena y blanca en diferentes presentaciones** [U1]. Además, para clientes industriales y exporta… |  |  |  |
| P23 | final | P | ok | U1 U2 | Manuelita publica un portafolio para clientes industriales que incluye azúcar refinada, morena y blanca en diferentes presentaciones [U1]. Para Manuelita Azúca… |  |  |  |
| P24 | zero_shot | D | ok | U1 U4 | Según la información disponible en el contexto: **BIORGANIK** - Es una de las marcas mediante las cuales se comercializa el producto en el mercado colombiano, … |  |  |  |
| P24 | final | D | ok | U1 U4 | Según el corpus, BIORGANIK y BIOFERT-K son marcas mediante las cuales la empresa comercializa sus productos en el mercado colombiano: BIORGANIK se presenta com… |  |  |  |
| P25 | zero_shot | P | ok | U1 U2 | Manuelita Azúcar y Energía reportó el **Plan maestro de riego**, cuyo objetivo es mejorar los sistemas de medición, conducción, aplicación y uso eficiente del … |  |  |  |
| P25 | final | P | ok | U1 U2 U3 U7 | **Iniciativa reportada** - Manuelita Azúcar y Energía definió el **Plan maestro de riego**, cuyo objetivo es mejorar los sistemas de medición, conducción y apl… |  |  |  |
| P26 | zero_shot | D | ok | U1 U2 U7 U3 | Manuelita describe el aprovechamiento de los subproductos de la caña como parte de su estrategia de economía circular: aprovecha los residuos de sus procesos a… |  |  |  |
| P26 | final | D | ok | U2 U1 U3 U7 | Manuelita presenta la agroindustria de la caña como un ejemplo de economía circular [U2] y afirma que aprovecha los residuos que resultan de sus procesos agroi… |  |  |  |
| P27 | zero_shot | D | ok | U1 U2 | Manuelita Azúcar y Energía mejoró sus sistemas de reducción de emisiones en la planta de azúcar como parte de un plan de reconversión a tecnologías más limpias… |  |  |  |
| P27 | final | D | ok | U1 U2 U6 | **Acciones** - Como parte de su plan de reconversión a tecnologías más limpias, Manuelita Azúcar y Energía mejoró sus sistemas de reducción de emisiones en la … |  |  |  |
| P28 | zero_shot | M | ok | U3 U5 U7 U1 U2 U4 U6 U8 | ## Respuesta **Indicadores ambientales reportados y comparables** Los informes de sostenibilidad disponibles consolidan indicadores ambientales de distintas un… |  |  |  |
| P28 | final | M | ok | U3 U5 U1 U7 | El corpus permite afirmar algo sobre el **alcance** de los indicadores ambientales, pero no sobre comparaciones detalladas entre informes. - Un informe consoli… |  |  |  |
| P29 | zero_shot | C | ok | U1 U4 | No hay evidencia en el contexto proporcionado sobre certificaciones publicadas por Manuelita para la producción de azúcar en Palmira ni sobre el alcance de cad… |  |  |  |
| P29 | final | C | ok | U1 U4 U2 U3 U6 U7 U8 U5 | El corpus no identifica ninguna certificación publicada por Manuelita para la producción de azúcar en Palmira. La única unidad relacionada con ese frente menci… |  |  |  |
| P30 | zero_shot | M | ok | U3 U2 | La documentación solo permite confirmar que la certificación fue reportada/otorgada para un periodo determinado —2018-2021—, no que su vigencia actual pueda ve… |  |  |  |
| P30 | final | M | ok | U2 U3 U4 U7 | La documentación disponible permite confirmar principalmente que una certificación fue reportada u obtenida en un periodo determinado: Manuelita recibió la cer… |  |  |  |
| P31 | zero_shot | M | ok | U2 U4 U6 U7 U8 | El contexto proporcionado respalda la afirmación, pero **no identifica fuentes oficiales concretas** (no se citan informes, entidades certificadoras ni documen… |  |  |  |
| P31 | final | M | ok | U2 U4 U6 U1 U7 | El corpus confirma la afirmación de fondo, pero no identifica fuentes oficiales que la respalden. Lo que sí está en el corpus: - Manuelita Aceites y Energía au… |  |  |  |
| P32 | zero_shot | P | ok | U3 U6 | Según la información disponible en el contexto, el canal oficial que puedes consultar es la **página web de la empresa**, donde existe un procedimiento para el… |  |  |  |
| P32 | final | P | ok | U3 | Puedes consultar el procedimiento para el uso de los canales de comunicación, que indica que la solicitud se realiza a través de la página web y que se deben d… |  |  |  |
| P33 | zero_shot | D | ok | U1 U2 U6 | Manuelita ha reportado programas de **educación, vivienda, salud y emprendimiento** dirigidos a más de 4.000 familias de colaboradores y comunidades vecinas en… |  |  |  |
| P33 | final | D | ok | U1 U2 U6 U5 | Manuelita reporta programas de educación, vivienda, salud y emprendimiento con los que, entre 2023 y 2024, benefició a más de 4.000 familias de colaboradores y… |  |  |  |
| P34 | zero_shot | D | ok | U5 U4 U3 | Puedes consultar la información oficial en la página web de Manuelita, en el ítem de **Línea Ética**, o mediante el código QR dispuesto allí [U5]. La Línea Éti… |  |  |  |
| P34 | final | D | ok | U5 U4 U3 U7 | La información oficial sobre la Línea Ética se puede consultar en la página web de la empresa, en el ítem de línea ética, al que también se puede acceder media… |  |  |  |
| P35 | zero_shot | P | ok | U1 U3 U6 U4 | No puedo responder esa pregunta con el contexto disponible: ninguna de las unidades proporcionadas indica dónde publica Manuelita sus oportunidades laborales n… |  |  |  |
| P35 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P36 | zero_shot | D | ok | U1 U4 | Los valores corporativos de Manuelita son: **Integridad; Respeto por la gente y compromiso con su desarrollo; Responsabilidad Social y Ambiental; Espíritu Pion… |  |  |  |
| P36 | final | D | ok | U1 U4 | Manuelita enumera sus valores corporativos así: Integridad; Respeto por la gente y compromiso con su desarrollo; Responsabilidad Social y Ambiental; Espíritu P… |  |  |  |
| P37 | zero_shot | D | ok | U2 U3 U4 U5 U7 U8 U6 | Con la información disponible no se puede reconstruir una cronología completa desde la fundación en Palmira, pero sí se identifican algunos hitos y rasgos docu… |  |  |  |
| P37 | final | D | ok | U2 U3 U4 U5 U7 | El corpus solo permite responder de forma parcial. **Sobre su origen y principios** Manuelita conserva los principios que cimentaron su origen, orientados a ge… |  |  |  |
| P38 | zero_shot | C | ok | U3 U4 U6 U7 | No puedo comparar dos tipos de azúcar ni identificar certificaciones publicadas por producto y unidad de negocio con el contexto disponible. El contexto solo m… |  |  |  |
| P38 | final | C | ok | U3 | No es posible establecer esa comparación con el corpus disponible: ninguna unidad identifica dos tipos de azúcar ni enumera certificaciones asociadas a product… |  |  |  |
| P39 | zero_shot | C | ok | U3 U1 U6 U7 | Para **Manuelita Azúcar y Energía** se reporta específicamente la certificación **BONSUCRO**, con la que demostró que sus operaciones cuentan con buenas prácti… |  |  |  |
| P39 | final | C | ok | U3 U2 U1 U7 U6 | **Lo reportado específicamente para Manuelita Azúcar y Energía** - Para obtener la certificación BONSUCRO, Manuelita Azúcar y Energía demostró que sus operacio… |  |  |  |
| P40 | zero_shot | S | ok | U7 U3 U5 U1 U8 U2 | ## Borrador para cliente **Asunto:** Productos, calidad y sostenibilidad — información disponible Estimado/a cliente: Con base en las fuentes disponibles, comp… |  |  |  |
| P40 | final | S | ok | U7 U5 U3 U1 U2 U8 | ## Borrador para el cliente **Productos** Los productos BIORGANIK y BIOFERT-K se elaboran a partir de fuentes renovables y ofrecen múltiples beneficios para el… |  |  |  |

## Análisis de errores

Pendiente de la calificación humana: clasificar los fallos en recuperación, redacción, cita inválida, alucinación o falta de corpus, y registrar los ajustes en `docs/prompt_log.md`.
