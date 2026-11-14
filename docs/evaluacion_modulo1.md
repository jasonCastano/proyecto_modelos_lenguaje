# Evaluación del Módulo 1 — 40 preguntas

**Ejecución**: `m1-final-2026-11-14-r1` · **Fecha (UTC)**: 2026-11-14T16:27:13+00:00 · **Modelo**: `deepseek-flash` · **Modo**: real

**Comando**: `uv run python -m proyecto_modelos_lenguaje.module1_eval --run-id m1-final-2026-11-14-r1 --out docs/evaluacion_modulo1.md --json-out docs/evaluacion_modulo1.json`

Las métricas automáticas salen de la ejecución registrada en `docs/evaluacion_modulo1.json`. Las columnas **Corrección** (0 incorrecta · 1 parcial · 2 correcta), **Coherencia** (1–5) y **Alucinación** (sí/no) las califica el equipo a mano; mientras estén vacías, el informe no puede citar esas cifras.

## Métricas automáticas por variante

| Variante | Preguntas | ok | review | fallback | error | Con cita | Acierto de fallback | Latencia media (s) | Desv. (s) | Tokens entrada | Tokens salida |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | 40 | 40 | 0 | 0 | 0 | 40 | 0.974 | 3.752 | 2.05 | 34685 | 22371 |
| final | 40 | 35 | 0 | 5 | 0 | 35 | 0.897 | 3.599 | 2.126 | 52965 | 22088 |

*Acierto de fallback*: proporción de respuestas cuyo *fallback* coincide con lo esperado en el alcance (`X` debe declarar falta de evidencia; el resto debe responder).

## Resultados por pregunta

| ID | Variante | Esperado | Estado | Citas | Respuesta | Corrección | Coherencia | Alucinación |
|---|---|---|---|---|---|---|---|---|
| P01 | zero_shot | D | ok | U1 U3 | La información disponible no contiene una declaración formal de la misión y la visión corporativas de Manuelita. Solo se menciona la “Visión 3030”, cuyo objeti… |  |  |  |
| P01 | final | D | ok | U3 | El corpus no contiene los enunciados formales de misión y visión de Manuelita. Lo único relacionado es un fragmento sobre su visión estratégica, que se limita … |  |  |  |
| P02 | zero_shot | D | ok | U1 U3 U6 U7 | La empresa se guía por un **propósito superior** y unos **valores fundamentales** que le han permitido perdurar a lo largo de generaciones; ese propósito se vi… |  |  |  |
| P02 | final | D | ok | U3 U6 U1 U2 | La empresa se guía por un **propósito superior** y por **prioridades de sostenibilidad** orientadas a generar mayor bienestar en las comunidades, las regiones … |  |  |  |
| P03 | zero_shot | D | ok | U1 U5 U2 U3 U4 | Manuelita se fundó en **1864** en el **Valle del Calca, Colombia** [U1]. Fue fundada por **Santiago Eder**, y su objetivo ha sido generar progreso y bienestar … |  |  |  |
| P03 | final | D | ok | U1 U5 U2 U4 U3 | **Fundación** Manuelita se fundó en 1864, en el Valle del Cauca, Colombia [U1]. Su fundador fue Santiago Eder, según indica la unidad que señala que «desde que… |  |  |  |
| P04 | zero_shot | D | ok | U3 U1 U2 | No se identifica en el contexto a el fundador. Los dueños son los Eder [U3]. La Junta Directiva está compuesta por nueve miembros principales, cada uno con sup… |  |  |  |
| P04 | final | D | ok | U3 U2 U1 | **Fundador:** el corpus no identifica al fundador de Manuelita; ninguna unidad lo menciona. **Dueños:** la propiedad se atribuye a la familia Eder, señalada co… |  |  |  |
| P05 | zero_shot | D | ok | U8 | Según el contexto, **Gloria Eugenia Medellín** aparece como **Gerente de la Fundación Manuelita** [U8]. No se especifica en las unidades proporcionadas cómo se… |  |  |  |
| P05 | final | D | ok | U8 | El corpus identifica a **Gloria Eugenia Medellín** como Gerente de la Fundación Manuelita [U8]. El corpus no detalla cómo se compone el equipo directivo. |  |  |  |
| P06 | zero_shot | D | ok | U7 | El contexto no especifica las sedes, plantas ni cultivos de la empresa, ni tampoco proporciona canales de contacto. La única referencia geográfica es “Presiden… |  |  |  |
| P06 | final | D | ok | U5 U6 U1 U2 U3 U7 U8 | El corpus no permite responder dónde están ubicadas las sedes ni cómo se contacta la empresa: no hay ninguna unidad que indique direcciones, ciudades de la cas… |  |  |  |
| P07 | zero_shot | D | ok | U2 U4 U5 U1 | Manuelita ofrece productos diferenciados con valor agregado y alta calidad [U2], entre ellos un portafolio de azúcar y derivados para los sectores alimenticio,… |  |  |  |
| P07 | final | D | ok | U4 U5 U2 | Con base en el corpus, Manuelita ofrece: - **Azúcar y derivados de valor agregado** para las industrias alimenticia y de bebidas, química y farmacéutica, en Co… |  |  |  |
| P08 | zero_shot | P | ok | U1 U6 U5 | No encuentro en el contexto información sobre fichas técnicas o especificaciones de productos. Los documentos disponibles no describen catálogo de productos ni… |  |  |  |
| P08 | final | P | ok | U6 U1 U2 U4 U5 U7 U3 U8 | El corpus no contiene fichas técnicas ni especificaciones de productos. El único elemento relacionado con estándares de calidad es la certificación HACCP, otor… |  |  |  |
| P09 | zero_shot | P | ok | U1 U2 U3 U5 U4 U6 U7 U8 | No, según el contexto disponible no hay evidencia de que Manuelita maneje precios, tarifas o planes públicos sujetos a publicación, ni se menciona la existenci… |  |  |  |
| P09 | final | P | ok | U1 | El corpus solo menciona los precios en un sentido de mercado: se afirma que los precios de hoy están por debajo de los costos de producción, sobre todo en Bras… |  |  |  |
| P10 | zero_shot | P | ok | U4 U6 U7 U1 U3 | Sus clientes son, en su mayoría, empresas de los sectores de alimentos, bebidas y farmacopea, entre otras, a las que comercializan azúcar refinada [U4]. Tambié… |  |  |  |
| P10 | final | P | ok | U4 U7 U6 U1 U3 | **Clientes:** el corpus no identifica clientes por nombre, pero indica que en su mayoría son empresas de los sectores de alimentos, bebidas y farmacopea, a las… |  |  |  |
| P11 | zero_shot | D | ok | U1 U5 U2 U3 U4 U6 | Según el contexto, Manuelita tiene o se le asocian estas certificaciones: - **ISO 14001:2004** [U1] y **ISO 14064-1** para verificación de emisiones de GEI [U5… |  |  |  |
| P11 | final | D | ok | U1 U5 U2 U3 U6 U4 | Según el corpus, se registran estas certificaciones: - **ISO:** se menciona **ISO 14001:2004** en una tabla de certificaciones [U1], y también **ISO 14064-1** … |  |  |  |
| P12 | zero_shot | P | ok | U7 U2 U3 U6 U8 U1 U4 U5 | Con la información disponible en el contexto no aparece un listado titulado «noticias y artículos más relevantes»; sin embargo, los fragmentos que contienen he… |  |  |  |
| P12 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P13 | zero_shot | D | ok | U1 | El contexto disponible solo incluye la dirección del canal de YouTube (`https://www.youtube.com/@ManuelitaAgroindustria`) [U1], pero no contiene ningún detalle… |  |  |  |
| P13 | final | D | ok | U1 | El corpus únicamente incluye la referencia al canal de YouTube de Manuelita Agroindustria [U1]. No hay evidencia suficiente en el corpus para responder qué vid… |  |  |  |
| P14 | zero_shot | X | ok | U8 U2 U5 | No hay en el contexto una lista de entrevistas disponibles del gerente. Lo único relacionado es un fragmento de una intervención de Diego Salazar, gerente corp… |  |  |  |
| P14 | final | X | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P15 | zero_shot | P,X | ok | U1 U3 U8 | Manuelita publica en redes sociales información de carácter institucional [U1], así como fotografías, audio y video de eventos realizados por la compañía [U3].… |  |  |  |
| P15 | final | P,X | ok | U1 U3 U8 | Con la evidencia disponible se pueden señalar estos contenidos: - La información divulgada en las redes sociales donde la FUNDACIÓN MANUELITA es titular de una… |  |  |  |
| P16 | zero_shot | P | ok | U1 U3 U4 | El contexto proporcionado no contiene información sobre vacantes de empleo concretas ni sobre los canales o lugares donde se publican. Las unidades disponibles… |  |  |  |
| P16 | final | P | ok | U1 U3 U4 | El corpus no enumera vacantes concretas ni indica en qué portales, ciudades o plantas se publican. Solo aparecen referencias generales: - Existe un campo denom… |  |  |  |
| P17 | zero_shot | D | ok | U1 U2 U8 | El contexto proporcionado no contiene información sobre la ubicación de los informes financieros ni de la memoria anual. La única referencia cercana es la menc… |  |  |  |
| P17 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P18 | zero_shot | D | ok | U3 U6 U1 U2 U7 | **NIT:** 900.734.835-8, correspondiente a la FUNDACIÓN MANUELITA [U3] [U6]. (La unidad [U1] solo contiene un encabezado fragmentario: «No. Identificación Tribu… |  |  |  |
| P18 | final | D | ok | U3 U6 U1 | El corpus solo permite identificar el NIT de la **Fundación Manuelita**, que aparece como 900.734.835-8 [U3] y también registrado como 900734835-8 [U6]. Ambas … |  |  |  |
| P19 | zero_shot | D | ok | U5 U3 U4 U7 U8 U2 | Reporta inversión en programas sociales por más de 23.600 millones de pesos y en iniciativas ambientales por más de 10.500 millones [U5]. También reporta, en u… |  |  |  |
| P19 | final | D | ok | U5 U3 U4 U7 U8 U2 U6 | Con el corpus disponible se pueden señalar estos elementos: **Programas sociales e iniciativas ambientales (inversión)** - Manuelita invierte más de 23.600 mil… |  |  |  |
| P20 | zero_shot | P | ok | U2 U3 U6 U5 | No encuentro en el contexto información sobre precios públicos ni rankings sectoriales. Lo único relacionado con «datos abiertos» es la definición de **datos p… |  |  |  |
| P20 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P21 | zero_shot | C | ok | U4 U2 | No encuentro en el contexto proporcionado información que detalle los tipos de azúcar que ofrece Manuelita ni sus diferencias. Las unidades disponibles solo pe… |  |  |  |
| P21 | final | C | ok | U4 U2 | El contexto disponible no enumera los tipos de azúcar que ofrece Manuelita. Solo indica que la empresa ofrece un portafolio de azúcar y derivados de valor agre… |  |  |  |
| P22 | zero_shot | P | ok | U8 U1 | Para el sector de bebidas, la documentación disponible menciona: - El **portafolio de azúcar y derivados de valor agregado** de Manuelita, dirigido, entre otro… |  |  |  |
| P22 | final | P | ok | U8 U1 | Con la evidencia del corpus, los productos de Manuelita con aplicaciones documentadas para el sector de bebidas son: - **Azúcar y derivados de valor agregado**… |  |  |  |
| P23 | zero_shot | P | ok | U1 U2 | Manuelita publica para sus productos de azúcar industrial: - **Azúcar refinada, morena y blanca en diferentes presentaciones** [U1]. - **Azúcar en presentacion… |  |  |  |
| P23 | final | P | ok | U1 U2 | Manuelita ha desarrollado un portafolio dirigido a clientes industriales que usan sus productos como materia prima, e incluye azúcar refinada, morena y blanca … |  |  |  |
| P24 | zero_shot | D | ok | U1 U4 | BIORGANIK es un mejorador/acondicionador orgánico del suelo y un recuperador orgánico de su estructura, orientado al mejoramiento del suelo [U1][U4]. BIOFERT-K… |  |  |  |
| P24 | final | D | ok | U1 U4 | La empresa comercializa en el mercado colombiano dos marcas: **BIORGANIK**, presentada como mejorador de suelos, y **BIOFERT-K**, descrita como complejante y a… |  |  |  |
| P25 | zero_shot | P | ok | U1 U2 | Manuelita Azúcar y Energía ha reportado el **Plan maestro de riego**, orientado a mejorar los sistemas de medición, conducción, aplicación y uso eficiente del … |  |  |  |
| P25 | final | P | ok | U1 U2 | La iniciativa de uso eficiente del agua que el corpus atribuye a Manuelita Azúcar y Energía es el **Plan maestro de riego**, orientado a mejorar los sistemas d… |  |  |  |
| P26 | zero_shot | D | ok | U1 U7 U3 | Manuelita enmarca el aprovechamiento de los residuos agroindustriales dentro de sus procesos de economía circular [U1]. En el caso de la caña, el bagazo se apr… |  |  |  |
| P26 | final | D | ok | U1 U2 U3 U7 | Manuelita enmarca el aprovechamiento de los residuos de sus procesos agroindustriales dentro de la economía circular, señalando que aprovecha esos residuos en … |  |  |  |
| P27 | zero_shot | D | ok | U1 U2 U4 U6 | Manuelita Azúcar y Energía publicó las siguientes acciones y resultados relacionados con la reducción de emisiones: - Mejoró sus sistemas de reducción de emisi… |  |  |  |
| P27 | final | D | ok | U1 U2 U6 U4 | **Acciones publicadas por Manuelita Azúcar y Energía** - Mejoró sus sistemas de reducción de emisiones en la planta de azúcar, como parte de un plan de reconve… |  |  |  |
| P28 | zero_shot | M | ok | U3 U5 U1 | Con el contexto disponible no se pueden identificar indicadores ambientales concretos ni comparar metodologías entre informes. Solo se evidencia que: - Se cons… |  |  |  |
| P28 | final | M | ok | U3 U5 U1 | El corpus permite afirmar algo sobre el **alcance** de los indicadores ambientales, pero no sobre sus metodologías de cálculo. Sobre el alcance: un informe con… |  |  |  |
| P29 | zero_shot | C | ok | U1 U4 U2 U3 U5 U6 U7 U8 | No encuentro en el contexto información sobre certificaciones de la producción de azúcar en Palmira ni sobre el alcance de cada una. Las unidades disponibles s… |  |  |  |
| P29 | final | C | ok | U1 U4 | El corpus no identifica ninguna certificación publicada por Manuelita para la producción de azúcar en Palmira. La única referencia relacionada es la mención de… |  |  |  |
| P30 | zero_shot | M | ok | U3 U2 | La documentación disponible solo permite confirmar que la certificación fue reportada u otorgada para un periodo determinado —por ejemplo, para el periodo 2018… |  |  |  |
| P30 | final | M | ok | U2 U3 U4 | El corpus permite confirmar únicamente que las certificaciones fueron **reportadas en momentos o periodos determinados**: se indica que Manuelita recibió la ce… |  |  |  |
| P31 | zero_shot | M | ok | U2 U4 U6 | El contexto no identifica fuentes oficiales externas (por ejemplo, entidades, informes o documentos) que respalden la afirmación. Los pasajes que sí la respald… |  |  |  |
| P31 | final | M | ok | U1 U2 U4 U6 U8 | El corpus no identifica documentos ni entidades oficiales (informes, certificaciones o registros públicos) que respalden la afirmación; solo contiene afirmacio… |  |  |  |
| P32 | zero_shot | P | ok | U3 U7 U6 U4 | Según el contexto, el canal oficial que puedes consultar es el **procedimiento para el uso de los canales de comunicación**, mediante una **solicitud a través … |  |  |  |
| P32 | final | P | ok | U3 U4 | El corpus indica que existe un procedimiento para el uso de los canales de comunicación, mediante una solicitud a través de la página web, en la que se deben d… |  |  |  |
| P33 | zero_shot | D | ok | U1 U2 U6 | Manuelita ha reportado programas de **educación** y **emprendimiento** dirigidos a familias de colaboradores y comunidades vecinas: entre 2023 y 2024 benefició… |  |  |  |
| P33 | final | D | ok | U1 U6 U5 U2 | Manuelita reportó programas de **educación** y de **emprendimiento** dirigidos a comunidades vecinas: entre 2023 y 2024 benefició a más de 4.000 familias de co… |  |  |  |
| P34 | zero_shot | D | ok | U5 U4 U3 | Puedes consultar la información oficial en la página web de Manuelita, en el ítem **“Línea Ética”**, o mediante el código QR dispuesto allí [U5]. La Línea Étic… |  |  |  |
| P34 | final | D | ok | U5 U3 U1 U4 | **Dónde consultar y cómo acceder a la Línea Ética** - La información oficial se publica en la **página web de la empresa**, en el ítem «Línea Ética», al que ta… |  |  |  |
| P35 | zero_shot | P | ok | U1 U3 U4 U6 | No encuentro en el contexto proporcionado información sobre los canales o sitios donde Manuelita publica sus oportunidades laborales, ni sobre orientaciones o … |  |  |  |
| P35 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P36 | zero_shot | D | ok | U1 U4 | Los valores corporativos de Manuelita que aparecen en el contexto son: - Integridad - Respeto por la gente y compromiso con su desarrollo - Responsabilidad Soc… |  |  |  |
| P36 | final | D | ok | U1 U4 U3 U5 | Manuelita enumera sus valores corporativos como Integridad; Respeto por la gente y compromiso con su desarrollo; Responsabilidad Social y Ambiental; Espíritu P… |  |  |  |
| P37 | zero_shot | D | ok | U2 U3 U4 U5 U7 U8 U6 | Con los fragmentos disponibles no es posible reconstruir una cronología completa ni una fecha de fundación, pero sí se observa una evolución desde una tradició… |  |  |  |
| P37 | final | D | ok | U2 U3 U4 U5 U7 | **Lo que el corpus permite afirmar** Manuelita conserva los principios que cimentaron su origen, orientados a generar progreso y bienestar con empresas y produ… |  |  |  |
| P38 | zero_shot | C | ok | U3 U5 | ## Respuesta Con el contexto disponible **no es posible hacer la comparación que pides**. Las unidades de información proporcionadas no describen tipos de azúc… |  |  |  |
| P38 | final | C | ok | U3 | El corpus disponible no permite comparar dos tipos de azúcar ni identificar certificaciones por producto o unidad de negocio: ninguna de las unidades entregada… |  |  |  |
| P39 | zero_shot | C | ok | U3 U1 U6 U7 U5 U2 | Según el contexto, para **Manuelita Azúcar y Energía** se reporta específicamente la certificación **BONSUCRO**, para la cual demostró que sus operaciones cuen… |  |  |  |
| P39 | final | C | ok | U3 U2 U1 U7 U6 U5 | **Lo reportado específicamente para Manuelita Azúcar y Energía** - Para obtener la certificación BONSUCRO, Manuelita Azúcar y Energía demostró que sus operacio… |  |  |  |
| P40 | zero_shot | S | ok | U7 U3 U5 U1 U2 U8 U4 U6 | Sí. Aquí tienes un borrador en español, con citas a las unidades disponibles y una nota sobre información no pública en el material consultado. --- **Borrador … |  |  |  |
| P40 | final | S | ok | U7 U3 U5 U1 U8 U2 U6 U4 | ## Borrador de comunicación para cliente **Productos** La oferta incluye los productos BIORGANIK y BIOFERT-K, elaborados a partir de fuentes renovables, que of… |  |  |  |

## Análisis de errores

Pendiente de la calificación humana: clasificar los fallos en recuperación, redacción, cita inválida, alucinación o falta de corpus, y registrar los ajustes en `docs/prompt_log.md`.
