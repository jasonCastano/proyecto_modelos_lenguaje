# MEMORY — memoria curada de Valer-IA Caña

> Hechos estables y decisiones de operación. Sin datos de personas: la memoria de cada usuario vive en
> el Store del backend (seudónimo HMAC) y se audita con `agent memory list --user <seudónimo>`.
> La bitácora diaria está en `memory/YYYY-MM-DD.md` (la escribe el backend; no se versiona).

## Dominio (con fuente)

- Manuelita es un grupo agroindustrial diversificado en alimentos y energía renovable con presencia en
  varios países de las Américas (Informe de Sostenibilidad 2023-2024, p. 12).
- Plataformas: caña de azúcar (Colombia y Perú), palma de aceite (Meta y Casanare), frutas y hortalizas
  (Perú) y acuicultura (Chile) (Informe de Sostenibilidad 2023-2024, pp. 8 y 42).
- Las cifras anuales salen de `data/curated/series_anuales.csv` (74 cifras con página y URL); los
  informes son anuales, no trimestrales.

## Operación

- Valer-IA responde por el puente `valeria-bridge` → backend FastAPI (router, memoria, 20 herramientas
  de atención y 6 de planificación, citas, notas de voz en español e inglés). Si el backend no responde
  en 90 s, responde el agente nativo de OpenClaw con `valeria-tools`
  (solo lectura) en **modo degradado**: debe avisarlo y no prometer acciones de escritura.
- Toda escritura (perfil, preferencias, olvido, exportación, solicitud de contacto) se confirma con las
  palabras de la persona («dale», «mejor no») y vence a los 10 minutos. Nadie necesita comandos.
- Canal: SIM dedicada a Valer-IA (spec 028); nunca grupos (`groupPolicy: disabled`). Modo cerrado
  (números de prueba) y modo abierto a cualquier número solo en el ensayo y la sustentación.

## Aprendizajes

- Los saludos y agradecimientos no necesitan búsqueda (enrutador: ruta `direct`).
- Las preguntas de cifras van a `aggregate_series`/`compare_indicator`, no a búsqueda documental.
