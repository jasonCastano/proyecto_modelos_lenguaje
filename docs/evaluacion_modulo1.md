# Evaluación del Módulo 1 — 40 preguntas

**Ejecución**: `m1-eval-2026-11-10-deepseek` · **Fecha (UTC)**: 2026-11-10T21:23:09+00:00 · **Modelo**: `deepseek-flash` · **Modo**: real

**Comando**: `uv run python -m proyecto_modelos_lenguaje.module1_eval --run-id m1-eval-2026-11-10-deepseek`

Las métricas automáticas salen de la ejecución registrada en `docs/evaluacion_modulo1.json`. Las columnas **Corrección** (0 incorrecta · 1 parcial · 2 correcta), **Coherencia** (1–5) y **Alucinación** (sí/no) las califica el equipo a mano; mientras estén vacías, el informe no puede citar esas cifras.

## Métricas automáticas por variante

| Variante | Preguntas | ok | review | fallback | error | Con cita | Acierto de fallback | Latencia media (s) | Desv. (s) | Tokens entrada | Tokens salida |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | 40 | 40 | 0 | 0 | 0 | 40 | 0.974 | 3.772 | 1.675 | 34685 | 20715 |
| final | 40 | 23 | 0 | 17 | 0 | 23 | 0.59 | 3.65 | 3.113 | 49645 | 20242 |

*Acierto de fallback*: proporción de respuestas cuyo *fallback* coincide con lo esperado en el alcance (`X` debe declarar falta de evidencia; el resto debe responder).

## Resultados por pregunta

| ID | Variante | Esperado | Estado | Citas | Respuesta | Corrección | Coherencia | Alucinación |
|---|---|---|---|---|---|---|---|---|
| P01 | zero_shot | D | ok | U3 U6 U1 | Con la información disponible en el contexto no es posible identificar de forma explícita los enunciados corporativos de la misión y la visión de Manuelita. Lo… |  |  |  |
| P01 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P02 | zero_shot | D | ok | U3 U6 U1 | La empresa se guía por un **propósito superior** orientado a la sostenibilidad y al mayor bienestar de sus comunidades, regiones y la sociedad en general `[U3]… |  |  |  |
| P02 | final | D | ok | U1 U3 U6 | El corpus señala que la fidelidad a un propósito y a unos valores fundamentales es la razón por la que una empresa puede perdurar a lo largo de seis generacion… |  |  |  |
| P03 | zero_shot | D | ok | U1 U5 U2 U3 U4 U6 | Manuelita se fundó en **1864**, en el Valle del Calca, Colombia, y fue fundada por **Santiago Eder** [U1][U5]. Entre los hitos mencionados en el contexto están… |  |  |  |
| P03 | final | D | ok | U1 U5 U2 U4 U3 U6 | **Fundación** Manuelita se fundó en 1864, en el Valle del Calca, Colombia [U1]. Su fundador fue Santiago Eder, y desde entonces el objetivo declarado ha sido g… |  |  |  |
| P04 | zero_shot | D | ok | U3 U1 U2 | - **Fundador:** no hay información en el contexto proporcionado. - **Dueños:** los Eder [U3]. - **Junta directiva:** está compuesta por nueve miembros principa… |  |  |  |
| P04 | final | D | ok | U1 U2 U3 | **Junta directiva:** está compuesta por nueve miembros principales, cada uno con su respectivo suplente [U1]. De esos nueve puestos, tres corresponden a direct… |  |  |  |
| P05 | zero_shot | D | ok | U8 U1 U4 U5 | Según el contexto, **Gloria Eugenia Medellín** aparece como **Gerente de la Fundación Manuelita** [U8]. También se menciona al “Gerente” como responsable de de… |  |  |  |
| P05 | final | D | ok | U8 | El contexto solo permite identificar a una persona con el cargo de gerente: Gloria Eugenia Medellín aparece como Gerente de la Fundación Manuelita [U8]. Sobre … |  |  |  |
| P06 | zero_shot | D | ok | U7 U5 U6 U1 U2 U3 | Con la información disponible, se mencionan **plantas industriales en Presidente** [U7], **cultivos de uva de mesa y espárragos para exportación** [U5], **cult… |  |  |  |
| P06 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P07 | zero_shot | D | ok | U2 U4 U5 U7 | Manuelita ofrece productos diferenciados con valor agregado y alta calidad [U2]. Su portafolio incluye azúcar y derivados de valor agregado para industrias ali… |  |  |  |
| P07 | final | D | ok | U4 U5 U2 U1 | Manuelita ofrece un portafolio de azúcar y derivados de valor agregado dirigido a las industrias alimenticia y de bebidas, química y farmacéutica de Colombia, … |  |  |  |
| P08 | zero_shot | P | ok | U1 U6 | No encuentro en el contexto información sobre fichas técnicas o especificaciones de productos. Lo más cercano es una referencia a especificaciones técnicas y o… |  |  |  |
| P08 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P09 | zero_shot | P | ok | U1 | No encuentro en el contexto evidencia de que Manuelita maneje precios, tarifas o planes públicos, ni referencia alguna a catálogos de precios o tarifas. Lo úni… |  |  |  |
| P09 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P10 | zero_shot | P | ok | U4 U7 U6 U3 | Según el contexto, sus clientes son en su mayoría empresas de los sectores de alimentos, bebidas, farmacopea, entre otras, a quienes comercializan azúcar refin… |  |  |  |
| P10 | final | P | ok | U4 U6 U7 U1 U3 | Según el corpus, los clientes de la operación azucarera son en su mayoría empresas de los sectores de alimentos, bebidas y farmacopea, a las que se comercializ… |  |  |  |
| P11 | zero_shot | D | ok | U1 U5 U2 U3 U6 U4 | Manuelita presenta, según el contexto, las siguientes certificaciones o referencias: - **ISO**: **ISO 14001:2004** [U1] y **ISO 14064-1** para verificación de … |  |  |  |
| P11 | final | D | ok | U1 U5 U2 U3 U6 U4 | En el corpus aparecen estas referencias a certificaciones: - **ISO:** se menciona **ISO 14001:2004** en la tabla de certificaciones [U1] y **ISO 14064-1** para… |  |  |  |
| P12 | zero_shot | P | ok | U7 | La noticia más relevante en el contexto es que, en el comparativo febrero–marzo de 2016, el precio internacional del azúcar se incrementó en 12% [U7]. No se id… |  |  |  |
| P12 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P13 | zero_shot | D | ok | U1 | El contexto solo aporta el enlace al canal de YouTube (`https://www.youtube.com/@ManuelitaAgroindustria`) [U1], pero no incluye información sobre qué videos o … |  |  |  |
| P13 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P14 | zero_shot | X | ok | U8 U4 | No se puede determinar con el contexto: no se enumeran entrevistas disponibles del gerente. Solo aparece un fragmento atribuido a Diego Salazar, gerente corpor… |  |  |  |
| P14 | final | X | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P15 | zero_shot | P,X | ok | U1 U3 U8 U4 U5 U7 | Según el contexto disponible, Manuelita publica en sus redes sociales: - **Información de carácter institucional**: la información divulgada en las redes socia… |  |  |  |
| P15 | final | P,X | ok | U1 U3 U8 | La información divulgada en las redes sociales donde la Fundación Manuelita es titular de una cuenta es pública y de carácter exclusivamente institucional [U1]… |  |  |  |
| P16 | zero_shot | P | ok | U4 U3 | No encuentro en el contexto información sobre vacantes de empleo específicas ni sobre los canales o lugares donde se publican. Las unidades disponibles solo me… |  |  |  |
| P16 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P17 | zero_shot | D | ok | U1 U8 | El contexto no especifica dónde se encuentran los informes financieros ni la memoria anual. Solo menciona que unos Estados Financieros acompañan “este informe”… |  |  |  |
| P17 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P18 | zero_shot | D | ok | U3 U6 | El NIT es **900.734.835-8** [U3][U6]. No aparece en el contexto el número de **registro mercantil** de la empresa. |  |  |  |
| P18 | final | D | ok | U3 U6 U1 | El contexto identifica un NIT correspondiente a la FUNDACIÓN MANUELITA: 900.734.835-8 [U3], cifra que aparece con el mismo número aunque sin puntos de separaci… |  |  |  |
| P19 | zero_shot | D | ok | U5 U1 U3 U8 U2 U4 U7 | Reporta, entre otros: - Inversión en **programas sociales** por más de **23.600 millones de pesos** y en **iniciativas ambientales** por más de **10.500 millon… |  |  |  |
| P19 | final | D | ok | U5 U3 U4 U7 U2 U8 U6 | El corpus permite identificar los siguientes elementos reportados: - Inversión en programas sociales superior a 23.600 millones de pesos y en iniciativas ambie… |  |  |  |
| P20 | zero_shot | P | ok | U2 U3 U8 | El contexto disponible no contiene información sobre precios públicos, datos abiertos ni rankings sectoriales, por lo que no puedo responder a esa pregunta con… |  |  |  |
| P20 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P21 | zero_shot | C | ok | U4 U2 | Con la información disponible en el contexto no es posible responder la pregunta. El contexto solo menciona de forma muy general que Manuelita ofrece "un porta… |  |  |  |
| P21 | final | C | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P22 | zero_shot | P | ok | U8 U1 | Con la evidencia del contexto, Manuelita tiene aplicaciones documentadas para el sector de bebidas en: - **Azúcar y derivados de valor agregado**, dirigidos, e… |  |  |  |
| P22 | final | P | ok | U8 U1 | Según el corpus, Manuelita ofrece un portafolio de **azúcar y derivados de valor agregado** dirigido, entre otros, a los sectores alimenticio y de bebidas [U8]… |  |  |  |
| P23 | zero_shot | P | ok | U1 U2 | Manuelita publica para el canal industrial un portafolio de **azúcar refinada, morena y blanca en diferentes presentaciones** [U1]. Además, para **Manuelita Az… |  |  |  |
| P23 | final | P | ok | U1 U2 | Manuelita ofrece a sus clientes industriales azúcar refinada, morena y blanca en diferentes presentaciones [U1]. Asimismo, Manuelita Azúcar y Energía y Agroind… |  |  |  |
| P24 | zero_shot | D | ok | U1 U4 | Según el contexto disponible: **BIORGANIK** es un mejorador de suelos y, más específicamente, un acondicionador orgánico para el mejoramiento del suelo y un re… |  |  |  |
| P24 | final | D | ok | U1 U4 | **BIORGANIK** - Es un mejorador de suelos que se comercializa en el mercado colombiano bajo esa marca [U1]. - Se describe como un acondicionador orgánico para … |  |  |  |
| P25 | zero_shot | P | ok | U1 U2 | Manuelita Azúcar y Energía reporta el **Plan maestro de riego**, orientado a mejorar los sistemas de medición, conducción, aplicación y uso eficiente del agua … |  |  |  |
| P25 | final | P | ok | U1 U2 | Manuelita Azúcar y Energía reportó el **Plan maestro de riego**, cuyo objetivo es mejorar los sistemas de medición, conducción, aplicación y uso eficiente del … |  |  |  |
| P26 | zero_shot | D | ok | U1 U3 U7 | Manuelita enmarca el aprovechamiento de los residuos agroindustriales dentro de sus procesos de economía circular [U1]. En el caso de la caña, describe el uso … |  |  |  |
| P26 | final | D | ok | U1 U2 U3 U7 | Manuelita enmarca el aprovechamiento de los residuos de sus procesos agroindustriales dentro de la economía circular [U1], y señala que la agroindustria de la … |  |  |  |
| P27 | zero_shot | D | ok | U1 U2 U6 U4 | Manuelita Azúcar y Energía ha publicado las siguientes acciones y resultados relacionados con la reducción de emisiones: - **Acción:** mejoró sus sistemas de r… |  |  |  |
| P27 | final | D | ok | U1 U2 | Manuelita Azúcar y Energía mejoró sus sistemas de reducción de emisiones en la planta de azúcar como parte de un plan de reconversión a tecnologías más limpias… |  |  |  |
| P28 | zero_shot | M | ok | U3 U5 U1 | Con el contexto disponible **no es posible identificar indicadores ambientales concretos comparables ni precisar diferencias de metodología o alcance** entre i… |  |  |  |
| P28 | final | M | ok | U3 U5 U1 | El corpus no enumera indicadores ambientales específicos que permitan una comparación directa entre informes. La evidencia disponible indica que un informe con… |  |  |  |
| P29 | zero_shot | C | ok | U1 U4 U2 U3 U6 U7 U5 U8 | El contexto disponible no contiene información sobre certificaciones específicas que Manuelita publique para la producción de azúcar en Palmira. El único eleme… |  |  |  |
| P29 | final | C | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P30 | zero_shot | M | ok | U3 U2 | La documentación permite confirmar principalmente que la certificación fue **reportada/obtenida en un periodo determinado**: se mencionan 170.308 créditos de r… |  |  |  |
| P30 | final | M | ok | U2 U3 U4 | La documentación disponible solo permite confirmar que las certificaciones fueron reportadas en momentos o periodos determinados, no su vigencia actual. En un … |  |  |  |
| P31 | zero_shot | M | ok | U2 U4 U6 U8 | El contexto no identifica **fuentes oficiales** concretas (informes, registros públicos o entidades) que respalden la afirmación. Solo se puede afirmar que las… |  |  |  |
| P31 | final | M | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P32 | zero_shot | P | ok | U3 | Puedes consultar el **procedimiento para el uso de los canales de comunicación** y radicar la solicitud **a través de la página web**, diligenciando los campos… |  |  |  |
| P32 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P33 | zero_shot | D | ok | U1 U6 U2 | Manuelita ha reportado de forma general programas de **educación** y **emprendimiento** dirigidos a colaboradores y comunidades vecinas [U1]. En educación, el … |  |  |  |
| P33 | final | D | ok | U1 U6 U2 | Manuelita reportó programas de educación y emprendimiento dirigidos a familias de colaboradores y comunidades vecinas, junto con iniciativas de vivienda y salu… |  |  |  |
| P34 | zero_shot | D | ok | U3 U5 U4 | Puedes consultar la información oficial y acceder al canal de la Línea Ética por varias vías: - **Correo del Oficial de Cumplimiento:** oclaftpalmar@manuelita.… |  |  |  |
| P34 | final | D | ok | U5 U4 U3 U7 | La información oficial sobre la Línea Ética se puede consultar en la página web de la empresa, en el ítem de «línea ética», al que también se accede mediante u… |  |  |  |
| P35 | zero_shot | P | ok | U1 U3 U4 | El contexto no especifica dónde publica Manuelita sus oportunidades laborales ni qué orientaciones ofrece para postularse. Solo menciona el respeto por las opo… |  |  |  |
| P35 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P36 | zero_shot | D | ok | U1 U4 | Los valores corporativos de Manuelita son: **Integridad; Respeto por la gente y compromiso con su desarrollo; Responsabilidad Social y Ambiental; Espíritu Pion… |  |  |  |
| P36 | final | D | ok | U1 U4 U5 | Los valores corporativos que la organización enuncia son: integridad, respeto por la gente y compromiso con su desarrollo, responsabilidad social y ambiental, … |  |  |  |
| P37 | zero_shot | D | ok | U2 U3 U4 U5 U7 U8 | Con la evidencia del contexto no es posible reconstruir una cronología completa ni fechar el origen de Manuelita en Palmira. Lo que sí queda documentado es lo … |  |  |  |
| P37 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P38 | zero_shot | C | ok | U3 U1 U2 U4 U5 U6 U7 U8 | No puedo hacer esa comparación con la información disponible. El contexto proporcionado no describe tipos de azúcar ni enumera certificaciones por producto o u… |  |  |  |
| P38 | final | C | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P39 | zero_shot | C | ok | U3 U1 U5 U6 U7 | Para **Manuelita Azúcar y Energía** se reporta específicamente la obtención de la **certificación BONSUCRO**, para la cual demostró que sus operaciones cuentan… |  |  |  |
| P39 | final | C | ok | U3 U2 U1 U6 U7 U5 | ## Iniciativas reportadas específicamente para Manuelita Azúcar y Energía La única iniciativa ambiental y social que el corpus atribuye de forma explícita a Ma… |  |  |  |
| P40 | zero_shot | S | ok | U7 U3 U5 U1 U8 | **Borrador para cliente — Productos, calidad y sostenibilidad** *Uso informativo; pendiente de validación comercial y técnica.* Estimado/a cliente: Le comparti… |  |  |  |
| P40 | final | S | ok | U7 U5 U3 U1 U2 U8 | Sí. Borrador para cliente: **Productos y beneficios** - Los productos BIORGANIK y BIOFERT-K se elaboran a partir de fuentes renovables y ofrecen beneficios par… |  |  |  |

## Análisis de errores

Pendiente de la calificación humana (M1-09): clasificar los fallos en recuperación, redacción, cita inválida, alucinación o falta de corpus, y registrar los ajustes en `docs/prompt_log.md`.
