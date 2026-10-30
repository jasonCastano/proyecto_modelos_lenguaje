# Verificación de canales oficiales

**Fecha de corte:** 2026-10-29
**Alcance:** YouTube, Instagram y Linktree oficiales de Manuelita, más la Fundación Manuelita
(enlazada desde el Linktree oficial).
**Campañas:** `2026-10-official-channels`, `2026-10-official-channels-2`,
`2026-10-official-channels-3`, `2026-10-youtube-backfill-1`,
`2026-10-youtube-asr-transcripts`, `2026-10-fundacion-manuelita`.

## 1. Método y política de acceso

Antes de cada captura el pipeline consulta `robots.txt` y aplica la política configurada en
`config/official_channels.toml` y `config/sources.toml`. No se usan cookies de sesión, credenciales
ni técnicas para evadir controles de acceso. Cada decisión queda registrada en la tabla
`policy_checks` del catálogo (`data/bronze/_meta/bronze.sqlite3`).

| Canal | `robots.txt` | Decisión | Artefactos |
|-------|--------------|----------|-----------:|
| YouTube | Permite las rutas públicas; limita frecuencia | Capturar metadatos y subtítulos, sin descargar audio/video | 111 |
| Instagram | `User-agent: *` → `Disallow: /`; aviso de Meta que prohíbe la recolección automatizada sin permiso | **No capturar** | 0 |
| Linktree | `User-agent: *` → `Disallow: /` | **No capturar** | 0 |
| Fundación Manuelita | `User-agent: *` → `Disallow:` (sin restricciones) | Capturar | 41 |

Instagram y Linktree quedan por fuera del corpus por decisión de cumplimiento, no por una falla
técnica. El pipeline las conserva como fuentes deshabilitadas de hecho: la campaña las descubre y
las marca como `robots_disallowed` en `outcomes`.

## 2. YouTube (`@ManuelitaAgroindustria`)

- Canal ID: `UCanNTjBY24t7fID3tj0WfTw`.
- Metadatos del canal: título, descripción, seguidores, enlaces y miniatura
  (`data/bronze/raw/youtube/2026-10-official-channels/`).
- Listado auditado: **69 videos y shorts** (pestañas Videos + Shorts).
- Metadatos por video: título, descripción, fecha, duración, canal, etiquetas y disponibilidad de
  transcripción.

### Resultado por video

| Situación | Videos | Tratamiento |
|-----------|-------:|-------------|
| Accesibles con subtítulos | 28 | VTT en español/inglés descargado con `yt-dlp` |
| Accesibles sin subtítulos | 5 | Transcripción local con `faster-whisper` (`small`, int8) |
| Accesibles, audio sin habla | 2 | Sin transcripción (`Vinaza Seca Manuelita`, `Expovinos 2020`) |
| Duplicado exacto | 1 | `Manuelita Corporativo 2024` reutiliza la transcripción de `Manuelita, Institutional Video` |
| Requieren inicio de sesión | 3 | No capturados: `t4c3_rcoimI`, `8csShBos7dE`, `2cEntF9DHTA` |
| No disponibles | 30 | Enlaces privados, eliminados o restringidos por YouTube |
| **Total** | **69** | |

**Cobertura de transcripción:** 33 videos con texto (28 por subtítulos + 5 por ASR). Si se cuenta el
duplicado exacto como video independiente, la cobertura es 34 de 36 videos accesibles (94,4 %).

### Trazabilidad de las transcripciones ASR

- Script: `scripts/transcribe_youtube.py`.
- Modelo: `faster-whisper` `small`, `compute_type=int8`, VAD activo, idioma `es`.
- El audio se descarga a un directorio temporal y se elimina; solo se almacenan el VTT y un JSON de
  procedencia (`?transcript=asr` y `?transcript=asr&meta=1`).
- Se filtran alucinaciones típicas de Whisper (por ejemplo, «Subtítulos por la comunidad de
  Amara.org»). Un artefacto con ese texto fue retirado (`retraction_reason =
  asr_no_speech_hallucination`).

## 3. Instagram (`@manuelitaagroindustria`)

- Cuenta oficial verificada; el perfil público declara 899 publicaciones y cerca de 11 K seguidores.
- `https://www.instagram.com/robots.txt` contiene `User-agent: *` → `Disallow: /` y una nota de Meta:
  «Collection of data on Instagram through automated means is prohibited unless you have express
  written permission».
- Decisión: **no se capturan publicaciones, comentarios ni imágenes**. No hay artefactos de
  Instagram en el corpus.
- Consecuencia para el RAG: las preguntas sobre contenido exclusivo de Instagram (campañas,
  historias, publicaciones) quedan fuera de alcance y deben responderse indicando que la fuente no
  es accesible. Los mismos temas se cubren parcialmente con el sitio oficial y YouTube.

## 4. Linktree (`linktr.ee/manuelitaagroindustria`)

- `https://linktr.ee/robots.txt` contiene `User-agent: *` → `Disallow: /`.
- Decisión: **no se captura la página**. Se verificó manualmente el mapa público de enlaces para
  comprobar que no aporta contenido nuevo:

| Enlace del Linktree | Destino | Cobertura en bronce |
|---------------------|---------|---------------------|
| Portal Manuelita | `https://www.manuelita.com/` | Sí (`official_site`, 397 artefactos) |
| Sostenibilidad | `https://www.manuelita.com/sostenibilidad/` | Sí (`official_site`) |
| Únete a nuestro equipo | `https://www.manuelita.com/talento/` | Sí (`official_site`) |
| Fundación Manuelita | `https://fundacionmanuelita.org/` | Sí (`fundacion_manuelita`, 41 artefactos) |

El Linktree funciona como agregador: no contiene información propia distinta de estos cuatro
destinos. Por eso su exclusión no deja un vacío de contenido.

## 5. Fundación Manuelita

Sitio de primer nivel enlazado desde el Linktree oficial. `robots.txt` permite la captura y publica
un `sitemap_index.xml`.

- 57 objetivos descubiertos; 41 artefactos almacenados (40 HTML + 1 PDF).
- PDF principal: `InformedeGestion-FundacionManuelita2025.pdf` (19,2 MB).
- 16 fallos: enlaces `http://` que responden 522 y PDF históricos (2018-2020) con enlaces 404 en el
  propio sitio. El informe de gestión 2025 y el contenido HTML quedaron capturados.

## 6. Efecto en el corpus

| Fuente | Artefactos activos | Bytes |
|--------|-------------------:|------:|
| `official_site` | 397 | 262,9 MB |
| `youtube` | 111 | 1,4 MB |
| `fundacion_manuelita` | 41 | 21,3 MB |
| `elpais` | 4 | 3,4 MB |
| `datos_gov` | 2 | 1,3 MB |
| `asocana` | 1 | 31 KB |
| `camara_comercio` | 1 | 101 KB |
| **Total** | **557** | **290,5 MB** |

El catálogo completo conserva 26.905 artefactos no retirados; 26.347 están en cuarentena por
irrelevancia y no cuentan como corpus activo.

## 7. Verificación reproducible

```bash
# Estado de las fuentes y artefactos activos
uv run python scripts/verify_official_channels.py

# Integridad de las campañas de canales oficiales
uv run pml verify --campaign 2026-10-official-channels-3
uv run pml verify --campaign 2026-10-youtube-asr-transcripts
uv run pml verify --campaign 2026-10-fundacion-manuelita

# Reportes completos
# data/bronze/reports/2026-10-official-channels-3/
# data/bronze/reports/2026-10-fundacion-manuelita/
```

## 8. Vacíos declarados

1. **Instagram:** bloqueado por `robots.txt` y por los términos de recolección de Meta.
2. **Linktree:** bloqueado por `robots.txt`; sin contenido propio.
3. **YouTube:** 30 videos no disponibles y 3 que exigen sesión autenticada. No se usaron cookies
   personales.
4. **Audio sin habla:** 2 videos musicales no generan transcripción.
5. Los enlaces históricos de la Fundación (2018-2020) están rotos en el sitio de origen.

Estos vacíos se declaran en la app y en el informe del Módulo 1; no se rellenan con texto inventado.
