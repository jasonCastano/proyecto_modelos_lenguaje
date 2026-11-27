# Contrato de interfaz: frontend de Valer-IA (spec 031)

Lo que las pruebas (Vitest, e2e) y el gate de la skill pueden dar por cierto después del rediseño.

## Rutas (sin cambios)

| Ruta | Área |
|---|---|
| `/` | entrada |
| `/agente` | agente por perfil |
| `/planificacion` | consola de planificación |
| `/evidencia` | evidencia |

## Documento

- `<html lang="es" data-type="software" data-radius="soft" data-buttons="solid" data-motion="on">`.
- Metas: `page-type=software`, `site-kind=software`, `description`, `og:*`, `theme-color` `#14240f`.
- Enlace de salto al contenido como primer elemento enfocable.

## Entrada (`/`)

- `main > section` por cada sección de `research.md` R6, cada una con `id` y su h2 primero (el hero lleva el h1).
- Hero: `data-enter`; la línea de aviso dice que es un proyecto académico con IA y no un canal oficial de Manuelita;
  el visual es el video pitch (`PitchVideo`), saltable y sin repetirse en la sesión, como hoy; con «reducir
  movimiento» no se reproduce solo.
- Botón principal «Habla con Valer-IA» → `/agente`; secundario «Ver la planificación» → `/planificacion`.
- Rejilla de negocios: cada foto con `alt`, `data-source="stand-in"` y sin pie de foto.
- Pie: declaración de proyecto académico, enlaces a las cuatro áreas y una línea de créditos de fotos.

## Áreas de aplicación

- Se conservan los roles, nombres accesibles y textos que usan las pruebas actuales; cuando un texto cambie, la
  prueba se ajusta en el mismo commit.
- Agente: selector de perfil con su color y glifo; citas como enlaces; tarjeta de aprobación con rol `region` y título.
- Planificación y evidencia: tablas con encabezados, cifras con números tabulares.

## Globales

- Sin desplazamiento horizontal de 320 a 1920 px; objetivos táctiles ≥ 44 px fuera del texto corrido.
- Contraste AA en todo texto; foco visible.
- `prefers-reduced-motion: reduce` → sin animaciones automáticas y nada oculto.
- Sin el logotipo de Manuelita en ninguna parte.
