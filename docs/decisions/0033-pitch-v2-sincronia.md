# ADR 0033 — Pitch v2: planos sincronizados con la narración y modelo de respaldo

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-26
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0032 (video pitch con MAGI-2, fuera de línea), que esta decisión amplía;
  - ADR 0027 y spec 023 (dictado con faster-whisper);
  - `specs/029-pitch-escenas-sincronizadas/` (spec, plan, research, contratos, tareas);
  - `video/pitch/cambios.md` (pedido del integrante).

## Contexto

La v1 del pitch (spec 028) tiene seis escenas de 9,5 s, cada una un solo plano de la presentadora. Al verla, el
integrante pidió que **lo que se ve acompañe lo que se dice**:

- el trapiche cuando se nombra;
- los iconos de informes, noticias y plataformas, que entran a la tablet;
- las cinco personas de los perfiles, que llegan al nombrarse;
- una oficina para la escena de la diferencia;
- una vista de perfiles en lugar de los pasos numerados.

También pidió que cada escena dure lo que su narración y que la escena 03 tenga una frase más.

Además, el 2026-11-26 por la tarde, MAGI-2 dejó de responder en la API de Higgsfield. Los tres modos responden
`403 model_unavailable`, y el modelo salió del catálogo, aunque su página de documentación sigue publicada.

## Decisión

1. **Escenas por planos**:
   - una escena se compone de uno o más planos generados;
   - un plano puede partir de la referencia (`image`), conservar su identidad sin fijar el primer cuadro
     (`reference`), no usar imagen (`text`) o partir del último cuadro de otro plano aprobado (`frame:`), lo que
     mantiene iguales a las cinco personas entre las escenas 03 y 06;
   - el registro `escenas.json` pasa al esquema 2.
2. **Momentos sincronizados en el guion (1.2.0)**:
   - **Tiempos**: `pml pitch align` saca de la narración sintetizada los tiempos de cada palabra, con
     faster-whisper local, y los guarda en `sincronia.json`.
   - **Duración**: cada escena dura su narración más 0,5 s.
3. **Gráficos del montaje**:
   - los iconos y la vista de perfiles son SVG propios, rasterizados con Playwright y superpuestos por ffmpeg en el
     instante de su palabra;
   - no los genera el modelo, así que son exactos, legibles y gratis;
   - es el único texto legible del video, aparte de los subtítulos.
4. **Reajuste de planos**:
   - el revisor anota en qué segundo del clip ocurre cada evento (anclas);
   - el montaje reajusta cada tramo entre 0,8× y 1,25× para que el evento caiga sobre su palabra;
   - fuera de ese rango, se regenera.
5. **Modelo por preferencia**:
   - `config/pitch.toml` lista `models = ["magi2", "kling4"]`;
   - `pml pitch probe` comprueba sin costo cuál responde;
   - el primero disponible queda fijado en `escenas.json`, y todos los planos de la v2 usan el mismo;
   - Kling 4.0 (1080p, unos 0,19 USD/s) es la segunda opción, elegida por el integrante el 2026-11-26.
6. **Publicación sin perder la v1**:
   - el montaje va a `video/pitch/borrador/`;
   - `pml pitch publish` lo copia a la web solo con todos los planos aprobados y el chequeo en verde (pausas
     ≤ 0,8 s; ≥ 90 % de los momentos a ±0,5 s).

## Alternativas consideradas

- **Un plano por cada evento**:
  - ventaja: sincronía exacta;
  - en contra: de 14 a 20 planos más y movimiento cortado.
- **Pedir al modelo los iconos y los paneles**: tiempos aproximados, letras falsas y más costo. Se descartó en la
  aclaración Q2.
- **Narración por frases cortadas en cada palabra clave**: se escucha entrecortada.
- **Alineación forzada con otra herramienta (aeneas, MFA)**: dependencia nueva y pesada; faster-whisper ya está en
  el proyecto.
- **Otros modelos de Higgsfield**:

| Modelo | Por qué no |
|---|---|
| Seedance 2.0 y 2.5 | Fuera de presupuesto en 1080p |
| Kling 4.0 Flash, MiniMax | 720p o menos |
| Wan 3.0 Prime | Viable, pero algo más caro |

- **Esperar a MAGI-2**: sin fecha de regreso.

## Consecuencias

- El costo estimado de la v2 (57 s en 8 planos) es de 4,56 USD con MAGI-2 o unos 10,83 USD con Kling 4.0, dentro
  del tope total de 20 USD (van 5,44 USD de la v1). **Costo real: 11,02 USD con Kling 4.0**, sin regeneraciones;
  el total del pitch quedó en 16,46 USD.
- En `plano-03a`, Kling hizo llegar a las cinco personas en otro orden y más rápido que la narración. Se
  sincronizan la primera y la última llegada (anclas), y las demás se miden con su instante real (`events`).
  El reajuste mínimo bajó de 0,8× a 0,7×, y la colaboradora (−0,9 s) y el proveedor (+1,1 s) quedaron como
  desfases aceptados por el integrante: 21 de 23 momentos están a ±0,5 s.
- La revisión admite `start_s` para saltar el inicio de un clip; se usó con los paneles que trae la imagen de
  origen en 02 y 05.
- Si el modelo fijado es Kling 4.0:
  - la constitución (§3.7 y §10, que nombran MAGI-2) se enmienda en el mismo commit;
  - Kling no admite semilla: la regeneración no es idéntica, aunque la indicación, el trabajo y el clip quedan
    registrados;
  - Kling no documenta audio: el fondo de campo queda en silencio y la narración es la de Phonon.
- La revisión humana de cada plano ahora incluye `cue_shown` y las anclas.
- La web no cambia de código: recibe el nuevo video, los subtítulos, la portada y `pitch.ts` al publicar.
