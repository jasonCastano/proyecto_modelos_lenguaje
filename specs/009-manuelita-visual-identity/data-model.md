# Fase 1 — Modelo de datos: identidad visual Manuelita

**Feature**: `009-manuelita-visual-identity`
**Fecha**: 2026-10-30

## 1. Paleta

### 1.1 BrandPalette

Colores de marca tomados del logotipo público y colores derivados de superficie y texto.

| Campo | Hex | Origen | Uso |
|-------|-----|--------|-----|
| `forest` | `#387C2B` | Logotipo | Primario: cabecera, títulos, bordes de acento |
| `orange` | `#E86D1F` | Logotipo | Acento: acciones, subrayados, badges de demo |
| `lime` | `#B0BC22` | Logotipo | Apoyo: indicadores secundarios |
| `yellow` | `#FFD200` | Logotipo | Apoyo: destacados puntuales |
| `orange_light` | `#F6A01A` | Logotipo | Apoyo: hover y detalles |
| `white` | `#FFFFFF` | Logotipo | Fondo base |
| `surface` | `#F5F7F3` | Derivado | Fondo de tarjetas y panel |
| `ink` | `#14240F` | Derivado | Texto principal |
| `ink_muted` | `#3F4A3C` | Derivado | Metadatos y texto secundario |
| `success` | `#2F7D32` | Derivado | Estado listo |
| `warning` | `#A05F00` | Derivado | Estado de revisión |
| `info` | `#1D5C8A` | Derivado | Estado sin evidencia |
| `danger` | `#B3261E` | Derivado | Estado de error |

**Validación**: todo hex MUST cumplir `^#[0-9A-F]{6}$` en mayúsculas.

### 1.2 Pares de contraste obligatorios

| Texto | Fondo | Mínimo |
|-------|-------|--------|
| `ink` | `white` | 4.5 |
| `ink` | `surface` | 4.5 |
| `ink_muted` | `white` | 4.5 |
| `ink_muted` | `surface` | 4.5 |
| `white` | `forest` | 4.5 |
| `white` | `danger` | 4.5 |
| `white` | `info` | 4.5 |
| `white` | `warning` | 4.5 |
| `forest` | `surface` | 3.0 |
| `orange` | `white` | 3.0 |

**Invariante**: `contrast_ratio(texto, fondo) >= mínimo` para cada par declarado; si un par no cumple, el
token debe ajustarse antes de publicar la interfaz.

## 2. Tokens

### 2.1 BrandTokens

| Campo | Tipo | Notas |
|-------|------|-------|
| `palette` | `BrandPalette` | Ver 1.1 |
| `contrast_pairs` | lista de `(texto, fondo, mínimo)` | Ver 1.2 |
| `type_scale` | mapa | `display` 28, `heading` 22, `body` 16, `caption` 13 (px) |
| `font_stack` | texto | Pila del sistema, sin descargas |
| `radius` | entero | 12 px para tarjetas, 8 px para badges |
| `spacing_unit` | entero | 8 px |
| `brand_name` | texto | «Grupo Manuelita» |
| `project_name` | texto | «RAG Ingenio Manuelita» |
| `tagline` | texto | Lema institucional corto |
| `attribution` | texto | Atribución de la marca a su titular |
| `affiliation_note` | texto | Aviso de proyecto académico no afiliado |

## 3. Estados

### 3.1 StatusVariant

| Campo | Tipo | Notas |
|-------|------|-------|
| `key` | texto | `ok`, `ready`, `review`, `fallback`, `missing_evidence`, `error`, `demo` |
| `color` | texto | Nombre del token de color |
| `icon` | texto | Símbolo legible (`✓`, `!`, `i`, `×`, `●`) |
| `label` | texto | Etiqueta en español |

### 3.2 Mapeo de estados

| Estado funcional | Variante visual | Color | Etiqueta |
|------------------|-----------------|-------|----------|
| `ok` (Q&A/Resumen) | `ok` | success | Correcta |
| `ready` (FAQ) | `ready` | success | Lista |
| `review` | `review` | warning | Revisar |
| `fallback` | `fallback` | info | Sin evidencia |
| `missing_evidence` | `fallback` | info | Sin evidencia |
| `error` | `error` | danger | Error |
| modo demostración | `demo` | orange | Modo demo |

**Invariantes**:

- Toda variante tiene `label` e `icon` no vacíos: el color nunca es el único canal.
- El mapeo conserva la semántica de la especificación 008 (no se renombran estados funcionales).

## 4. Componentes

### 4.1 SourceCard

| Campo | Tipo | Notas |
|-------|------|-------|
| `label` | texto | `U1`, `U2`, … |
| `title` | texto | Título del documento |
| `location` | texto | Sección, página o marca temporal |
| `url` | texto | Enlace verificable |
| `authority` | texto | `first_party`, `open_data`, `third_party` |

**Validación**: `url` no vacía; si falta `location`, la tarjeta escribe «sin sección declarada» en lugar de
dejar el campo vacío.

### 4.2 PageChrome

| Campo | Tipo | Notas |
|-------|------|-------|
| `project_name` | texto | Título de la página |
| `brand_line` | texto | Firma «Grupo Manuelita · Ingenio Manuelita» |
| `status_items` | lista | Datos, modelo, modo demo; cada uno con icono y etiqueta |
| `footer` | texto | Atribución + aviso de no afiliación |

## 5. Relaciones

```text
BrandTokens ──► BrandPalette
BrandTokens ──► StatusVariant (por clave)
StatusVariant ──► StatusBadge (render)
Citation ──► SourceCard (render)
PageChrome ──► cabecera + pie
```

## 6. Validaciones transversales

1. No hay URLs ni rutas absolutas en tokens ni en el CSS.
2. El CSS se inyecta una sola vez por sesión.
3. Ningún texto visible usa solo color para comunicar significado.
4. Los nombres propios («Manuelita», «MEGA 2030») se conservan literalmente.
5. La identidad no altera datos, citas ni resultados de las tareas.
6. Todo recurso visual es local (sin `<img>` remoto ni `@font-face` externo).
