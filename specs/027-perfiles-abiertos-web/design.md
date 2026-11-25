# Design: elegir perfil sin candados (frontend-design)

Este documento extiende el sistema visual de la spec 026 (`specs/026-plataforma-web-manuelita/design.md`) y no
crea uno nuevo. Cambian tres cosas: el selector del agente, la fila del planificador en la entrada y la llegada a la
consola. El resto queda igual.

## Brief

- **Sujeto**: la mesa de atención de un ingenio azucarero. Cinco públicos llegan con preguntas distintas (público
  general, compradores industriales, cañeros, trabajadores y el equipo de planta) y cada uno escoge con quién habla.
- **Audiencia**: personas que abren la app por primera vez (docente, propietario del repositorio, invitados de la
  jornada) sin saber qué significa cada perfil.
- **Tarea principal**: elegir el perfil adecuado en menos de 30 s y saber siempre cuál está activo.

## Tokens (reutilizados, ninguno nuevo)

| Rol | Token | Uso aquí |
|---|---|---|
| Caña | `--cane` #387C2B | borde de la opción elegida, glifo de visitante y proveedor |
| Raíl | `--cane-deep` #173512 | texto del nombre del perfil activo |
| Azúcar | `--sugar` #FFD200 | glifo del cliente B2B |
| Melaza | `--molasses` #F6A01A | glifo del colaborador |
| Energía | `--power` #B0BC22 | glifo del planificador |
| Etanol | `--ethanol` #E86D1F | solo el foco del teclado (`--focus`), como en toda la app |
| Tinta | `--ink`, `--ink-muted` | nombre y línea «para quién» |

Tipografía: Archivo variable, con el ancho como señal de rol (spec 026):

- Nombre del perfil: `wdth 100`, peso 650.
- Línea «para quién»: `wdth 100`, peso 400, `--ink-muted`.
- Ejemplo de pregunta: `wdth 80` (el ancho de datos), en cursiva no. Se distingue por la comilla «» y el color de
  tinta.

## Layout

### Selector del agente (≥ 720 px)

Es un libro de registro horizontal: cinco columnas iguales, separadas por filetes `--rule` y sin cajas con sombra.
La opción elegida se marca con un filete superior de 3 px del color de su producto y el fondo `--surface`. Las
demás quedan sobre `--field`.

```text
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ ▲ Visitante  │ ◆ Cliente B2B│ ▲ Proveedor  │ ● Colaborador│ ⚡ Planificador│  ← nombre
│ Conoces a    │ Compras para │ Entregas caña│ Trabajas en  │ Repartes la  │  ← para quién
│ Manuelita    │ tu empresa   │ al ingenio   │ Manuelita    │ caña de la   │
│              │              │              │              │ semana       │
└──────────────┴──────────────┴──────────────┴──────────────┴══════════════┘
                                                               ▲ filete energía = activo
Te atiende como Planificador industrial · Datos sintéticos, no la operación real. [Abrir la planificación]
  └ ProfileNotice: una sola línea; el enlace es acción secundaria (action--quiet)
```

- El ejemplo de pregunta aparece debajo del selector, dentro de `ProfileSuggestions`, que ya existe. Las
  sugerencias cambian con el perfil, así que no se repiten dentro de cada columna. Así cada columna sostiene una
  sola idea: para quién es.
- Las cinco columnas son elegibles. No hay opacidad reducida, `disabled`, candado ni `title` con explicaciones.

### Selector del agente (< 720 px)

Una lista vertical con las mismas filas: glifo, nombre y «para quién» en una línea que se corta con elipsis. Ocupa
como máximo 5 × 48 px. El área táctil es de 48 px de alto. No hay desplazamiento horizontal.

### Entrada (`ProfileLedger`)

Se conserva tal cual. La fila del planificador deja de mostrar «Solo equipo de planta autorizado» y presenta, como
las otras, su botón de consulta de ejemplo. `PlatformHero` dice siempre «Abrir la planificación».

### Consola (`/planificacion`)

Ya no hay pantalla de acceso. Al llegar por dirección, la consola fija el perfil activo en planificador y muestra
la advertencia de datos sintéticos que ya tiene en su cabecera.

## Copy

| Perfil | Para quién es (`forWhom`) |
|---|---|
| Visitante | Quieres conocer Manuelita |
| Cliente B2B | Compras para tu empresa |
| Proveedor cañero | Entregas caña al ingenio |
| Colaborador | Trabajas en Manuelita |
| Planificador industrial | Planeas la producción de la semana |

Otros textos:

- **Aviso del perfil activo**: «Te atiende como {perfil}.» Para el planificador se añade: «Los datos de planta
  son sintéticos, no la operación real de Manuelita.» y la acción «Abrir la planificación».
- **Se retiran**:
  - «Solo equipo de planta autorizado».
  - «(solo autorizados)».
  - «La planificación es solo para el equipo de planta autorizado…».
  - «Hablar con el agente en otro perfil».
- **Reglas de redacción**: frases en voz activa, en segunda persona y en minúscula de oración. Sin mayúsculas
  sostenidas ni flechas en los botones.

## Principios

1. **Elegir es de la persona**: nada en la interfaz sugiere que un perfil sea «mejor» o restringido. Las cinco
   opciones pesan lo mismo.
2. **Una idea por opción**: el «para quién» decide y el ejemplo confirma. Las capacidades detalladas viven en la
   entrada.
3. **El color es el producto**: el filete del perfil activo usa el color del producto de su glifo. No se añaden
   colores.
4. **Sin movimiento nuevo**: el cambio de perfil solo mueve el filete, sin animación (se respeta
   `prefers-reduced-motion`, que ya está en los tokens).

## Revisión contra el brief

- **Primer borrador**: tarjetas con icono grande, título y tres viñetas. Es el kit SaaS de tarjetas iguales que la
  spec 026 evitó, y ocupa media pantalla antes del chat. **Cambio**: columnas de registro con una sola línea.
- **Segundo borrador**: rótulo en mayúsculas «ELIGE TU PERFIL» sobre el selector. Es una etiqueta innecesaria,
  porque el título de área «Habla con Valer-IA» ya da el contexto y el `aria-label` del grupo nombra el control.
  **Cambio**: sin rótulo.
- **Accesorio retirado**: un distintivo «Nuevo» en el planificador. No informa nada a quien llega por primera
  vez.

## Calidad mínima

- Grupo `role="radiogroup"` con flechas, Inicio y Fin. Todas las opciones son navegables (hoy se saltan las
  deshabilitadas).
- Foco visible con `--focus`.
- Contraste AA verificado con axe-core.
- Sin desplazamiento horizontal de 360 a 1920 px.
