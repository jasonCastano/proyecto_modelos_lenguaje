# ADR 0035 — Frontend profesional de Valer-IA: sitio de producto con la skill design-taste-frontend

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-27
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0030 (plataforma web v1, spec 026) y spec 027 (perfiles abiertos), que esta decisión amplía;
  - ADR 0032 y 0033 (video pitch), que pasa a ser el visual del hero;
  - ADR 0034 (imágenes de perfil), de donde vienen los colores del logotipo;
  - `specs/031-frontend-profesional-valeria/` (spec, plan, research, copy, contrato, tareas).

## Contexto

La web de Valer-IA cumplía los requisitos del Módulo 3, pero se veía como una herramienta técnica. El integrante
pidió un frontend profesional:
- con la skill `design-taste-frontend`;
- con los colores corporativos de Manuelita y elementos de sus productos;
- inspirado en manuelita.com.

## Decisión

1. **Tipo software y reparto de la skill**: hero `split` con el video pitch como visual (sigue siendo lo primero
   de la entrada), navegación centrada, pie de declaración, banda oscura para la planificación, un botón primario
   y un momento animado (`letters-assemble`).
2. **La entrada como sitio de producto**: una sección por pantalla a 1440×900, en este orden:
   - el hero;
   - la app en grande, con una respuesta real del corpus y sus dos citas;
   - los cinco perfiles;
   - los cuatro negocios de Manuelita;
   - la frase «Cada dato, con su fuente.»;
   - la planificación con un diagrama de caña → optimizador → azúcar, etanol y energía;
   - las garantías;
   - las herramientas reales;
   - las preguntas frecuentes;
   - el cierre.
   De manuelita.com se toman la estructura y el tono, no la marca.
3. **El kit de la skill no se copia**: no declara licencia y el repositorio es público y MIT. Sus reglas se
   reimplementan en `web/src/styles/site.css` y `home.css`. Sus scripts se usan como herramientas externas, sin
   versionarlos: gate, copy-lint, capturas, búsqueda de fotos e íconos.
4. **Identidad**:
   - Archivo como única familia (en lugar de la pareja que repartía la skill);
   - paleta de marca con los colores del logotipo: verde para las acciones, rojo anaranjado, naranja y amarillo en
     filetes y hojas;
   - colores fijos por producto;
   - sin el logotipo, su figura ni su tipografía.
5. **Fotos sustitutas**: seis fotos de Wikimedia Commons (CC0, dominio público, CC BY, CC BY-SA), sin marca ni
   personas reconocibles. Se descargan una vez con `scripts/fetch_photos.py`, se guardan en WebP por Git LFS, sus
   créditos van en `web/public/media/fotos/CREDITOS.md` y una prueba exige autor, licencia y fuente. Los íconos
   reales de las herramientas son CC0 (Gil Barbara's logos).
6. **Áreas de trabajo**: agente, planificación y evidencia heredan el sistema (navegación, pie, botones, foco)
   sin cambiar su comportamiento. La consulta, el resumen y la FAQ de los Módulos 1 y 2 pasan a la evidencia.

## Alternativas descartadas

- **Copiar el kit de la skill** (`system.css`, `system.js`, `motion`): riesgo de licencia.
- **Fotos del sitio oficial de Manuelita**: son de su propiedad; la constitución prohíbe su marca.
- **Cambiar de tipografía a la que repartía la skill**: rompería la identidad aprobada y dependería de Google Fonts.
- **Rediseñar solo la entrada**: el integrante pidió las cuatro áreas.

## Consecuencias

- La entrada comunica el producto en la primera pantalla y conserva el video, las garantías y los perfiles.
- El gate de la skill queda en `GATE: OPEN 29` tras sus tres rondas (de 65 FAIL), con cinco exenciones con su
  motivo. La mayoría de lo abierto viene de que el gate reconoce la rejilla de su propio kit y no la reimplementada
  (bordes y columnas) y pide fotos donde hay íconos propios o UI viva. Queda documentado en
  `specs/031-frontend-profesional-valeria/quickstart.md`.
- Las pruebas de interfaz y de extremo a extremo se ajustaron a los textos nuevos; los comportamientos no cambiaron.
- Las fotos son ilustrativas: no muestran operaciones de Manuelita.
