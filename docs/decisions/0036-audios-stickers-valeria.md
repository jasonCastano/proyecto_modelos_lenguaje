# ADR 0036 — Audios de los stickers con la voz del agente

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-27
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0020 (voz del agente con Phonon, spec 016);
  - ADR 0034 (imágenes de perfil y stickers de Valer-IA);
  - `specs/030-imagenes-perfil-valeria/` (US6, research R12 y R13).

## Contexto

Los stickers de Valer-IA (ADR 0034) son WebP animados y WhatsApp no admite sonido en ese formato. El integrante
pidió un audio por sticker con la frase dicha por la voz de Valer-IA, de 5 s como máximo, guardado en
`docs/whatsapp/stickers/audios/`. Así se puede mandar el sticker seguido de su nota de voz, o unir los dos en un
video para crear un sticker con sonido en WhatsApp.

La voz del agente (Phonon, `gradium/phonon-40m-es`, voz «Rebeca») ya está aprobada en §2, pero solo para leer las
respuestas del chat. Llevarla a material de difusión es un uso nuevo. Además, la regla de §10 para las imágenes
de perfil prohíbe los modelos generativos, y la síntesis de voz es un modelo.

## Decisión

1. **La voz oficial y nada más**: los audios se sintetizan con `VoiceService` y la configuración de la spec 016,
   en el equipo, sin red (`HF_HUB_OFFLINE=1` con el modelo en la caché) y sin costo. No se clona ni se imita
   ninguna voz real.
2. **Acabado reproducible** (`scripts/whatsapp_images.py`):
   - se recorta el silencio de los extremos (−45 dBFS, 30 ms de margen);
   - se dejan 150 ms de silencio a cada lado;
   - se iguala el volumen (RMS de la voz a −20 dBFS, pico ≤ −1 dBFS).

   Si un audio pasa de 5 s se vuelve a sintetizar. Si sigue largo, no se aprueba: la frase nunca se corta.
3. **Formato**: OGG/Opus mono de 48 kHz a 32 kbit/s, la nota de voz de WhatsApp. Se codifica con PyAV, que ya es
   dependencia del proyecto (spec 023), así que no hay dependencias nuevas y las pruebas corren en el CI.
4. **Trazabilidad**: los pasos son los mismos que para las imágenes.
   - `render --piece audios` deja los borradores, que Git ignora.
   - `approve audio-<nombre> --by` publica el audio con su ficha:
     - texto exacto, sticker, voz y modelo;
     - licencia CC BY-NC 4.0 y atribución a Phonon;
     - formato, duración y niveles;
     - costo 0 y quién lo aprobó.
   - `check` lo verifica.
   - Los `.ogg` van por Git LFS.
5. **Gobierno**: la constitución 2.7.0 amplía la regla de §10 con los audios de los stickers.

## Alternativas descartadas

- **MP3 o M4A**: WhatsApp los muestra como archivo de audio, no como nota de voz.
- **WAV**: unas 20 veces más pesado y tampoco se muestra como nota de voz.
- **`ffmpeg` por `subprocess`**: está en el equipo del integrante pero no en el CI; PyAV hace lo mismo.
- **Otra voz del catálogo o un servicio de voz en línea**: rompería la identidad con el chat web; un servicio
  externo tendría costo y sacaría el texto del equipo.

## Consecuencias

- **Identidad:** el sticker suena con la misma voz del chat web.
- **Licencia:** la de las voces es CC BY-NC 4.0. Los audios solo pueden usarse en el contexto académico y no
  comercial del proyecto, con la atribución del README.
- **Producción:** producir de nuevo los audios necesita el modelo de voz en la caché (la primera vez, `HF_TOKEN` y
  las condiciones aceptadas en Hugging Face). Las pruebas usan un sintetizador falso y no lo necesitan.
- **Uso:** unir el audio a la animación y crear el sticker con sonido en WhatsApp queda fuera de esta decisión.
