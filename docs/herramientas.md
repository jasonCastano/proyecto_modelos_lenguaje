# Catálogo de herramientas de Valer-IA Caña

> Generado con `uv run python -m proyecto_modelos_lenguaje.agent tools --markdown docs/herramientas.md` desde `src/proyecto_modelos_lenguaje/agent/catalog.py` (spec 024, ítem 1.1). No editar a mano.

Regla de oro: **lectura automática, escritura con aprobación**. Las de lectura marcadas «MCP» también se exponen por el servidor MCP `valeria-tools`; simular y optimizar la producción (spec 025) solo existen en el backend. Las de escritura piden «SÍ/NO» en la web y en WhatsApp. Las herramientas 21–26 usan datos **sintéticos** de demostración y solo las ve el perfil planificador.

| # | Herramienta | Tipo | Rutas | Fuente | Descripción |
|---:|---|---|---|---|---|
| 1 | `search_documents` | lectura (MCP) | documental, mixed, structured | Qdrant híbrida sobre gold/knowledge_units | Busca en los documentos públicos de Manuelita (historia, productos, sostenibilidad, programas, operaciones) con búsqueda híbrida y devuelve fragmentos citables [U#]. |
| 2 | `query_structured` | lectura (MCP) | documental, mixed, structured | tabla SQLite estructurada derivada del oro | Consulta datos puntuales de Manuelita y sus filiales (años, cifras, capacidades) y cuenta o lista entidades; cada dato trae su fuente [F#]. |
| 3 | `aggregate_series` | lectura (MCP) | documental, mixed, structured | data/curated/series_anuales.csv | Cifras anuales curadas (ventas, EBITDA, producción…) con suma, promedio, máximo, mínimo o variación calculados en código con Decimal; cita la fuente [F#]. |
| 4 | `list_indicators` | lectura (MCP) | structured | data/curated/series_anuales.csv | Lista los indicadores anuales curados de Manuelita (ventas, EBITDA, azúcar, bioetanol…) con su unidad y los años publicados; úsala antes de pedir una cifra o comparación [F#]. |
| 5 | `compare_indicator` | lectura (MCP) | mixed, structured | data/curated/series_anuales.csv (Decimal) | Compara un indicador anual entre dos años distintos: variación absoluta y porcentual calculadas en código con Decimal, con la fuente de cada cifra [F#]. |
| 6 | `sustainability_lookup` | lectura (MCP) | documental | Qdrant híbrida con filtro por payload (topic_id + términos del eje) | Busca evidencia de sostenibilidad de Manuelita por eje (agua, carbono, energía, residuos, biodiversidad o social) con búsqueda híbrida filtrada por tema; cita [U#]. |
| 7 | `list_business_units` | lectura (MCP) | structured | gold/entities.jsonl (subsidiary, company) + series anuales | Lista la empresa y las filiales o unidades de negocio de Manuelita con su país y plataforma, opcionalmente filtradas por país; cada una con su evidencia [F#]. |
| 8 | `list_company_entities` | lectura (MCP) | structured | gold/entities.jsonl | Lista las certificaciones o las marcas de Manuelita registradas en el oro, cada una con un fragmento que la menciona como evidencia [F#]. |
| 9 | `get_official_channels` | lectura (MCP) | direct, documental | config/official_channels.toml + oro (contacto) | Canales oficiales de contacto de Manuelita según el propósito (general, empleo, proveedores, clientes o prensa), publicados en su sitio y redes; cita [F#]. |
| 10 | `faq_lookup` | lectura (MCP) | documental | gold/faq_seeds.jsonl + unidades de evidencia | Busca la pregunta frecuente del oro más parecida a la del usuario y devuelve sus unidades de evidencia citables [U#]. |
| 11 | `summarize_topic` | lectura (MCP) | documental | gold/topics/*.md + unidades del tema | Panorama extractivo de un tema del oro (identidad, productos, sedes, fundación…): devuelve las unidades más representativas con su cita [U#], sin resumen generado. |
| 12 | `latest_news` | lectura (MCP) | documental | unidades fechadas del tema noticias (published_at) | Noticias y comunicados de Manuelita más recientes según su fecha de publicación, opcionalmente desde un año; cada noticia se cita [U#]. |
| 13 | `get_fragment` | lectura (MCP) | documental | gold/knowledge_units.jsonl | Devuelve el texto completo, la URL y las páginas de una unidad de oro por su unit_id (p. ej. para ampliar una cita) [U#]. |
| 14 | `calculate` | lectura (MCP) | direct, mixed, structured | aritmética Decimal con AST seguro (sin eval) | Calculadora exacta con Decimal: una expresión aritmética (+ - * / % y paréntesis) o una operación percent_change, ratio o sum sobre valores; nunca calcules a mano [F#]. |
| 15 | `get_my_profile` | lectura (MCP) | direct | SqliteStore (profile, preferences) | Muestra lo que el usuario guardó de sí mismo (nombre, trabajo, cargo, ciudad) y sus preferencias; solo del usuario actual. |
| 16 | `save_profile` | escritura (HITL) | clarify, direct, documental, mixed, out_of_scope, planning, structured | Store ("users", id, "profile") | Guardar datos del perfil del usuario (nombre, trabajo, cargo o ciudad). Requiere aprobación humana antes de ejecutarse. |
| 17 | `save_preference` | escritura (HITL) | clarify, direct, documental, mixed, out_of_scope, planning, structured | Store ("users", id, "preferences") | Guardar una preferencia del usuario para próximas conversaciones. Requiere aprobación humana antes de ejecutarse. |
| 18 | `forget_memory` | escritura (HITL) | clarify, direct, documental, mixed, out_of_scope, planning, structured | Store del usuario | Olvidar las preferencias y el perfil guardados del usuario. Requiere aprobación humana antes de ejecutarse. |
| 19 | `export_conversation` | escritura (HITL) | clarify, direct, documental, mixed, out_of_scope, planning, structured | hilo del checkpointer | Exportar la conversación actual en Markdown. Requiere aprobación humana antes de ejecutarse. |
| 20 | `request_human_contact` | escritura (HITL) | clarify, direct, documental, mixed, out_of_scope, planning, structured | $MANUELITA_STATE_DIR/contacts.jsonl | Registrar una solicitud para que una persona de Manuelita atienda un tema, con el canal preferido del usuario. Requiere aprobación humana antes de ejecutarse. |
| 21 | `get_plant_state` | lectura (MCP) | planning | data/synthetic/planificacion/<v>/state.json + plant_cana.json | Estado SINTÉTICO de la planta de caña: caña disponible y calidad, capacidades, equipos, inventarios y mezcla actual. Solo para planificación (datos de demostración). |
| 22 | `get_commitments` | lectura (MCP) | planning | data/synthetic/planificacion/<v>/commitments.json | Compromisos SINTÉTICOS de la semana (azúcar, etanol y energía) con cantidad mínima, prioridad y contraparte genérica. Solo para planificación. |
| 23 | `search_operating_procedures` | lectura (MCP) | planning | data/synthetic/planificacion/<v>/procedures/*.md (BM25 en memoria) | Busca en los procedimientos operativos SINTÉTICOS de la planta (prioridades, vapor, molienda, aprobación de planes) y devuelve fragmentos citables [S#]. |
| 24 | `simulate_production_scenario` | lectura (solo backend) | planning | simulador lineal (agent/planning.py) | Simula un reparto fijo de la caña entre azúcar y etanol: balances de azúcar, etanol, vapor y energía, margen y restricciones incumplidas. Datos sintéticos; cifras en código. |
| 25 | `optimize_production_plan` | lectura (solo backend) | planning | scipy.optimize.linprog (HiGHS) sobre agent/planning.py | Optimiza el programa de producción de la semana (programación lineal): plan de máximo margen, restricción que limita, alternativas y plan_id. Datos sintéticos; cifras en código. |
| 26 | `save_production_proposal` | escritura (HITL) | clarify, direct, documental, mixed, out_of_scope, planning, structured | $MANUELITA_STATE_DIR/planning/proposals.jsonl | Guardar la propuesta de programación de producción calculada en esta conversación para revisión del equipo de planta. Requiere aprobación humana antes de ejecutarse. |

## Esquemas de argumentos

### 1. `search_documents`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `query` | string | sí | Consulta en español. |
| `section` | string o null | no | Tema para filtrar (payload topic_id). |

### 2. `query_structured`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `query` | string o null | no | Texto libre a buscar. |
| `subject` | string o null | no | Empresa o filial (nombre o alias). |
| `attribute` | string o null | no | Atributo: año, capacidad, porcentaje… |
| `entity_type` | string o null | no | Lista y cuenta entidades de ese tipo (conteo exacto). |
| `limit` | integer | no | Máximo de hechos a devolver. |

### 3. `aggregate_series`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `metric` | string | sí | Métrica: ventas_consolidadas, ebitda, utilidad_neta, patrimonio, cana_molida, azucar, bioetanol_carburante, biodiesel, aceite_palma, camaron, mejillon o inversion_social. |
| `op` | list · sum · avg · max · min · change | no | list (valores), sum, avg (promedio), max, min o change (variación). |
| `year_from` | integer o null | no | Año inicial. |
| `year_to` | integer o null | no | Año final. |

### 4. `list_indicators`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `business` | string o null | no | Negocio o plataforma para filtrar (p. ej. «caña», «palma», «acuicultura», «Grupo Manuelita»). Vacío: todas las métricas. |

### 5. `compare_indicator`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `metric` | string | sí | Métrica del CSV (p. ej. ventas_consolidadas, ebitda, azucar, cana_molida). |
| `year_a` | integer | sí | Año base de la comparación. |
| `year_b` | integer | sí | Año a comparar con el año base. |

### 6. `sustainability_lookup`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `theme` | agua · carbono · energia · residuos · biodiversidad · social | sí | Eje: agua, carbono, energia, residuos, biodiversidad o social. |
| `query` | string o null | no | Pregunta concreta dentro del eje (opcional). |
| `top_k` | integer | no | Máximo de fragmentos. |

### 7. `list_business_units`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `country` | string o null | no | País para filtrar (Colombia, Perú, Chile…). Vacío: todas. |

### 8. `list_company_entities`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `kind` | certification · brand | sí | certification (certificaciones) o brand (marcas). |

### 9. `get_official_channels`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `purpose` | general · empleo · proveedores · clientes · prensa | no | general, empleo, proveedores, clientes o prensa. |

### 10. `faq_lookup`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `question` | string | sí | Pregunta del usuario. |
| `top_k` | integer | no | Máximo de preguntas frecuentes. |

### 11. `summarize_topic`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `topic_id` | catalogos · certificaciones · clientes · empleo · finanzas · fundacion · general · identidad · noticias · precios · productos · rankings · redes · sedes · sostenibilidad · youtube | sí | Tema del oro (data/gold/topics). |

### 12. `latest_news`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `limit` | integer | no | Número de noticias. |
| `since_year` | integer o null | no | Solo noticias publicadas desde este año. |

### 13. `get_fragment`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `unit_id` | string | sí | Identificador de la unidad de oro. |

### 14. `calculate`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `expression` | string o null | no | Expresión aritmética con números, + - * / ( ) y %. «15%» es 0,15; la coma es separador decimal y, con coma, el punto es de miles (1.250,5). |
| `operation` | string o null | no | percent_change (de values[0] a values[1]), ratio (values[0]/values[1]) o sum. |
| `values` | array o null | no | Valores para operation. |

### 15. `get_my_profile`

Sin argumentos.

### 16. `save_profile`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `name` | string o null | no | Nombre del usuario. |
| `workplace` | string o null | no | Dónde trabaja. |
| `role` | string o null | no | Cargo u ocupación. |
| `city` | string o null | no | Ciudad donde vive. |

### 17. `save_preference`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `key` | response_format · topics_of_interest · language · audience | sí | response_format, topics_of_interest, language o audience (perfil). |
| `value` | string | sí | Valor de la preferencia. |

### 18. `forget_memory`

Sin argumentos.

### 19. `export_conversation`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `format` | string | no |  |

### 20. `request_human_contact`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `topic` | string | sí | Tema de la solicitud. |
| `preferred_channel` | whatsapp · email · llamada | sí | Canal preferido: whatsapp, email o llamada. |
| `name` | string o null | no | Nombre para el contacto. |

### 21. `get_plant_state`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `plant_id` | string | no | Planta: cana. |

### 22. `get_commitments`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `plant_id` | string | no | Planta: cana. |
| `product` | string o null | no | Filtra por producto: sugar, ethanol o power. |

### 23. `search_operating_procedures`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `query` | string | sí | Qué restricción o regla buscar. |

### 24. `simulate_production_scenario`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `plant_id` | string | no |  |
| `cane_available` | number o null | no | t de caña disponibles. |
| `cane_delta_pct` | number o null | no | Cambio % de la caña (−15 = 15 % menos). |
| `cane_quality` | number o null | no | Pol % de la caña. |
| `steam_limit` | number o null | no | Límite de vapor (t). |
| `sugar_share` | number | sí | Fracción de la caña a azúcar (0 a 1). |

### 25. `optimize_production_plan`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `plant_id` | string | no |  |
| `cane_available` | number o null | no | t de caña disponibles. |
| `cane_delta_pct` | number o null | no | Cambio % de la caña (−15 = 15 % menos). |
| `cane_quality` | number o null | no | Pol % de la caña. |
| `steam_limit` | number o null | no | Límite de vapor (t). |
| `prioritize` | margin · power | no | margin (máximo margen) o power (máxima energía). |

### 26. `save_production_proposal`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|:-:|---|
| `plan_id` | string | sí | plan_id del último plan calculado. |
| `note` | string o null | no | Nota opcional para el equipo. |
