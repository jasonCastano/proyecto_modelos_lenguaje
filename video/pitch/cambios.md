# Cambios pedidos al video pitch

> **Aplicado** en la spec 029 (guion 1.2.0, 2026-11-26): ver `specs/029-pitch-escenas-sincronizadas/` y el ADR 0033.

## Cambio del 2026-11-27: sepia de 1864 y barrido de época (plano-01a)

- **Pedido por**: Roberto José Guerrero (2026-11-27).
- **Pedido**: mientras el narrador dice «Manuelita nació en 1864 como un trapiche para producir azúcar», el
  trapiche en blanco y negro alusivo a 1864, con un efecto de cambio de época que recorra la pantalla de derecha
  a izquierda justo antes de que salga Valer-IA. El integrante eligió **sepia suave**.
- **Aplicado** (montaje, sin regenerar planos; costo en Higgsfield: **0 USD**):
  - `escenas.json`, `plano-01a.look = {style: "sepia-suave", sweep_s: 0.5}`;
  - `pml pitch assemble` aplica sepia con grano, viñeta y un parpadeo leve, y en los últimos 0,5 s del plano
    una línea de luz cruza de derecha a izquierda y devuelve el color.
- **Tiempos en el video**: sepia de 0,0 a 3,9 s (la frase termina en 4,1 s), barrido de 3,9 a 4,4 s y Valer-IA
  entra en color a los 4,4 s.
- **Comprobación**: `pml pitch validate` y `pml pitch check` en verde (52,12 s, 1080×1920, 18,75 MB).
- **Estado**: aprobado por el integrante y publicado en la web con `pml pitch publish` (2026-11-27).

## Cambio del 2026-11-27: sonido con la primera interacción (web)

- **Pedido**: que el audio del video se active al entrar por primera vez a la página.
- **Límite**: los navegadores no dejan sonar un video antes de que la persona interactúe con la página; si se
  intenta, detienen el video.
- **Decisión del integrante (opción A)**: el video sigue arrancando sin sonido y con subtítulos; con el primer
  clic, toque o tecla en cualquier parte de la página se activa el sonido y el video vuelve al inicio, una sola
  vez. No cuentan los controles del video, el botón de sonido ni «Saltar el video».
- **Aplicado** en `web/src/components/home/PitchVideo.tsx`, con sus pruebas en `PitchVideo.test.tsx` y el
  contrato `specs/028-video-pitch-magi2/contracts/web-ui.md`. Costo: 0 USD.

---

Escribe aquí lo que quieres cambiar del video (`web/public/media/pitch-valeria.mp4`). Cuando termines, avísale
a Claude con un mensaje como «aplica los cambios de `video/pitch/cambios.md`».

## Cómo llenarlo

- Ubica la parte por **escena** o por **segundo** del video (tabla de abajo). Cada escena dura 9,5 s.
- En cada escena, escribe solo en las líneas que empiezan con `Cambio:`. Deja vacío lo que no cambia.
- Puedes escribir en español y con tus palabras: «que no salgan los paneles flotantes», «que diga X en vez de Y»,
  «que camine más lento», «quita el texto de los pasos», etc.
- Si el cambio es general (voz, ritmo, subtítulos, portada, música, duración), escríbelo en **Cambios generales**.

### Qué cuesta cada tipo de cambio

| Tipo de cambio | Qué se rehace | Costo en Higgsfield |
|---|---|---|
| Texto narrado, subtítulos, texto en pantalla, orden, recortes | Narración (Phonon) y montaje | 0 USD |
| Imagen de una escena (acción, cámara, fondo, objetos, ropa) | Esa escena con MAGI-2 | 0,80 USD por escena (unos 15 min) |
| Imagen de todas las escenas | Las 6 escenas | 4,80 USD (tope total: 20 USD; van 5,44) |

Antes de gastar, Claude mostrará el `--dry-run` con el costo y esperará tu confirmación.

---

## Escena 01 · gancho · 0,0–9,5 s

- **Narración actual**: «Manuelita nació en 1864 como un trapiche para producir azúcar. Valer-IA te ayuda a
  conocerla con un agente que cita fuentes.»
- **Imagen actual**: de pie en el cañaduzal, levanta la vista de la tablet y sonríe; la cámara se acerca despacio.
- Cambio en la narración:
- Cambio en la imagen: Antes de mostras a Valeri-IA, mientras el narrador habla, añade el trapiche tradiconal funcinando para la produccion de azucar, el trapiche que este ubicado en un cañaduzal. Has que el video este sincronizado con la narracion. Cuando el narrador menciones a Valer-IA has que salga del cañaduzal de la derecha, levanta la vista de la tablet y sonríe; la cámara se acerca despacio.

## Escena 02 · problema · 9,5–19,0 s

- **Narración actual**: «Su información pública está repartida en informes, noticias y páginas de cuatro
  plataformas: caña, palma, acuicultura y frutas.»
- **Imagen actual**: mira la tablet pensativa; a su alrededor flotan paneles translúcidos con gráficas e iconos.
- Cambio en la narración:
- Cambio en la imagen: Cuando el narrador mencione "informes", "noticias", "caña", "palma", "acuicultura" y "frutas", genera iconos representativos de cada una de esas palabras, y los reemplazas por los paneles flotantes, en su lugar esos iconos van ingresando a la tablet que sostiene Valeri-IA pensativa.

## Escena 03 · solucion · 19,0–28,5 s

- **Narración actual**: «Valer-IA reúne esa información en un solo agente para visitantes, clientes, proveedores,
  colaboradores y el equipo de planta.»
- **Imagen actual**: gira la tablet hacia la cámara (pantalla verde abstracta) y luego primer plano de su cara.
- Cambio en la narración: Valer-IA reúne esa información en un solo agente para visitantes, clientes, proveedores, colaboradores y el equipo de planta, así aliados ahorran tiempo, toman decisiones con mayor confianza y evitan depender de información desactualizada o sin respaldo.
- Cambio en la imagen: Cuando el narrador mencione "visitantes", "clientes", "proveedores", "colaboradores", y "equipo de planta", genera personas que representen cada una de esas palabras. Los "visitantes" "clientes", y "proveedores" entraran caminando desde el lado izquierdo de la pantalla, y los "colaboradores" y "equipo de planta" entraran caminando desde el lado derecho de la pantalla. A medida que van entrando cada uno se van ubicando al lado de Valer-IA, y con Valer-IA ubicada en el centro gira la tablet hacia la cámara (pantalla verde abstracta) y luego primer plano de su cara.

## Escena 04 · diferencia · 28,5–38,0 s

- **Narración actual**: «Cita cada fuente, calcula las cifras en código y te pide un sí antes de guardar algo.»
- **Imagen actual**: primer plano de las manos tocando la tablet; la cámara sube a su cara y asiente.
- Cambio en la narración:
- Cambio en la imagen: Cambia de escenario a Valer-IA, ahora esta en una oficina de CEO de Ingenio Manuelita. Y mientras el narrador esta hablando, Valer-IA esta redactando un informe donde representivamente "cite referencias", "calcula cifras" y "pide un sí antes de guardar algo"; la cámara sube a su cara y asiente.

## Escena 05 · uso · 38,0–47,5 s

- **Narración actual**: «Elige tu perfil, haz tu pregunta y revisa las fuentes. Si planificas producción, abre la
  consola con datos sintéticos.»
- **Texto en pantalla actual**: «1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación»
- **Imagen actual**: camina entre la caña con la tablet y explica con la mano; paneles flotantes a su lado.
- Cambio en la narración:
- Cambio en el texto en pantalla: No muestres esos numeros, en su lugar muestra una vista rapida de los perfiles del agente.
- Cambio en la imagen: Los paneles flotantes que sean la vista rapida de los perfiles de Valer-IA.

## Escena 06 · accion · 47,5–57,0 s

- **Narración actual**: «Conocer Manuelita ya no es buscar: es preguntar. Entra a Valer-IA, elige tu perfil y haz tu
  primera pregunta hoy.»
- **Imagen actual**: se detiene, invita con la mano y sonríe; la cámara se aleja a un plano general del campo.
- Cambio en la narración:
- Cambio en la imagen: De los lados salen los aliados de "visitantes", "clientes", "proveedores", "colaboradores", y "equipo de planta" despidiendose con una mano.

---

## Cambios generales

- Voz (tono, velocidad, otra voz):
- Subtítulos (tamaño, posición, quitar):
- Sonido de fondo (más o menos ambiente, música):
- Portada (imagen que se ve antes de reproducir):
- Otros: Cuando la narracion termine de hablar en cada escena se puede continuar a la siguiente, de esta forma se puede ahorrar segundos y usarlos para la siguiente escena si se requiere. Todo dentro del tiempo maximo de 60 segundos.
- Formato: Cambia las dimenciones del video por horizontal 16:9 (1920 × 1080)
