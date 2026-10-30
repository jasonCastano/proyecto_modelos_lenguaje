# Alcance del Q&A — Módulo 1

**Versión**: 1.1
**Fecha**: 2026-10-30
**Estado**: **Aprobado y vigente.** G1 cerrada; M1-01 completada. Las 40 preguntas y las cuatro fronteras están aprobadas.
**Autores**: Jason Alejandro Castaño, Roberto José Guerrero
**Fuentes de verdad**: `CONSTITUTION.md`, `config/coverage-items.toml`, `data/gold/`

> **Registro de aprobación**: el alcance fue aprobado el 2026-10-30 por Jason Alejandro Castaño. La
> revisión cruzada de Roberto José Guerrero queda como seguimiento de gobernanza y no bloquea el cierre
> operativo de M1-01.

---

## 1. Qué significa "alcance" en este proyecto

El alcance es el **contrato explícito** entre lo que el asistente promete hacer y lo que no. No es solo
una lista de preguntas: define cuatro fronteras.

| Frontera | Pregunta que responde | Este documento |
|----------|-----------------------|----------------|
| **Temática** | ¿De qué se puede preguntar? | 40 preguntas en 8 categorías, mapeadas a los 24 ítems |
| **Documental** | ¿Con qué fuentes se responde? | 557 artefactos activos, 404 documentos de plata, 3.810 fragmentos, 15.211 unidades de oro |
| **Conductual** | ¿Cómo debe responder? | Siempre con cita; si no hay evidencia, lo declara; no inventa |
| **Negativa** | ¿Qué queda fuera? | Instagram, Linktree, PDF escaneados o cifrados, datos privados, asesoría financiera o legal |

Sin alcance no se puede evaluar: no hay forma de distinguir una respuesta correcta de una inventada, ni
de saber si el sistema falló o simplemente se le preguntó algo que nunca prometió responder.

---

## 2. Dentro y fuera de alcance

### Dentro de alcance

- Información pública de Ingenio Manuelita y sus empresas, marcas y fundación.
- Hechos, cifras, certificaciones, productos, sostenibilidad, historia y gobierno corporativo.
- Preguntas de un cliente primerizo, de un cliente industrial, de un proveedor y de un empleado potencial.
- Comparaciones y síntesis **solo** con evidencia publicada y citas verificables.
- Respuestas que declaren vacíos: "la documentación disponible no permite confirmarlo".

### Fuera de alcance

- Contenido privado, autenticado o pago.
- Instagram y Linktree: bloqueados por `robots.txt`.
- PDF escaneados, cifrados o sin texto: no se aplica OCR ni descifrado.
- Asesoría financiera, legal, médica o de inversión.
- Predicciones, opiniones o recomendaciones no publicadas por la empresa.
- Afirmaciones sobre vigencia de certificaciones que la fuente no permita confirmar.
- Cálculos o promedios propios sobre cifras contradictorias: el conflicto se muestra, no se resuelve por promedio.

---

## 3. Criterios de una pregunta válida

Cada pregunta del banco cumple estos requisitos:

1. **Tiene ID único** (`P01`–`P40`).
2. **Pertenece a una categoría** de las ocho definidas.
3. **Se mapea a uno o más de los 24 ítems** de cobertura.
4. **Declara una fuente esperada**: página oficial, informe, noticia o canal.
5. **Declara el resultado esperado**: respuesta directa, parcial, comparación, síntesis, meta-respuesta o fallback.
6. **Es evaluable**: se puede marcar como correcta, parcial, incorrecta o "sin evidencia".
7. **No depende de datos privados** ni de fuentes bloqueadas para ser respondida.

### Tipos de pregunta

| Código | Tipo | Qué exige |
|--------|------|-----------|
| `F` | Factual | Un dato explícito y citable |
| `C` | Comparativa | Dos o más elementos con criterios explícitos |
| `A` | Aplicada | Un escenario de negocio (bebidas, proveedor, cliente industrial) |
| `M` | Meta-evidencia | Evaluar la fuente, la vigencia o la comparabilidad |
| `S` | Síntesis | Integrar varias fuentes en un borrador con citas y vacíos |

### Resultados esperados

| Código | Resultado | Criterio |
|--------|-----------|----------|
| `D` | Directa | Responde con cita y sin inventar |
| `P` | Parcial | Responde parte y declara lo que falta |
| `C` | Comparativa | Compara con criterios y cita cada lado |
| `M` | Meta | Explica qué permite y qué no permite la evidencia |
| `S` | Síntesis | Borrador con citas, estructura y sección de vacíos |
| `X` | Fallback | Debe decir "no hay evidencia suficiente" |

---

## 4. Categorías y distribución

| # | Categoría | Preguntas | Total |
|---|-----------|-----------|------:|
| 1 | Identidad, historia y valores | P01–P05, P36, P37 | 7 |
| 2 | Sedes, contacto y proveedores | P06, P32 | 2 |
| 3 | Productos, aplicaciones y compras | P07–P10, P21–P24, P38 | 9 |
| 4 | Certificaciones y calidad | P11, P29, P30 | 3 |
| 5 | Sostenibilidad, ambiente y economía circular | P19, P25–P28, P39 | 6 |
| 6 | Noticias y presencia digital | P12–P15 | 4 |
| 7 | Empleo y comunidad | P16, P33, P35 | 3 |
| 8 | Datos duros, ética y transparencia | P17, P18, P20, P31, P34, P40 | 6 |
| | **Total** | | **40** |

---

## 5. Banco de preguntas

### 5.1 Identidad, historia y valores

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P01 | ¿Cuál es la misión y la visión de Manuelita? | F | I-01 | Sitio oficial / informe de gestión | D | Aprobada |
| P02 | ¿Qué valores y propósito guían a la empresa? | F | I-02 | Sitio oficial / informe | D | Aprobada |
| P03 | ¿Cuándo y cómo se fundó Manuelita y cuáles son sus hitos? | F | I-03 | Historia oficial | D | Aprobada |
| P04 | ¿Quiénes son el fundador, los dueños y la junta directiva? | F | I-04 | Gobierno corporativo | D | Aprobada |
| P05 | ¿Quién es el gerente y cómo se compone el equipo directivo? | F | I-05 | Sitio oficial / informes | D | Aprobada |
| P36 | ¿Cuáles son los valores corporativos de Manuelita y cómo los explica la organización? | F | I-02 | Código de ética / informe | D | Aprobada |
| P37 | ¿Cómo ha evolucionado Manuelita desde su origen en Palmira y cuáles son los principales hitos documentados de su historia? | F | I-03, I-06 | Historia oficial | D | Aprobada |

### 5.2 Sedes, contacto y proveedores

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P06 | ¿Dónde tiene sedes, plantas y cultivos, y cómo se contacta? | F | I-06 | Sitio oficial / contacto | D | Aprobada |
| P32 | Tengo una empresa en Palmira y quiero ser proveedor: ¿qué canales y orientaciones oficiales puedo consultar? | A | I-06 | `manuelita.com/proveedores-cana`, `manuelita.com/contacto` | P | Aprobada |

### 5.3 Productos, aplicaciones y compras

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P07 | ¿Qué productos y servicios ofrece Manuelita? | F | O-01 | Portafolio oficial | D | Aprobada |
| P08 | ¿Qué fichas técnicas o especificaciones tienen sus productos? | F | O-02 | Fichas técnicas | P | Aprobada |
| P09 | ¿Maneja Manuelita precios, tarifas o planes públicos? ¿Dónde están los catálogos? | F | O-03, O-04 | Listas de precios / catálogos PDF | P | Aprobada |
| P10 | ¿Quiénes son sus clientes, aliados o casos de éxito? | F | O-05 | Sitio oficial / noticias | P | Aprobada |
| P21 | ¿Qué tipos de azúcar ofrece Manuelita y cuáles son sus principales diferencias según la información publicada? | C | O-01, O-02 | `manuelita-productos/azucar-industrial`, informes | C | Aprobada |
| P22 | Tengo una empresa de bebidas: ¿qué productos de Manuelita tienen aplicaciones documentadas para este sector? | A | O-01, O-02, O-05 | Azúcar industrial / informes / noticias | P | Aprobada |
| P23 | ¿Qué presentaciones y características publica Manuelita para sus productos de azúcar industrial? | F | O-01, O-02 | Azúcar industrial / informe 2015 | P | Aprobada |
| P24 | ¿Qué son BIORGANIK y BIOFERT-K y qué usos agrícolas describe la empresa para cada uno? | F | O-01, O-02 | Informes 2017-2018 y 2023-2024 | D | Aprobada |
| P38 | Soy un potencial cliente industrial: ¿puedes comparar dos tipos de azúcar e identificar las certificaciones publicadas que corresponden a cada producto y unidad de negocio? | C | O-01, O-02, O-06 | Azúcar industrial / certificaciones / informes | C | Aprobada |

> Nota: en el informe en inglés aparece `BIOFERTI-K`; en los informes en español, `BIOFERT-K`. Son la misma
> línea de producto. La respuesta debe señalar la variante y no tratarlas como productos distintos.

### 5.4 Certificaciones y calidad

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P11 | ¿Qué certificaciones tiene Manuelita (ISO, BASC, INVIMA, RSPO)? | F | O-06 | `manuelita.com/certificaciones-y-politicas` | D | Aprobada |
| P29 | ¿Qué certificaciones publica Manuelita para la producción de azúcar en Palmira y cuál es el alcance de cada una? | C | O-06, I-06 | Certificaciones / informes | C | Aprobada |
| P30 | ¿La documentación disponible permite confirmar la vigencia de una certificación o solamente que fue reportada en un periodo determinado? | M | O-06, H-01 | Certificados / informes | M | Aprobada |

### 5.5 Sostenibilidad, ambiente y economía circular

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P19 | ¿Qué indicadores de sostenibilidad y programas sociales reporta? | F | H-03 | Informe de sostenibilidad | D | Aprobada |
| P25 | ¿Qué iniciativas de uso eficiente del agua ha reportado Manuelita Azúcar y Energía en el Valle del Cauca? | F | H-03, I-06 | Informes de sostenibilidad | P | Aprobada |
| P26 | ¿Cómo describe Manuelita el aprovechamiento de los subproductos de la caña dentro de su estrategia de economía circular? | F | H-03, O-01 | Informes / noticias | D | Aprobada |
| P27 | ¿Qué acciones y resultados publicados tiene Manuelita Azúcar y Energía relacionados con la reducción de emisiones? | F | H-03 | Informes / noticias | D | Aprobada |
| P28 | ¿Qué indicadores ambientales pueden compararse entre los informes de sostenibilidad disponibles y cuáles presentan diferencias de metodología o alcance? | C, M | H-03, H-01 | Informes 2019-2020 a 2023-2024 | M | Aprobada |
| P39 | ¿Qué iniciativas ambientales y sociales se han reportado específicamente para Manuelita Azúcar y Energía, diferenciándolas de las de otras empresas del grupo? | C | H-03, I-06, O-01 | Informes de sostenibilidad | C | Aprobada |

### 5.6 Noticias y presencia digital

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P12 | ¿Cuáles son las noticias y artículos más relevantes? | F | D-01, D-02 | Sala de prensa / blog | P | Aprobada |
| P13 | ¿Qué videos y transcripciones publica en YouTube? | F | D-03 | Canal oficial de YouTube | D | Aprobada |
| P14 | ¿Qué entrevistas del gerente están disponibles? | F | D-04 | YouTube / medios | X | Aprobada |
| P15 | ¿Qué publica Manuelita en redes sociales? | F | D-05 | Redes (bloqueadas) | P, X | Aprobada |

### 5.7 Empleo y comunidad

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P16 | ¿Qué vacantes de empleo publica y dónde? | F | D-06 | `manuelita.com/vacantes` | P | Aprobada |
| P33 | ¿Qué programas educativos y de emprendimiento ha reportado Manuelita para las comunidades cercanas a su operación en el Valle del Cauca? | F | H-03, I-06 | Fundación Manuelita / informes | D | Aprobada |
| P35 | ¿Dónde publica Manuelita sus oportunidades laborales y qué orientaciones ofrece para postularse? | F, A | D-06 | `manuelita.com/vacantes`, `manuelita.com/talento` | P | Aprobada |

### 5.8 Datos duros, ética y transparencia

| ID | Pregunta | Tipo | Ítems | Fuente esperada | Esperado | Estado |
|----|----------|------|-------|-----------------|----------|--------|
| P17 | ¿Dónde están los informes financieros y la memoria anual? | F | H-01 | Informes / Supersociedades | D | Aprobada |
| P18 | ¿Cuál es el NIT y el registro mercantil de la empresa? | F | H-02 | Cámara de Comercio / Supersociedades | D | Aprobada |
| P20 | ¿Qué precios públicos, datos abiertos y rankings sectoriales existen? | F | H-04, H-05, H-06 | SECOP / datos abiertos / rankings | P | Aprobada |
| P31 | ¿Qué fuentes oficiales respaldan la afirmación de que Manuelita aprovecha fuentes renovables para generar energía? | M | H-03, O-01, D-01 | Informes / noticias / historia oficial | M | Aprobada |
| P34 | ¿Dónde puedo consultar la información oficial sobre la línea ética y cómo acceder a ese canal? | F | I-02, I-05 | `manuelita.com/linea-etica`, `manuelita.com/codigoetica` | D | Aprobada |
| P40 | ¿Puedes preparar un borrador para un cliente sobre productos, calidad y sostenibilidad, citando fuentes oficiales y señalando qué información no está disponible públicamente? | S | O-01, O-06, H-03, H-01 | Síntesis de fuentes oficiales | S | Aprobada |

---

## 6. Matriz de cobertura de los 24 ítems

| Ítem | Nombre | Preguntas que lo cubren |
|------|--------|--------------------------|
| I-01 | Misión y visión | P01 |
| I-02 | Valores y propósito | P02, P34, P36 |
| I-03 | Historia | P03, P37 |
| I-04 | Fundador / dueño y junta | P04 |
| I-05 | Gerente y equipo directivo | P05, P34 |
| I-06 | Sedes y ubicaciones | P06, P29, P32, P33, P37, P39 |
| O-01 | Productos y servicios | P07, P21, P22, P23, P24, P26, P38, P39, P40 |
| O-02 | Fichas técnicas | P08, P21, P22, P23, P24, P38 |
| O-03 | Precios y planes | P09, P20 |
| O-04 | Catálogos PDF | P09 |
| O-05 | Casos de éxito y clientes | P10, P22 |
| O-06 | Certificaciones | P11, P29, P30, P38, P40 |
| D-01 | Noticias y sala de prensa | P12, P31 |
| D-02 | Blog y artículos | P12 |
| D-03 | Videos de YouTube | P13 |
| D-04 | Entrevistas del gerente | P14 |
| D-05 | Redes sociales | P15 |
| D-06 | Vacantes de empleo | P16, P35 |
| H-01 | Informes financieros | P17, P28, P30, P40 |
| H-02 | NIT y registro | P18 |
| H-03 | Indicadores de sostenibilidad | P19, P25, P26, P27, P28, P31, P33, P39, P40 |
| H-04 | Precios públicos y tarifas | P20 |
| H-05 | Datos abiertos | P20 |
| H-06 | Rankings sectoriales | P20 |

**Resultado**: 24/24 ítems tienen al menos una pregunta. Ningún ítem queda huérfano.

---

## 7. Preguntas con evidencia débil o bloqueada

Estas preguntas son válidas, pero el resultado esperado incluye un vacío declarado. No se deben "arreglar"
inventando respuestas.

| Pregunta | Situación | Comportamiento esperado |
|----------|-----------|-------------------------|
| P08 Fichas técnicas | Solo 3 unidades de oro en O-02 | Responder con lo publicado y declarar que no hay fichas completas |
| P09 Precios y catálogos | 20 unidades en O-03 y 6 en O-04 | Declarar que no hay lista de precios pública |
| P14 Entrevistas del gerente | 5 unidades en D-04 | Si no hay entrevista identificable, decir "no hay evidencia" |
| P15 Redes sociales | Instagram y Linktree bloqueados por `robots.txt` | Responder solo con lo capturado de canales accesibles |
| P20 Datos abiertos y rankings | 8 unidades en H-05 | Responder con rankings publicados y remitir a SECOP/datos abiertos |
| P28 Comparación de indicadores | Informes con metodologías y años distintos | No promediar; explicar diferencias de alcance |
| P30 Vigencia de certificaciones | La fuente reporta el periodo, no siempre la vigencia | Distinguir "reportada" de "vigente" |
| P39 Diferenciación por empresa | El grupo comparte reportes consolidados | No atribuir a una filial lo que es del grupo |
| P40 Borrador de síntesis | Requiere integrar varias fuentes | Incluir sección explícita de "no disponible" |

---

## 8. Protocolo de respuesta

Toda respuesta del asistente debe cumplir:

1. **Cita obligatoria**: URL, título y sección o página.
2. **Abstención explícita**: si no hay evidencia, decir "la documentación disponible no permite responder".
3. **Sin mezcla de empresas**: distinguir Manuelita, Manuelita Azúcar y Energía, Laredo, Aceites y Energía,
   Fundación Manuelita y demás filiales.
4. **Sin promedio de conflictos**: si hay cifras contradictorias, mostrar las dos y su fuente.
5. **Sin vigencia inferida**: si la fuente no lo dice, no afirmar que una certificación está vigente.
6. **Sin datos privados**: no completar con conocimiento externo ni con suposiciones.
7. **Idioma**: responder en el idioma de la pregunta, conservando nombres propios y siglas.

---

## 9. Cómo se evalúa este alcance

La evaluación del Módulo 1 (`docs/evaluacion_modulo1.md`) usará las 40 preguntas con esta estructura:

- **Conjunto núcleo**: P01–P20, cobertura amplia del negocio.
- **Conjunto extendido**: P21–P40, escenarios aplicados, comparaciones y meta-evidencia.
- **Comparación**: respuesta baseline zero-shot vs. respuesta final con contexto de oro.
- **Métricas por pregunta**: corrección (0/1/2), fuente citada (sí/no), coherencia (0/1/2), alucinación (sí/no),
  y resultado esperado cumplido (D/P/C/M/S/X).
- **Métricas agregadas**: exactitud, tasa de citas, tasa de alucinación, tasa de fallback correcto.
- **Reporte separado**: núcleo y extendido, para no ocultar que las preguntas difíciles bajan el promedio.

Las preguntas `X` no cuentan como fallo si el sistema declara correctamente que no hay evidencia. Contarlas
como error sería premiar la invención.

---

## 10. Aprobación G1

| Rol | Nombre | Decisión | Fecha |
|-----|--------|----------|-------|
| Aprobación del alcance | Jason Alejandro Castaño | 40 preguntas y cuatro fronteras aprobadas | 2026-10-30 |
| Revisión cruzada | Roberto José Guerrero | Seguimiento de gobernanza; no bloquea el cierre operativo | — |

**Constancia**: el alcance queda aprobado y vigente. M1-01 se cierra con esta aprobación. La revisión
cruzada de Roberto José Guerrero se mantiene como seguimiento documental del equipo y no condiciona el
cierre operativo de la tarea.

---

## 11. Control de cambios

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | 2026-10-30 | 20 preguntas iniciales aprobadas; 20 preguntas adicionales incorporadas; 8 categorías; matriz de 24 ítems |
| 1.1 | 2026-10-30 | Alcance y 40 preguntas aprobados; G1 cerrada; M1-01 completada |
