# Feature Specification: Video elevator pitch de Valer-IA generado con MAGI-2

**Feature Branch**: `028-video-pitch-magi2`

**Created**: 2026-11-25

**Status**: Draft (revisión 2026-11-26: generación por la API de Higgsfield)

**Input**: User description: "genera las especificaciones para usar el modelo de MAGI-2 de Sand.ai en este proyecto. Mi idea es usar la informacion de ingenio manuelita y crear un video generado que venda el producto de la plataforma web de Valer-IA. Usa la imagen de "D:\proyecto_modelos_lenguaje\docs\referencias\avatar_ingenio_manuelita.png" como referencia para el video y toda la informacion de Ingenio Manuelita. El video generado no debe exceder un minuto de duracion y debe tener el formato de un elevator pitch. Puedes usar este video como guia para el elevator pitch: https://www.youtube.com/watch?v=w0IX4mGw6Kk. El video se debe mostrar de primero cuando el cliente ingrese la aplicacion web y con el contenido del video conocer y saber como se debe usar a Valer-IA."

## Contexto

Valer-IA es la plataforma de agentes de Manuelita (idea 7). Hoy, quien entra a la web encuentra la entrada, los
cinco perfiles y la consola de planificación, pero no hay una pieza breve que le diga en segundos **qué es
Valer-IA, para quién es y cómo usarla**.

Se quiere un video corto con formato de **elevator pitch**, generado con el modelo abierto **MAGI-2 de Sand.ai**,
que venda la plataforma y enseñe a usarla:

- **Contenido**: la información pública de Ingenio Manuelita que ya está en el corpus del proyecto.
- **Presentadora**: una figura basada en la imagen de referencia `docs/referencias/avatar_ingenio_manuelita.png`,
  una mujer con chaqueta verde y tableta, en un cañaduzal con el ingenio al fondo.

Es lo primero que ve el cliente al entrar a la web.

MAGI-2 genera clips cortos con audio a partir de texto o de una imagen más texto. Un pitch de hasta un minuto se
compone, por tanto, de varias escenas que se generan, revisan y ensamblan **una vez**. La web sirve el video
terminado; no lo genera en cada visita.

**Revisión 2026-11-26**: las escenas se generan con MAGI-2 a través de la **API de Higgsfield**, que lo ofrece por
segundo generado. El integrante ya tiene la clave de la API en el archivo de entorno local. Esto reemplaza el
alquiler de una máquina con 8 GPU, que queda solo como alternativa documentada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entender Valer-IA en menos de un minuto al entrar (Priority: P1)

Un cliente abre la aplicación web por primera vez. Lo primero que aparece es el video del pitch, presentado por la
figura de referencia en un entorno de caña. En menos de un minuto le cuenta:

- qué problema resuelve Valer-IA;
- qué es Valer-IA y para quién es (los cinco perfiles);
- qué la distingue: cita sus fuentes, calcula las cifras en código y pide confirmación antes de guardar;
- cómo empezar a usarla.

Al terminar, el cliente sabe qué hacer a continuación.

**Why this priority**: es el pedido central: que el video se vea primero y que con él el cliente conozca y sepa usar
Valer-IA. Sin esto no hay entregable.

**Independent Test**: una persona que no conoce el proyecto ve el video al entrar y, sin ayuda, dice qué es
Valer-IA, elige un perfil y hace su primera pregunta.

**Acceptance Scenarios**:

1. **Given** un cliente que entra a la web, **When** carga la entrada, **Then** el video del pitch es el primer
   elemento que ve, antes de cualquier otro contenido.
2. **Given** el video en reproducción, **When** termina, **Then** dura 60 segundos o menos y la pantalla ofrece la
   acción de empezar a usar Valer-IA.
3. **Given** el video, **When** se revisa su guion, **Then** sigue la estructura de un elevator pitch: gancho,
   problema, solución, diferencia, cómo usarla y llamado a la acción.
4. **Given** el video, **When** se revisan sus afirmaciones sobre Manuelita, **Then** cada una proviene de la
   información pública del corpus y puede rastrearse a su fuente.

---

### User Story 2 - Ver o saltar el video sin estorbar la entrada (Priority: P2)

El cliente controla el video: puede ver los subtítulos, activar el sonido, pausar, volver a verlo o saltarlo e ir
directo a la plataforma. Si ya lo vio en la sesión, la entrada no lo vuelve a imponer, pero lo sigue ofreciendo.

**Why this priority**: un video que se impone y no se puede saltar ahuyenta a quien ya conoce la plataforma y choca
con las reglas de accesibilidad del proyecto.

**Independent Test**: en la entrada, saltar el video lleva al contenido en un paso. Al volver en la misma sesión, el
video aparece como opción para verlo de nuevo, no como bloqueo.

**Acceptance Scenarios**:

1. **Given** el video en la entrada, **When** el cliente elige saltarlo, **Then** llega al contenido de la entrada
   en un solo paso.
2. **Given** el video, **When** empieza, **Then** arranca sin sonido y con subtítulos visibles en español. El
   cliente puede activar el sonido.
3. **Given** un cliente con preferencia de movimiento reducido, **When** entra, **Then** el video no se reproduce
   solo: se muestra su portada con la opción de reproducirlo y la transcripción.
4. **Given** un cliente que ya vio o saltó el video en la sesión, **When** vuelve a la entrada, **Then** el video
   queda como una opción para verlo de nuevo.
5. **Given** que el video no carga (red lenta o archivo ausente), **When** el cliente entra, **Then** ve la portada
   y la transcripción, y la entrada funciona igual.

---

### User Story 3 - Producir el video de forma reproducible y honesta (Priority: P3)

El equipo produce el video con MAGI-2, por la API de Higgsfield, a partir de:

- un guion breve basado en el corpus de Manuelita;
- la imagen de referencia;
- una indicación por escena.

Un integrante lanza la generación desde su equipo con un comando del proyecto, escena por escena o todas a la vez.
El comando usa la clave del archivo de entorno, espera cada clip y lo guarda en el repositorio. Cada escena queda
registrada (indicación, imagen usada, duración, proveedor, modelo, identificador del trabajo y fecha) para poder
regenerarla o corregirla. El video declara que fue generado con inteligencia artificial y que el proyecto es
académico.

**Why this priority**: sin reproducibilidad ni declaración de IA, la pieza incumple la constitución (§10). Es
trabajo previo, pero no lo ve el cliente.

**Independent Test**: con el registro de producción, otra persona del equipo entiende cómo se generó cada escena y
puede volver a generarla.

**Acceptance Scenarios**:

1. **Given** el guion aprobado, **When** se genera el video, **Then** cada escena tiene registradas su indicación,
   la imagen de referencia, su duración, el proveedor, el modelo y el identificador del trabajo.
2. **Given** la clave de Higgsfield en el archivo de entorno, **When** el integrante genera una escena, **Then** el
   clip queda guardado y registrado como pendiente de revisión, y la clave no aparece en el repositorio, en los
   registros ni en la salida del comando.
3. **Given** que falta la clave o el saldo no alcanza, **When** se intenta generar, **Then** el comando se detiene
   con un mensaje claro antes de gastar créditos y no modifica las escenas ya aprobadas.
4. **Given** el video en la entrada, **When** se muestra, **Then** junto a él hay un texto visible que dice que es
   contenido generado con IA y que Valer-IA es un proyecto académico, no un canal oficial de Manuelita. El video no
   lleva ese rótulo grabado (revisión 2026-11-26).
5. **Given** el video, **When** se revisa la imagen, **Then** no aparece el logotipo ni piezas gráficas de la marca
   Manuelita, y la presentadora no se identifica como empleada ni vocera de Manuelita.

---

### Edge Cases

- **Escena que no cumple**: MAGI-2 genera una escena con texto ilegible, manos deformes, cifras inventadas en
  pantalla o una figura que no se parece a la referencia. Esa escena se descarta y se regenera; nunca se publica
  una escena sin revisión humana.
- **Pitch demasiado largo**: el guion supera 60 segundos al ensamblarse. Se recorta el guion, no se acelera el
  audio.
- **Interrupción**: el cliente cambia de área mientras el video corre. El video se detiene y no sigue sonando en
  otra página.
- **Teléfono**: el cliente entra desde un teléfono. El video se adapta al ancho, sin desplazamiento horizontal, y
  los subtítulos siguen legibles.
- **Clon nuevo**: alguien clona el repositorio. El video está disponible tras los pasos habituales de instalación,
  sin generarlo de nuevo.
- **Contenido desactualizado**: el video menciona algo de Valer-IA que luego cambia (por ejemplo, un perfil). El
  registro de producción permite regenerar solo la escena afectada.
- **Falla de la API**: Higgsfield rechaza el trabajo, se agota el tiempo de espera o la red se cae. La escena queda
  como pendiente con el error registrado; las demás no se pierden y se puede reintentar solo esa.
- **Una generación a la vez**: la API limita los trabajos simultáneos. Las escenas se generan en serie.
- **Gasto**: cada generación cuesta. Antes de lanzar, el comando muestra cuántos segundos va a generar y su costo
  estimado, y no regenera escenas ya aprobadas salvo que se pida.
- **Datos enviados a un tercero**: la imagen de referencia y las indicaciones se suben a Higgsfield. Solo se envían
  esas entradas, nunca datos del corpus fuera del guion, claves ni datos personales.

## Requirements *(mandatory)*

### Functional Requirements

**Contenido del pitch**

- **FR-001**: El video MUST durar 60 segundos o menos.
- **FR-002**: El video MUST seguir la estructura de un elevator pitch: gancho, problema, solución, diferencia, cómo
  usarla y llamado a la acción.
- **FR-003**: El video MUST explicar cómo se usa Valer-IA en pasos que el cliente pueda repetir: elegir un perfil,
  hacer una pregunta, revisar las fuentes citadas y, con el planificador, abrir la consola de planificación.
- **FR-004**: Las afirmaciones sobre Ingenio Manuelita MUST salir de la información pública del corpus del proyecto.
  Cada una MUST quedar trazada a su fuente en el guion. No MUST incluir cifras o hechos sin fuente.
- **FR-005**: Si el video menciona la planificación industrial, MUST decir que usa datos sintéticos de
  demostración.
- **FR-006**: La narración y los subtítulos MUST estar en español.

**Imagen y honestidad**

- **FR-007**: La presentadora del video MUST basarse en la imagen de referencia
  `docs/referencias/avatar_ingenio_manuelita.png`, con apariencia coherente entre escenas.
- **FR-008**: Antes de generar, el equipo MUST confirmar y registrar que la imagen de referencia es sintética o
  tiene derechos de uso, y que no representa a una persona real identificable.
- **FR-009**: La entrada MUST mostrar, como texto visible junto al video y en su transcripción, que es contenido
  generado con inteligencia artificial y que Valer-IA es un proyecto académico, no un canal oficial de Manuelita.
  El video MUST NOT llevar ese rótulo grabado, y su narración cierra con un llamado a la acción, no con la
  declaración (decisión del integrante, 2026-11-26).
- **FR-010**: El video MUST NOT mostrar el logotipo ni piezas gráficas de la marca Manuelita. Tampoco MUST
  presentar a la presentadora como empleada, vocera o representante de Manuelita.

**Producción**

- **FR-011**: El video MUST generarse con el modelo MAGI-2 de Sand.ai, escena por escena, a partir del guion y de
  la imagen de referencia. La vía principal MUST ser la API de Higgsfield; ejecutar los pesos abiertos en GPU
  propias o alquiladas queda como alternativa documentada.
- **FR-012**: Cada escena MUST quedar registrada con su indicación, la imagen de referencia, su duración, el
  proveedor, el modelo, el identificador del trabajo, la semilla si la API la acepta y la fecha. Ese registro MUST
  permitir regenerar una escena sola.
- **FR-025**: El proyecto MUST ofrecer un comando para generar escenas por la API: una escena o todas, en serie,
  esperando cada resultado y guardando el clip en el repositorio como pendiente de revisión.
- **FR-026**: La clave de la API MUST leerse solo del archivo de entorno local. MUST NOT escribirse en el
  repositorio, en el registro de escenas, en los registros ni en la salida del comando. Si falta, el comando MUST
  fallar con un mensaje que diga cómo configurarla.
- **FR-027**: Antes de generar, el comando MUST mostrar los segundos a generar y el costo estimado, y MUST ofrecer
  un modo de prueba que no llame a la API. No MUST regenerar escenas aprobadas salvo que se pida explícitamente.
- **FR-028**: La aplicación web y la integración continua MUST NOT llamar a la API de Higgsfield. Las pruebas MUST
  cubrir el comando sin red, con un cliente simulado.
- **FR-013**: Cada escena MUST pasar una revisión humana antes de entrar al montaje: parecido con la referencia,
  ausencia de texto ilegible o cifras inventadas en pantalla, y coherencia con el guion.
- **FR-014**: El video terminado MUST incluir subtítulos sincronizados y una transcripción en texto.

**Experiencia en la web**

- **FR-015**: Al entrar a la web, el video MUST ser el primer elemento visible de la entrada.
- **FR-016**: El video MUST iniciar sin sonido y con subtítulos. El cliente MUST poder activar el sonido, pausar,
  volver a ver y saltar el video.
- **FR-017**: Saltar el video MUST llevar al contenido de la entrada en un solo paso.
- **FR-018**: Tras verlo o saltarlo, el video MUST NOT volver a imponerse en la misma sesión. MUST seguir
  disponible como opción para verlo de nuevo.
- **FR-019**: Con preferencia de movimiento reducido, el video MUST NOT reproducirse solo. MUST mostrarse su
  portada con la opción de reproducirlo y la transcripción.
- **FR-020**: Si el video no carga, la entrada MUST seguir funcionando y mostrar la portada y la transcripción.
- **FR-021**: Al terminar el video, la entrada MUST ofrecer la acción de empezar a usar Valer-IA, que lleva al
  agente.
- **FR-022**: El video MUST verse completo de 360 a 1920 px de ancho, sin desplazamiento horizontal, con controles
  operables por teclado y contraste AA en los controles.
- **FR-023**: Quien clone el repositorio MUST obtener el video con los pasos habituales de instalación, sin tener
  que generarlo.

**Documentación**

- **FR-024**: El uso de MAGI-2 y de la API de Higgsfield, el guion, el registro de producción, los datos enviados al
  proveedor y la declaración de IA MUST documentarse en el proyecto: decisión de arquitectura, constitución y
  registro de prompts.

### Key Entities

- **Guion del pitch**: el texto narrado por bloques (gancho, problema, solución, diferencia, cómo usarla, llamado
  a la acción). Cada bloque tiene duración estimada y las fuentes del corpus que respaldan sus afirmaciones.
- **Escena**: un clip generado de unos 10 segundos. Tiene indicación, imagen de referencia, duración, proveedor,
  modelo, identificador del trabajo, fecha y estado (pendiente, generada, aprobada, descartada o con error).
- **Trabajo de generación**: una solicitud a la API de Higgsfield para una escena. Tiene identificador, estado,
  segundos pedidos, costo estimado y, si falla, el error.
- **Imagen de referencia**: la presentadora del pitch. Lleva su origen y sus derechos de uso registrados.
- **Video del pitch**: el montaje final de las escenas aprobadas, con subtítulos, transcripción y portada. La
  declaración de IA y de proyecto académico la muestra la web junto al video.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El video dura 60 segundos o menos (medido en el archivo final).
- **SC-002**: De 5 personas que no conocen el proyecto, al menos 4 describen qué es Valer-IA y hacen su primera
  pregunta en el agente después de ver solo el video, sin ayuda.
- **SC-003**: El 100 % de las afirmaciones sobre Manuelita del guion tienen fuente en el corpus, y el 0 % contiene
  cifras sin respaldo.
- **SC-004**: El video es lo primero visible al entrar, de 360 a 1920 px, y el contenido de la entrada aparece en un
  paso al saltarlo.
- **SC-005**: Con el video ausente o sin red, la entrada carga y funciona igual. Muestra la portada y la
  transcripción.
- **SC-006**: La declaración de IA y de proyecto académico es visible junto al video en el 100 % de las cargas de
  la entrada, incluido el modo compacto y la falla del video, y está en la transcripción.
- **SC-007**: El registro de producción permite regenerar cualquier escena. Una prueba lo comprueba regenerando una
  escena desde su registro.
- **SC-008**: Generar las 6 escenas por la API cuesta 20 USD o menos, incluidas las regeneraciones, y el costo real
  queda anotado en la decisión de arquitectura.
- **SC-009**: Una búsqueda de la clave en el repositorio, el registro de escenas y la salida del comando no la
  encuentra (0 apariciones).

## Assumptions

- **Modelo**: MAGI-2 de Sand.ai. Por la API de Higgsfield se usa la versión alojada, que según fuentes de noviembre
  de 2026 genera clips de 4 a 30 segundos en 1080p con audio, a unos 0,08 USD por segundo. Los pesos abiertos
  (MAGI-2 Preview, Apache 2.0, clips de 10 s) siguen como alternativa. El pitch se arma con 6 escenas de unos
  10 segundos, una por bloque del guion. El identificador exacto del modelo, la relación de aspecto vertical, el
  uso de la imagen como primer cuadro y la autenticación se confirmarán con la documentación oficial de
  Higgsfield durante el plan.
- **Dónde se genera**: en el equipo del integrante, con un comando que llama a la API de Higgsfield. La generación
  ocurre una vez, fuera de la aplicación web. La web solo sirve el video terminado; la aplicación no depende de
  MAGI-2 ni de Higgsfield para funcionar.
- **Clave y saldo**: el integrante ya tiene la clave en `HIGGSFIELD_API_KEY` dentro del archivo de entorno local y
  saldo en su cuenta. Si la API exige un identificador y un secreto separados, el plan define la segunda variable.
- **Proveedor**: subir la imagen de referencia y las indicaciones a Higgsfield es aceptable porque la imagen es
  sintética, el integrante tiene sus derechos y las indicaciones no contienen datos personales.
- **Video guía**: no se pudo revisar el contenido del video de YouTube indicado como guía. Se usa la estructura
  estándar de un elevator pitch (gancho, problema, solución, diferencia, uso y llamado a la acción). Si el video
  guía propone otra estructura, se ajusta en `/speckit-clarify`.
- **Imagen de referencia**: es una imagen generada con IA, el integrante tiene derechos de uso y no representa a una
  persona real ni contiene la marca Manuelita. Así quedó confirmado en su ficha el 2026-11-26 (FR-008). La presentadora del video es una figura distinta de
  la ilustración animada del chat (Valer-IA Caña); no la reemplaza.
- **Idioma y público**: español, para los cinco públicos de la plataforma. El pitch habla a todos; no hay un video
  por perfil.
- **Contenido de Manuelita**: solo información pública del corpus (oro), como en el resto del proyecto. No se usan
  materiales con derechos de terceros, como música o videos de Manuelita.
- **Audio**: se usa el audio que genera MAGI-2 o una narración en español sincronizada en el montaje, la que cumpla
  mejor la duración y la claridad. Siempre hay subtítulos.
- **Sesión**: «misma sesión» significa la misma pestaña o visita del navegador, como en las demás preferencias
  ligeras de la web.
- **Gobierno**: el cambio de la entrada y el uso de un modelo nuevo requieren una decisión de arquitectura y una
  enmienda de la constitución aprobada por el propietario del repositorio (jasonCastano).
