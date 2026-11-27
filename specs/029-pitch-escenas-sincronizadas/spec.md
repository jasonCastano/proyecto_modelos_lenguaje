# Feature Specification: Pitch v2 con escenas sincronizadas a la narración

**Feature Branch**: `029-pitch-escenas-sincronizadas`
**Created**: 2026-11-26
**Status**: Draft
**Input**: User description: "genera las especificaciones para estos cambios: video/pitch/cambios.md"

## Contexto

La spec 028 dejó publicado el video pitch de Valer-IA:

- 57 s, vertical 1080×1920;
- 6 escenas de 9,5 s, una por bloque del guion;
- cada escena es un solo plano de la presentadora en el cañaduzal.

Al verlo, el integrante pidió cambios escena por escena en `video/pitch/cambios.md` (2026-11-26). El objetivo es que
**lo que se ve acompañe lo que se dice**: cuando la narración nombra algo (el trapiche, los informes, los
visitantes, los perfiles), eso aparece en pantalla en ese momento.

Esta versión 2 cambia tres cosas de la 028:

1. **Imágenes sincronizadas**: aparecen personajes, iconos y escenarios nuevos justo cuando la narración los nombra.
2. **Duración por escena**: cada escena dura lo que dure su narración, no 9,5 s fijos. El tiempo que sobra queda
   para las escenas que lo necesitan, siempre dentro de 60 s.
3. **Texto en pantalla**: los pasos «1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación» se reemplazan por una
   vista rápida de los perfiles del agente.

Todo lo demás de la 028 se mantiene:

- dónde y cómo se muestra el video en la web;
- la declaración de IA junto al video;
- sin logotipos ni marca Manuelita;
- solo afirmaciones con fuente;
- generación por la API con registro y tope de gasto.

## Clarifications

### Session 2026-11-26

- Q: ¿Se sube el tope de gasto o se ajusta la versión 2 a lo que queda? → A: Se mantiene el tope total de 20 USD.
  Van 5,44 USD (versión 1), así que la versión 2, con regeneraciones, debe caber en 14,56 USD.
- Q: ¿Los iconos de la escena 02 y la vista de perfiles de la escena 05 los genera el modelo o se agregan en el
  montaje? → A: Se dibujan como gráficos animados en el montaje, sincronizados con la palabra. El modelo no los
  genera.
- Q: MAGI-2 dejó de responder en la API de Higgsfield (403 `model_unavailable`). ¿Qué modelo se usa? → A: MAGI-2
  si vuelve a estar disponible; si no, **Kling 4.0** como segunda opción (1080p), decidido por el integrante el
  2026-11-26. Todos los planos de la v2 usan el mismo modelo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver en pantalla lo que la narración nombra (Priority: P1)

Quien entra a la web ve el pitch. Cada vez que la narración nombra algo concreto, eso aparece en pantalla en ese
mismo momento:

- un trapiche;
- un tipo de información;
- un tipo de usuario;
- una capacidad del agente.

Así entiende el mensaje aunque vea el video sin sonido, que es como arranca.

**Why this priority**: es el motivo de todos los cambios pedidos. Si la imagen no sigue la narración, el video
sigue siendo una presentadora genérica y el pitch no se entiende sin audio.

**Independent Test**: reproducir el video sin sonido junto a su lista de momentos sincronizados. Para cada momento,
comprobar que el elemento aparece cuando la palabra se dice.

**Acceptance Scenarios**:

1. **Escena 01**:
   - **Given** la narración «Manuelita nació en 1864 como un trapiche para producir azúcar», **When** se oye,
     **Then** se ve un trapiche tradicional funcionando en un cañaduzal, sin la presentadora.
   - **Given** la narración llega a «Valer-IA», **When** se nombra, **Then** la presentadora sale del cañaduzal por la
     derecha, levanta la vista de la tablet y sonríe mientras la cámara se acerca despacio.
2. **Escena 02**, **Given** la narración nombra «informes», «noticias», «caña», «palma», «acuicultura» y «frutas»,
   **When** se dice cada palabra, **Then**:
   - aparece un icono que la representa;
   - ese icono entra en la tablet de la presentadora, que la mira pensativa;
   - ya no hay paneles flotantes.
3. **Escena 03**, **Given** la narración nombra «visitantes», «clientes», «proveedores», «colaboradores» y «equipo de
   planta», **When** se dice cada uno, **Then**:
   - entra caminando una persona que lo representa: los tres primeros desde la izquierda, los dos últimos desde la
     derecha;
   - cada una se ubica junto a la presentadora, que queda en el centro;
   - al final, ella gira la tablet hacia la cámara y hay un primer plano de su cara.
4. **Escena 04**, **Given** la narración «Cita cada fuente, calcula las cifras en código y te pide un sí antes de
   guardar algo», **When** se oye, **Then**:
   - la presentadora está en una oficina ejecutiva redactando un informe;
   - se ven, en orden y al decirse, tres momentos: citar una referencia, calcular una cifra y pedir confirmación
     antes de guardar;
   - al final la cámara sube a su cara y ella asiente.
5. **Escena 05**, **Given** la narración del uso, **When** se oye, **Then**:
   - en lugar de los pasos numerados aparece una vista rápida de los cinco perfiles del agente: Visitante, Cliente
     B2B, Proveedor, Colaborador y Planificador industrial;
   - los paneles flotantes junto a la presentadora son esos perfiles.
6. **Escena 06**, **Given** el llamado a la acción, **When** se oye, **Then** las cinco personas de la escena 03
   reaparecen a los lados y se despiden con la mano mientras la presentadora invita al espectador.

---

### User Story 2 - Un ritmo que sigue a la narración (Priority: P2)

Quien ve el video no espera en silencio entre escenas. Cuando la narración de una escena termina, el video pasa a la
siguiente. El tiempo ahorrado queda para escenas con más contenido, como la escena 03, que ahora tiene una frase
más larga.

**Why this priority**: con duraciones fijas, las escenas cortas dejan silencios y las largas no caben. La escena 03
ampliada no entra en 9,5 s.

**Independent Test**: medir en el video final, para cada escena, el silencio entre el fin de su narración y el inicio
de la siguiente, y la duración total.

**Acceptance Scenarios**:

1. **Given** una escena cuya narración dura N segundos, **When** se monta, **Then** la escena dura N segundos más una
   pausa breve, sin pasar de la duración del material visual disponible.
2. **Given** las seis escenas montadas, **When** se mide el video, **Then** dura 60 segundos o menos.
3. **Given** la escena 03 con la narración ampliada, **When** se monta, **Then** se oye completa, sin cortes ni
   aceleración de la voz.

---

### User Story 3 - Producir la versión 2 sin perder la 1 ni salirse del presupuesto (Priority: P3)

El integrante produce la versión 2 con el mismo flujo de la 028:

1. ver el costo antes de generar;
2. generar;
3. revisar cada plano;
4. montar y validar.

Hasta que la versión 2 esté aprobada, la web sigue mostrando la versión 1.

**Why this priority**: generar cuesta dinero real y tiempo de cola. Un error no debe dejar la web sin video ni gastar
de más.

**Independent Test**: correr la estimación de costo sin llamar a la API. Comprobar que refleja todos los planos
nuevos y que la web sigue sirviendo la versión 1 mientras haya planos sin aprobar.

**Acceptance Scenarios**:

1. **Given** el guion y los planos de la versión 2, **When** el integrante pide la estimación, **Then** ve:
   - cuántos planos se generan;
   - cuántos segundos suman;
   - cuánto cuestan;
   - cuánto queda del presupuesto.
2. **Given** un plano generado, **When** el integrante lo revisa, **Then** puede aprobarlo o descartarlo con los
   mismos criterios de la 028, más uno nuevo: el plano muestra lo que su momento sincronizado pide.
3. **Given** planos de la versión 2 sin aprobar, **When** se carga la web, **Then** se ve la versión 1 completa.

---

### Edge Cases

- **Plano que no se parece a la presentadora**: si un plano con varias personas cambia la cara de la presentadora,
  se descarta y se regenera; no se monta.
- **Texto o marcas en un plano**: si un plano generado trae letras, cifras, logotipos o letreros legibles, se
  descarta. Los nombres de perfiles e iconos que deban leerse se agregan en el montaje, no se piden al modelo.
- **Narración más larga que el material**: si la narración de una escena dura más que el material visual generado,
  el montaje lo señala y no estira ni congela la imagen sin aviso.
- **Total sobre 60 s**: si la suma de narraciones y pausas pasa de 60 s, la validación falla e indica qué escena
  recortar.
- **Presupuesto**: si el costo estimado supera lo que queda del tope, el comando no genera nada y lo informa.
- **Trapiche histórico**: la escena 01 muestra un trapiche tradicional genérico. No se presenta como la instalación
  real de Manuelita en 1864 ni como foto de archivo.
- **Personas representadas**: las cinco personas son figuras genéricas sintéticas. No representan a personas reales
  ni llevan uniformes, carnés o logotipos de Manuelita.
- **Movimiento reducido o video ausente**: el comportamiento de la 028 no cambia. Hay portada y transcripción, y el
  video no arranca solo.

## Requirements *(mandatory)*

### Functional Requirements

**Guion y narración**

- **FR-001**: La narración de la escena 03 MUST ampliarse a: «Valer-IA reúne esa información en un solo agente para
  visitantes, clientes, proveedores, colaboradores y el equipo de planta; así, los aliados ahorran tiempo, toman
  decisiones con mayor confianza y evitan depender de información desactualizada o sin respaldo.»
- **FR-002**: Las narraciones de las escenas 01, 02, 04, 05 y 06 MUST mantenerse como en la versión 1.1.0 del guion.
- **FR-003**: El guion MUST subir de versión, y el texto cambiado MUST invalidar la revisión de la escena 03.
- **FR-004**: El texto en pantalla «1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación» MUST eliminarse. En su
  lugar, la escena 05 MUST mostrar una vista rápida de los cinco perfiles con los nombres que usa la web: Visitante,
  Cliente B2B, Proveedor, Colaborador y Planificador industrial.

**Sincronización**

- **FR-005**: Cada escena MUST declarar sus **momentos sincronizados**: la palabra o frase de la narración y lo que
  debe verse cuando se dice.
- **FR-006**: Cada elemento sincronizado MUST aparecer en pantalla a no más de 0,5 s del momento en que se dice su
  palabra.
- **FR-007**: Los momentos sincronizados de las seis escenas MUST ser los de `video/pitch/cambios.md`, resumidos en
  la User Story 1:
  - escena 01: trapiche, luego la entrada de la presentadora al nombrar a Valer-IA;
  - escena 02: seis iconos que entran a la tablet;
  - escena 03: cinco personas que entran por los lados;
  - escena 04: oficina, con citar, calcular y confirmar;
  - escena 05: vista de perfiles;
  - escena 06: despedida de las cinco personas.
- **FR-008**: Una escena MAY componerse de varios planos generados para cumplir sus momentos sincronizados, como el
  trapiche y luego la presentadora en la escena 01.

**Ritmo y duración**

- **FR-009**: Cada escena MUST durar lo que dura su narración más una pausa de 0,3 a 0,8 s antes de la siguiente.
- **FR-010**: El video completo MUST durar 60 segundos o menos.
- **FR-011**: La narración de cada escena MUST oírse completa, sin cortes y sin cambiar su velocidad para que quepa.

**Contenido visual y marca**

- **FR-012**: La presentadora MUST verse como en la versión 1 en todos los planos donde aparece: misma cara, ropa y
  tablet.
- **FR-013**: Las cinco personas de las escenas 03 y 06 MUST ser las mismas en ambas escenas y MUST representar su
  perfil por su vestimenta y accesorios, sin texto. Por ejemplo:
  - visitante: con cámara o mochila;
  - cliente: de traje;
  - proveedor: con caja o carpeta;
  - colaborador: con camisa de trabajo;
  - equipo de planta: con casco y chaleco.
- **FR-014**: La oficina de la escena 04 MUST ser una oficina ejecutiva genérica. MUST NOT presentarse como la oficina
  de la presidencia de Manuelita. MUST NOT llevar su nombre, logotipo ni letreros. Esto mantiene la FR-010 de la 028:
  la presentadora no es empleada, vocera ni representante de Manuelita.
- **FR-015**: Los iconos de la escena 02 MUST representar sin palabras cada término: informes, noticias, caña,
  palma, acuicultura y frutas. MUST ser gráficos animados del montaje: cada uno entra al decirse su palabra y se
  desplaza hasta la tablet de la presentadora. El plano generado solo muestra a la presentadora mirando la tablet.
- **FR-015a**: La vista de perfiles de la escena 05 MUST ser un gráfico animado del montaje, con los cinco nombres
  legibles y su icono, ubicado como paneles junto a la presentadora. El plano generado no incluye paneles.
- **FR-016**: Ningún plano generado MUST contener texto, cifras, logotipos o letreros legibles. El único texto
  legible del video MUST ser el que se agrega en el montaje: los nombres de los perfiles y los subtítulos.
- **FR-017**: Las afirmaciones sobre Manuelita MUST seguir saliendo del corpus con su fuente, como en la 028. La
  ampliación de la escena 03 describe beneficios de Valer-IA y no afirma hechos de Manuelita.

**Producción y presupuesto**

- **FR-018**: Antes de generar, el comando MUST mostrar cuántos planos se generan, sus segundos, su costo y lo que
  queda del tope. MUST pedir confirmación, como en la 028.
- **FR-019**: El gasto total en la API MUST quedarse en 20 USD o menos, sumando la versión 1 y la versión 2. Con
  5,44 USD ya gastados, la versión 2, regeneraciones incluidas, MUST costar 14,56 USD o menos. Si la estimación no
  cabe, MUST reducirse el número o la duración de los planos antes de generar.
- **FR-020**: Cada plano MUST quedar registrado con su indicación, semilla, trabajo, costo y revisión, como cada
  escena en la 028, y MUST poder regenerarse solo.
- **FR-021**: Cada plano MUST pasar la revisión humana de la 028 (parecido, sin texto, sin marca, coherente con el
  guion), más un criterio nuevo: muestra lo que pide su momento sincronizado.
- **FR-022**: La web MUST seguir mostrando la versión 1 hasta que la versión 2 esté completa, aprobada y validada. Al
  reemplazarla, la versión 1 MUST quedar recuperable en el historial del repositorio.

### Key Entities

- **Escena**: un bloque del guion con su narración. Ahora tiene una duración variable, que sale de su narración, y
  se compone de uno o más planos.
- **Plano**: un clip generado con su indicación, semilla, costo y revisión. Pertenece a una escena y cubre un tramo
  de su narración.
- **Momento sincronizado**: una palabra o frase de la narración, el instante en que se dice y lo que debe verse
  entonces (un personaje, un icono, un escenario o un texto del montaje).
- **Elemento del montaje**: texto o gráfico que se agrega sobre el video y no lo genera el modelo, como los nombres
  de los perfiles. Tiene su instante de entrada y de salida.
- **Aliado**: una de las cinco personas que representan los perfiles. Aparece en las escenas 03 y 06 con la misma
  apariencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El video de la versión 2 dura 60 s o menos y ninguna narración se corta.
- **SC-002**: Al menos el 90 % de los momentos sincronizados declarados aparecen en pantalla a 0,5 s o menos de su
  palabra (revisión cuadro a cuadro), y ninguno aparece antes de que su palabra empiece a decirse.
- **SC-003**: Ningún silencio entre escenas dura más de 0,8 s.
- **SC-004**: El 0 % de los planos aprobados contiene texto legible generado, logotipos o letreros de Manuelita.
- **SC-005**: Una persona que ve el video **sin sonido** puede nombrar, solo con la imagen, al menos 4 de los 5
  perfiles de la plataforma.
- **SC-006**: La presentadora es reconocible como la misma en el 100 % de los planos aprobados donde aparece.
- **SC-007**: El gasto real de la versión 2 queda dentro del tope acordado y se registra por plano.
- **SC-008**: Mientras la versión 2 no esté aprobada, el 100 % de las cargas de la web muestra la versión 1 completa.

## Assumptions

- **Base**: se reutilizan la imagen de referencia, la ficha, el flujo de generación por Higgsfield, el registro y la
  publicación web de la spec 028. Esta spec cambia el guion, la composición de escenas y el montaje, no la web.
- **Formato**: se mantiene vertical 1080×1920 (la línea «Formato» de `cambios.md` quedó vacía).
- **Voz, subtítulos, sonido y portada**: sin cambios, porque `cambios.md` no pide nada en esas líneas. La portada se
  regenera del nuevo primer cuadro.
- **Gramática**: la frase añadida a la escena 03 se ajustó levemente («así, los aliados…») sin cambiar su sentido.
- **Oficina**: el integrante pidió «una oficina de CEO de Ingenio Manuelita». Se interpreta como una oficina
  ejecutiva genérica por la FR-010 de la 028 y la regla de marca de la constitución.
- **Trapiche**: es una representación genérica de un trapiche tradicional. El dato de 1864 ya tiene fuente en el
  corpus.
- **Planos estimados**: de 12 a 15 planos de 4 a 10 s. A 0,08 USD por segundo, eso es de 8 a 12 USD sin
  regeneraciones, dentro de los 14,56 USD disponibles. Como los iconos y los perfiles van en el montaje, las escenas
  02 y 05 no necesitan planos extra. La cifra exacta sale del plan.
- **Gráficos del montaje**: los iconos y la vista de perfiles son gráficos propios del proyecto, con los colores de
  la web y sin elementos de la marca Manuelita. No cuestan generación.
- **Gobierno**: cambiar la duración por escena y la composición en planos actualiza el ADR 0032 o crea uno nuevo, y
  enmienda la constitución si cambia la regla del video. Ambos los aprueba jasonCastano.
