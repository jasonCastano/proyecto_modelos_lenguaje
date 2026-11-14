# Evaluación del Módulo 1 — 40 preguntas

**Ejecución**: `m1-final-2026-11-14-r2` · **Fecha (UTC)**: 2026-11-14T16:35:31+00:00 · **Modelo**: `deepseek-flash` · **Modo**: real

**Comando**: `uv run python -m proyecto_modelos_lenguaje.module1_eval --run-id m1-final-2026-11-14-r2 --out docs/evaluacion_m1_r2.md --json-out docs/evaluacion_m1_r2.json`

Las métricas automáticas salen de la ejecución registrada en `docs/evaluacion_m1_r2.json`. Las columnas **Corrección** (0 incorrecta · 1 parcial · 2 correcta), **Coherencia** (1–5) y **Alucinación** (sí/no) las califica el equipo a mano; mientras estén vacías, el informe no puede citar esas cifras.

## Métricas automáticas por variante

| Variante | Preguntas | ok | review | fallback | error | Con cita | Acierto de fallback | Latencia media (s) | Desv. (s) | Tokens entrada | Tokens salida |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | 40 | 40 | 0 | 0 | 0 | 40 | 0.974 | 3.601 | 1.592 | 34685 | 20644 |
| final | 40 | 35 | 0 | 5 | 0 | 35 | 0.846 | 3.81 | 1.813 | 52965 | 22774 |

*Acierto de fallback*: proporción de respuestas cuyo *fallback* coincide con lo esperado en el alcance (`X` debe declarar falta de evidencia; el resto debe responder).

## Resultados por pregunta

| ID | Variante | Esperado | Estado | Citas | Respuesta | Corrección | Coherencia | Alucinación |
|---|---|---|---|---|---|---|---|---|
| P01 | zero_shot | D | ok | U1 U3 | El contexto no presenta de forma explícita la misión y la visión corporativas de Manuelita. Solo se menciona la **“Visión 3030”**, un programa de posconsumo y … |  |  |  |
| P01 | final | D | ok | U3 U2 U1 | El corpus no contiene el enunciado formal de la misión ni de la visión de Manuelita. Los elementos relacionados que sí aparecen son los siguientes: - Bajo el r… |  |  |  |
| P02 | zero_shot | D | ok | U3 U1 U6 U7 U2 | Según el contexto disponible: **Propósito** - La empresa se guía por un **propósito superior** y unas prioridades de sostenibilidad orientadas a lograr un mayo… |  |  |  |
| P02 | final | D | ok | U3 U6 U1 U2 | La empresa se guía por un **propósito superior** y unas prioridades de sostenibilidad orientadas a lograr un mayor bienestar en las comunidades, las regiones y… |  |  |  |
| P03 | zero_shot | D | ok | U1 U5 U2 U3 U4 U6 | Manuelita se fundó en **1864 en el Valle del Cauca, Colombia** [U1], y fue fundada por **Santiago Eder** [U5]. Desde su fundación, su objetivo ha sido **genera… |  |  |  |
| P03 | final | D | ok | U1 U5 U2 U4 U3 | **Fundación** Manuelita se fundó en 1864 en el Valle del Calca, Colombia [U1]. Su fundador fue Santiago Eder, y desde su creación el objetivo ha sido generar p… |  |  |  |
| P04 | zero_shot | D | ok | U3 U1 U2 | En el contexto no se identifica explícitamente al **fundador**. - **Dueños:** los **Eder** [U3]. - **Junta directiva:** está compuesta por **nueve miembros pri… |  |  |  |
| P04 | final | D | ok | U1 U2 U3 | La junta directiva está compuesta por nueve miembros principales, cada uno con su respectivo suplente [U1]. De esos nueve puestos, tres son directores independ… |  |  |  |
| P05 | zero_shot | D | ok | U8 U1 U4 U5 | Según el contexto disponible: - **Gerente:** la única referencia nominal es **Gloria Eugenia Medellín**, identificada como **Gerente de la Fundación Manuelita*… |  |  |  |
| P05 | final | D | ok | U8 U1 U5 | El corpus identifica a Gloria Eugenia Medellín como Gerente de la Fundación Manuelita [U8]. También se menciona de forma genérica la figura del «Gerente» como … |  |  |  |
| P06 | zero_shot | D | ok | U5 | El contexto no especifica dónde tiene sedes, plantas o cultivos, ni proporciona datos de contacto. Solo menciona que “Allí” se impulsan cultivos de uva de mesa… |  |  |  |
| P06 | final | D | ok | U5 U7 U2 U3 | El corpus no permite responder de forma completa: no contiene direcciones de la casa matriz, un listado de sedes ni canales de contacto (teléfonos, correos o f… |  |  |  |
| P07 | zero_shot | D | ok | U4 U5 U2 U7 | Manuelita ofrece: - Un portafolio de **azúcar y derivados de valor agregado** para industrias de Colombia, Perú y otros países vecinos, en sectores alimenticio… |  |  |  |
| P07 | final | D | ok | U4 U5 U2 U7 U1 | Manuelita ofrece un portafolio de azúcar y derivados de valor agregado dirigido a las industrias alimenticia y de bebidas, química y farmacéutica de Colombia, … |  |  |  |
| P08 | zero_shot | P | ok | U1 U5 U6 | No encuentro en el contexto información sobre fichas técnicas o especificaciones de productos. Lo que sí aparece son referencias a "especificaciones técnicas y… |  |  |  |
| P08 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P09 | zero_shot | P | ok | U1 | El contexto no permite afirmar que Manuelita maneje precios, tarifas o planes públicos, ni indica dónde están sus catálogos. La única referencia a precios es s… |  |  |  |
| P09 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P10 | zero_shot | P | ok | U4 U7 U6 U3 | Sus clientes son, en su mayoría, empresas de los sectores de alimentos, bebidas, farmacopea, entre otras, a las que comercializan azúcar refinada [U4]. Entre s… |  |  |  |
| P10 | final | P | ok | U4 U6 U1 U7 U3 | **Clientes.** La empresa comercializa azúcar refinada a clientes que en su mayoría son empresas de los sectores de alimentos, bebidas y farmacopea, entre otras… |  |  |  |
| P11 | zero_shot | D | ok | U1 U5 U2 U3 U4 U6 | El contexto menciona las siguientes certificaciones: - **ISO 14001:2004** [U1] y también **ISO 14064-1** para verificación de emisiones de GEI [U5]. - **BASC**… |  |  |  |
| P11 | final | D | ok | U3 U6 U4 U1 U5 U2 | Con lo que aporta el corpus: **RSPO** - La torta de palmiste de Manuelita está certificada bajo los estándares de sostenibilidad RSPO [U3]. - Manuelita Aceites… |  |  |  |
| P12 | zero_shot | P | ok | U1 U3 U4 U6 U7 | No hay en el contexto una lista completa de “noticias y artículos más relevantes”. Lo que sí se menciona es: - La modificación de algunos artículos del Decreto… |  |  |  |
| P12 | final | P | ok | U7 | El corpus no incluye un listado de noticias o artículos. La única unidad que alude a noticias menciona que, en el comparativo febrero–marzo de 2016, el precio … |  |  |  |
| P13 | zero_shot | D | ok | U1 | No hay información suficiente en el contexto para responder esa pregunta. El único dato disponible sobre YouTube es la dirección del canal institucional: `http… |  |  |  |
| P13 | final | D | ok | U1 | El corpus solo identifica el canal de YouTube de Manuelita Agroindustria, sin detallar los videos ni las transcripciones que publica allí [U1]. El corpus no es… |  |  |  |
| P14 | zero_shot | X | ok | U8 U4 | El contexto proporcionado no contiene un listado de entrevistas disponibles del gerente. Lo más cercano es: - **U8**: intervención de Diego Salazar, gerente co… |  |  |  |
| P14 | final | X | ok | U8 | El corpus no contiene un listado de entrevistas disponibles del gerente. Lo único relacionado es un fragmento en el que Diego Salazar se identifica como gerent… |  |  |  |
| P15 | zero_shot | P,X | ok | U1 U3 U8 | Manuelita publica en redes sociales información pública de carácter institucional [U1]. También usa fotografías, audio y video en publicaciones digitales y red… |  |  |  |
| P15 | final | P,X | ok | U1 U3 U8 U5 U7 | Con el corpus disponible solo puede responderse de forma parcial: no se detalla qué contenidos concretos se publican, pero sí se indica lo siguiente: - La info… |  |  |  |
| P16 | zero_shot | P | ok | U1 U3 U4 | El contexto proporcionado no especifica qué vacantes concretas se publican ni en qué plataforma o canal se publican. Lo que sí aparece es lo siguiente: - Exist… |  |  |  |
| P16 | final | P | ok | U3 U4 | El corpus no especifica cuáles vacantes concretas se publican ni el lugar o canal donde se publican. Lo que sí aparece es lo siguiente: - La disponibilidad de … |  |  |  |
| P17 | zero_shot | D | ok | U1 | El contexto disponible no indica dónde se ubican los informes financieros ni la memoria anual; solo se menciona que unos Estados Financieros "acompañan este in… |  |  |  |
| P17 | final | D | ok | U1 U2 | El corpus no indica la ubicación ni el enlace de los informes financieros o de la memoria anual. Solo hay referencias indirectas: se mencionan unos «Estados Fi… |  |  |  |
| P18 | zero_shot | D | ok | U3 U6 U2 | El NIT es **900.734.835-8** [U3][U6]. No se encuentra en el contexto el número del **registro mercantil**; solo se menciona que “por el registro se canceló $1.… |  |  |  |
| P18 | final | D | ok | U3 U6 U1 | El corpus solo permite identificar el NIT de la Fundación Manuelita: 900.734.835-8, según la certificación de su representante legal [U3], y 900734835-8, según… |  |  |  |
| P19 | zero_shot | D | ok | U5 U3 U4 U7 U8 U2 | Reporta, entre otros: - Inversión social y ambiental: más de 23.600 millones de pesos en programas sociales y más de 10.500 millones en iniciativas ambientales… |  |  |  |
| P19 | final | D | ok | U5 U1 U3 U4 U7 U2 U8 U6 | El corpus permite responder solo parcialmente. Esto es lo que se reporta: **Programas sociales y ambientales (inversión)** - Manuelita invierte más de 23.600 m… |  |  |  |
| P20 | zero_shot | P | ok | U2 U3 U8 | Con el contexto proporcionado, no es posible identificar precios públicos, datos abiertos ni rankings sectoriales específicos. Solo se define qué pueden ser lo… |  |  |  |
| P20 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P21 | zero_shot | C | ok | U4 U2 | La información proporcionada no especifica qué tipos de azúcar ofrece Manuelita ni sus diferencias. Solo indica que ofrece un portafolio de azúcar y derivados … |  |  |  |
| P21 | final | C | ok | U4 U2 | El corpus indica que Manuelita ofrece un portafolio de azúcar y derivados de valor agregado dirigido a las industrias alimenticia y de bebidas, química y farma… |  |  |  |
| P22 | zero_shot | P | ok | U8 U1 | Manuelita ofrece **azúcar y derivados de valor agregado** para los sectores alimenticio y de bebidas, entre otros [U8]. Además, el contexto documenta un produc… |  |  |  |
| P22 | final | P | ok | U8 U1 | Manuelita ofrece **azúcar y derivados de valor agregado** para los sectores alimenticio y de bebidas [U8]. Además, el corpus menciona un producto, cuyo nombre … |  |  |  |
| P23 | zero_shot | P | ok | U1 U2 | Manuelita publica para sus productos de azúcar industrial: **azúcar refinada, morena y blanca en diferentes presentaciones**, y para clientes industriales y ex… |  |  |  |
| P23 | final | P | ok | U1 U2 | Para el canal industrial, Manuelita publica un portafolio que incluye azúcar refinada, morena y blanca en diferentes presentaciones [U1]. Además, Manuelita Azú… |  |  |  |
| P24 | zero_shot | D | ok | U1 U4 | Según el contexto disponible: - **BIORGANIK**: se comercializa como **mejorador de suelos** [U1]; de forma más detallada, se describe como un **acondicionador … |  |  |  |
| P24 | final | D | ok | U1 U4 | **BIORGANIK** - Se comercializa en el mercado colombiano como marca de un mejorador de suelos [U1]. - Se describe como un acondicionador orgánico para el mejor… |  |  |  |
| P25 | zero_shot | P | ok | U1 U2 | Manuelita Azúcar y Energía ha reportado el **Plan maestro de riego**, cuyo objetivo es mejorar los sistemas de medición, conducción, aplicación y uso eficiente… |  |  |  |
| P25 | final | P | ok | U1 U2 | **Iniciativas reportadas por Manuelita Azúcar y Energía (Valle del Cauca):** - El **Plan maestro de riego**, cuyo objetivo es mejorar los sistemas de medición,… |  |  |  |
| P26 | zero_shot | D | ok | U1 U2 U3 U7 | Manuelita lo describe como parte de su estrategia de economía circular: aprovecha los residuos de sus procesos agroindustriales y considera la agroindustria de… |  |  |  |
| P26 | final | D | ok | U1 U2 U3 U7 | Manuelita enmarca el aprovechamiento de los residuos de sus procesos agroindustriales dentro de la economía circular, y señala que la agroindustria de la caña … |  |  |  |
| P27 | zero_shot | D | ok | U1 U2 | Manuelita Azúcar y Energía mejoró sus sistemas de reducción de emisiones en la planta de azúcar como parte de su plan de reconversión a tecnologías más limpias… |  |  |  |
| P27 | final | D | ok | U1 U2 U4 U6 | **Acciones** - Como parte de su plan de reconversión a tecnologías más limpias, Manuelita Azúcar y Energía mejoró los sistemas de reducción de emisiones en la … |  |  |  |
| P28 | zero_shot | M | ok | U3 U5 U1 U7 | ## Respuesta **Indicadores comparables (según el alcance declarado en el contexto)** El contexto permite identificar que los indicadores ambientales se reporta… |  |  |  |
| P28 | final | M | ok | U3 U5 U1 | El corpus permite señalar únicamente diferencias de **alcance** entre reportes, no una comparación de indicadores concretos: - Un informe consolida indicadores… |  |  |  |
| P29 | zero_shot | C | ok | U1 U4 U5 | Con el contexto disponible no es posible determinar qué certificaciones publica Manuelita para la producción de azúcar en Palmira ni el alcance de cada una. So… |  |  |  |
| P29 | final | C | ok | U1 U4 U3 U6 U7 U5 | El corpus no enumera certificaciones otorgadas a la producción de azúcar de Manuelita en Palmira. La única referencia relacionada es la mención de un «Alcance … |  |  |  |
| P30 | zero_shot | M | ok | U3 U2 | La documentación solo permite confirmar que la certificación fue **reportada/obtenida en un periodo determinado**, no su vigencia actual. El texto indica que M… |  |  |  |
| P30 | final | M | ok | U2 U3 U4 | La documentación disponible solo permite confirmar que las certificaciones fueron reportadas en un momento o periodo determinado, no su vigencia. - Se registra… |  |  |  |
| P31 | zero_shot | M | ok | U2 U4 U6 U7 U1 | El contexto disponible no identifica fuentes oficiales externas (por ejemplo, entidades regulatorias, certificaciones o informes auditados). Lo que respalda la… |  |  |  |
| P31 | final | M | ok | U2 U4 U6 U8 | El corpus sí respalda la afirmación, pero no identifica fuentes oficiales que la respalden. Lo que la evidencia muestra es lo siguiente: - Manuelita Aceites y … |  |  |  |
| P32 | zero_shot | P | ok | U3 U6 | Según el contexto disponible, el canal oficial documentado para realizar solicitudes es la **página web**, mediante un formulario en el que se deben diligencia… |  |  |  |
| P32 | final | P | ok | U3 U6 | El corpus solo registra un canal oficial de comunicación: el **procedimiento para el uso de los canales de comunicación**, que contempla la solicitud a través … |  |  |  |
| P33 | zero_shot | D | ok | U1 U6 U5 U2 | Según el contexto disponible, Manuelita reporta lo siguiente: - **Programas de educación y emprendimiento:** entre 2023 y 2024 benefició a más de 4.000 familia… |  |  |  |
| P33 | final | D | ok | U1 U2 U6 | Manuelita reportó que entre 2023 y 2024 benefició a más de 4.000 familias de colaboradores y comunidades vecinas mediante programas de educación, vivienda, sal… |  |  |  |
| P34 | zero_shot | D | ok | U5 U3 U4 | Puedes consultar la información oficial en la página web de la empresa, en el ítem de **Línea Ética**, o mediante el código QR dispuesto allí [U5]. Para accede… |  |  |  |
| P34 | final | D | ok | U4 U5 U3 | **Dónde se consulta y qué es.** La Línea Ética Manuelita es un servicio de información, anónimo e independiente, destinado a comunicar todo hecho irregular que… |  |  |  |
| P35 | zero_shot | P | ok | U1 U3 U4 U6 | No encuentro en el contexto proporcionado información sobre dónde publica Manuelita sus oportunidades laborales ni sobre orientaciones o instrucciones para pos… |  |  |  |
| P35 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P36 | zero_shot | D | ok | U1 U4 | Los valores corporativos de Manuelita son: **Integridad; Respeto por la gente y compromiso con su desarrollo; Responsabilidad Social y Ambiental; Espíritu Pion… |  |  |  |
| P36 | final | D | ok | U1 U4 U5 | Los valores corporativos que figuran en el corpus son: Integridad; Respeto por la gente y compromiso con su desarrollo; Responsabilidad Social y Ambiental; Esp… |  |  |  |
| P37 | zero_shot | D | ok | U2 U3 U4 U5 U7 U8 U6 | No hay evidencia suficiente en el contexto para detallar una cronología completa de la evolución de Manuelita desde su origen en Palmira ni para enumerar todos… |  |  |  |
| P37 | final | D | ok | U2 U3 U4 U5 U7 | El corpus no permite reconstruir una cronología completa de la evolución de Manuelita ni confirma explícitamente que su origen haya sido en Palmira. Sí aporta … |  |  |  |
| P38 | zero_shot | C | ok | U3 | No puedo comparar dos tipos de azúcar ni identificar certificaciones publicadas por producto y unidad de negocio con la información disponible. El contexto no … |  |  |  |
| P38 | final | C | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P39 | zero_shot | C | ok | U3 U6 U7 U1 | Para **Manuelita Azúcar y Energía** se reporta específicamente la obtención de la **certificación BONSUCRO**, con la que demostró que sus operaciones cuentan c… |  |  |  |
| P39 | final | C | ok | U3 U2 U6 U7 U1 | ## Iniciativas reportadas para Manuelita Azúcar y Energía La única iniciativa atribuida de forma específica a Manuelita Azúcar y Energía en el corpus es la **c… |  |  |  |
| P40 | zero_shot | S | ok | U1 U2 U3 U7 U5 U8 | **Borrador de comunicación para cliente** **Asunto:** Productos, calidad y sostenibilidad — resumen informativo Estimado/a [Nombre del cliente]: Compartimos un… |  |  |  |
| P40 | final | S | ok | U7 U3 U4 U5 U1 U8 U2 U6 | ## Borrador de comunicación para cliente **1. Productos** Los productos BIORGANIK y BIOFERT‑K se elaboran a partir de fuentes renovables y ofrecen múltiples be… |  |  |  |

## Análisis de errores

Pendiente de la calificación humana: clasificar los fallos en recuperación, redacción, cita inválida, alucinación o falta de corpus, y registrar los ajustes en `docs/prompt_log.md`.
