# ADR 0032 — Video pitch de la entrada generado con MAGI-2, fuera de línea

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-26
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0030 (plataforma web en cuatro áreas);
  - ADR 0020 y spec 016 (voz Phonon);
  - `specs/028-video-pitch-magi2/` (spec, plan, research, contratos, tareas);
  - `video/pitch/RUNBOOK.md`.

## Contexto

Quien entra a la web no tenía una pieza breve que le dijera qué es Valer-IA, para quién es y cómo usarla. El
integrante pidió un video de un minuto o menos, con formato de elevator pitch y generado con **MAGI-2** de Sand.ai.
El video debe:

- usar la imagen `docs/referencias/avatar_ingenio_manuelita.png` como referencia;
- usar la información de Ingenio Manuelita;
- mostrarse primero al entrar.

Según su ficha y su README, MAGI-2 Preview (Apache 2.0):

- genera clips de **10 s fijos**, verticales (1088×1920), a partir de texto o de imagen más texto, con audio
  ambiente;
- no documenta voz en español, sincronía de labios ni continuación entre clips;
- necesita **8 GPU Hopper** de clase 80 GB y unos 307 GB de pesos.

El equipo local tiene una RTX 3080 Ti de 16 GB.

## Decisión

1. **Producción fuera de línea y única**. MAGI-2 corre en una máquina alquilada de 8× H100/H200, con la imagen
   Docker oficial, siguiendo `video/pitch/RUNBOOK.md`. La aplicación y la CI nunca lo ejecutan. El repositorio
   guarda:
   - las entradas: guion, prompts, manifiesto y la imagen con su ficha de origen;
   - las salidas aprobadas, por Git LFS.
2. **Seis escenas I2V**, una por bloque del pitch: gancho, problema, solución, diferencia, uso y acción. Todas parten
   de la imagen de referencia como primer cuadro, se recortan a 9,5 s y suman 57 s. Cada escena guarda su prompt,
   semilla, versión del modelo y revisión humana con cuatro chequeos (`video/pitch/escenas.json`). Al montaje solo
   entran escenas aprobadas.
3. **Guion con fuentes**. `video/pitch/guion.toml` cita unidades del oro para cada afirmación de Manuelita.
   `pml pitch validate` rechaza cifras sin respaldo y exige «datos sintéticos» donde se menciona la planificación.
4. **Voz y rótulo en el montaje**:
   - la narración en español es la voz **Phonon** del proyecto, porque la presentadora no habla a cámara y así se
     evitan labios desincronizados;
   - ffmpeg mezcla la voz sobre el ambiente de MAGI-2 y graba el rótulo «Video generado con IA · Valer-IA es un
     proyecto académico, no un canal oficial de Manuelita»;
   - el montaje genera también los subtítulos WebVTT, la portada y la transcripción;
   - la tasa de bits se limita a 3 Mbps para que el archivo pese 25 MB o menos.
5. **Primer elemento de la entrada** (`PitchVideo`):
   - arranca sin sonido y con subtítulos;
   - se salta en un paso;
   - no se impone dos veces en la sesión;
   - respeta el movimiento reducido;
   - sin el video, muestra la portada y la transcripción;
   - las páginas ya se sirven sin caché (spec de `make app`).
6. **Ficha de la imagen**. La imagen es fotorrealista y la constitución prohíbe imitar a personas reales. Una ficha
   firmada por un integrante (`docs/referencias/avatar_ingenio_manuelita.md`) declara su origen, sus derechos y que
   no hay persona real ni marca. Sin ella no se valida ni se genera.

## Alternativas consideradas

- **Generar en la aplicación o bajo demanda**: imposible con el hardware disponible. Además, la entrada quedaría
  atada a una GPU o a un tercero.
- **Servicio alojado o Space de terceros**: la ficha dice que ningún proveedor de inferencia lo despliega. Subir la
  imagen y el guion a un tercero sin acuerdo es otro riesgo.
- **Video horizontal**: recorta a la presentadora y no es el modo nativo del modelo.
- **Alojar el video en YouTube**: depende de la red y de un tercero, y falla sin conexión en la sustentación.
- **Voz de MAGI-2 o grabar a una persona**: la voz en español no está documentada, y grabar introduce a una persona
  real.

## Consecuencias

- Hace falta alquilar unas 2 horas de 8× H100. Sin eso, la entrada muestra la portada y la transcripción, y todo lo
  demás funciona y se prueba.
- Las pruebas cubren toda la cadena sin GPU, con clips sintéticos de ffmpeg (`tests/integration/test_pitch_assemble.py`).
- Cambiar el texto de un bloque invalida su escena aprobada. El validador lo detecta y obliga a revisarla.
- Constitución **2.3.0** (§3.7 y §10).
