<!--
Sync Impact Report
==================
Version change: (sin ratificar) → 1.0.0
Bump rationale: ratificación inicial. El archivo contenía únicamente la plantilla sin
resolver; se definen por primera vez principios, restricciones y gobernanza.

Modified principles:
- [PRINCIPLE_1_NAME] → I. Reproducibilidad Experimental (NO NEGOCIABLE)
- [PRINCIPLE_2_NAME] → II. Evaluación con Métricas y Línea Base
- [PRINCIPLE_3_NAME] → III. Procedencia y Ética de Datos
- [PRINCIPLE_4_NAME] → IV. Experimentos como Código Versionado
- [PRINCIPLE_5_NAME] → V. Simplicidad y Alcance Académico

Added sections:
- Restricciones Técnicas (antes [SECTION_2_NAME])
- Flujo de Trabajo y Puertas de Calidad (antes [SECTION_3_NAME])

Removed sections: ninguna. Solo se sustituyeron marcadores de plantilla.

Templates and dependent artifacts: sin cambios. Leen la constitución en tiempo de
ejecución; no se modificó ninguna capa versionada de plantillas.

Follow-up TODOs: ninguno. La fecha de ratificación corresponde a la adopción inicial
de este documento; si existiera una adopción anterior no registrada, corregir la fecha
y aplicar un bump PATCH.
-->

# Proyecto Modelos de Lenguaje Constitution

## Core Principles

### I. Reproducibilidad Experimental (NO NEGOCIABLE)

Todo resultado reportado DEBE poder regenerarse desde un clon limpio del repositorio.
Un resultado que no se puede reproducir no constituye evidencia válida para el proyecto.

- El entorno se reconstruye con `uv sync --frozen`; `uv.lock` se versiona y no se edita a mano.
- Todo experimento fija semillas aleatorias y registra la versión exacta de Python y dependencias.
- Cada conjunto de datos tiene un manifiesto con origen, licencia, fecha de obtención, método
  de recolección y hash SHA-256 del archivo utilizado.
- Los hiperparámetros y rutas viven en archivos de configuración versionados, no en celdas
  ni en variables de entorno no documentadas.
- Cada ejecución relevante registra commit, comando, configuración, versión de datos y métricas
  en un registro de experimentos dentro del repositorio.

**Racional**: la evaluación académica exige que terceros puedan verificar los resultados; la
reproducibilidad es la condición mínima para defender cualquier conclusión.

### II. Evaluación con Métricas y Línea Base

Ninguna técnica, modelo o mejora se declara exitosa sin una medición explícita contra una
línea base definida antes de ejecutar el experimento.

- Las métricas se eligen y justifican antes de observar resultados de test.
- Toda variante se compara contra al menos una línea base trivial o publicada.
- Los resultados se reportan como media y dispersión sobre múltiples semillas cuando el
  proceso sea estocástico.
- El conjunto de test se reserva para la evaluación final; la selección de modelos usa
  validación.
- Las afirmaciones de mejora se acompañan de la tabla de resultados que las sustenta.

**Racional**: sin línea base ni métricas predefinidas, una diferencia observada no distingue
una mejora real de una variación por azar o de un sesgo de selección.

### III. Procedencia y Ética de Datos

Todo dato utilizado DEBE tener procedencia documentada y uso legalmente permitido.

- Cada dataset cuenta con una ficha que declara origen, licencia, método y fecha de recolección,
  tamaño, idioma, limitaciones conocidas y posibles sesgos.
- La recolección respeta `robots.txt`, los términos de servicio, los límites de tasa y la
  identificación del cliente; no se eluden controles de acceso.
- No se incorporan datos personales identificables ni contenido sensible sin anonimización
  verificable y justificación explícita.
- Los datos crudos son inmutables; toda transformación es un paso versionado y reversible.
- Los conjuntos de datos y artefactos pesados no se confirman en Git; se referencian por
  manifiesto y hash.

**Racional**: el proyecto trabaja con texto de terceros; la trazabilidad y el consentimiento
de uso protegen tanto la validez científica como a las personas representadas en los datos.

### IV. Experimentos como Código Versionado

La lógica experimental vive en código versionado e invocable; los notebooks son solo un
medio de exploración.

- Los pipelines residen en `src/proyecto_modelos_lenguaje/` y se ejecutan mediante una interfaz
  de línea de comandos documentada.
- Un notebook puede explorar, pero toda conclusión debe respaldarse con un script versionado
  que reproduzca el resultado.
- El código no contiene rutas absolutas, credenciales ni pasos manuales no documentados.
- Los artefactos generados se producen con un comando registrado en el README o en el plan.
- La configuración se externaliza en YAML/TOML y se valida al inicio de cada ejecución.

**Racional**: el código es el registro verificable del método; el estado manual de un notebook
no es auditable ni repetible por un evaluador.

### V. Simplicidad y Alcance Académico

Cada incremento DEBE resolver una pregunta concreta del curso con la menor complejidad
suficiente.

- Se prefiere la solución más simple que produzca una medición válida (YAGNI).
- No se añade infraestructura, servicio o abstracción sin una necesidad demostrada.
- Las dependencias nuevas se justifican por escrito indicando qué problema resuelven.
- Los compromisos de diseño se registran en el plan o en una decisión de arquitectura.
- El alcance se limita a lo evaluable dentro del calendario académico.

**Racional**: el objetivo es demostrar comprensión de las técnicas, no construir una plataforma;
la complejidad no justificada dificulta la revisión y la reproducción.

## Restricciones Técnicas

- **Lenguaje**: Python 3.14 o superior, gestionado exclusivamente con `uv`; no se usa `pip` ni
  `conda` para el entorno del proyecto.
- **Estructura**: disposición `src/` con el paquete `src/proyecto_modelos_lenguaje/`.
- **Calidad**: Ruff para lint y formato, y `pytest` para pruebas; ambos se ejecutan antes de
  cada integración.
- **Tipado**: las funciones y métodos públicos declaran anotaciones de tipo; los módulos
  exponen docstrings breves.
- **Recolección**: `scrapling` se usa solo en la capa de adquisición; el procesamiento y la
  evaluación no dependen de la red.
- **Secretos**: claves y credenciales se leen de variables de entorno; `.env` nunca se versiona.
- **Portabilidad**: rutas con `pathlib`, texto en UTF-8 y comandos compatibles con Windows y Linux.
- **Tamaño**: ningún archivo de datos o artefacto mayor a 10 MB se confirma en Git.

## Flujo de Trabajo y Puertas de Calidad

- **Ciclo dirigido por especificación**: `/speckit.specify` → `/speckit.clarify` →
  `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`. No se implementa sin plan aprobado.
- **Constitution Check**: el plan DEBE incluir la verificación de estos principios; toda
  violación se justifica en Complexity Tracking o se corrige antes de continuar.
- **Pruebas**: pruebas unitarias para preprocesamiento y métricas, y al menos una prueba
  extremo a extremo sobre una muestra mínima; las pruebas no dependen de la red.
- **Revisión**: cada cambio se contrasta con esta constitución antes de integrarse; el lint y
  las pruebas deben pasar.
- **Commits**: mensajes en formato Conventional Commits y commits atómicos alineados con las
  tareas del plan.
- **Documentación**: README, ficha de datos y registro de experimentos se actualizan cuando
  cambia el comportamiento observable.
- **Integración**: no se integra código con pruebas fallidas, lint pendiente o violaciones
  constitucionales sin resolver.

## Governance

Esta constitución prevalece sobre cualquier otra práctica, guía o preferencia del proyecto.
Cuando exista conflicto, prevalece este documento.

**Procedimiento de enmienda**:

1. Presentar la propuesta por escrito con el cambio, su justificación y el impacto esperado.
2. Obtener la aprobación del responsable del proyecto.
3. Determinar el tipo de versión y actualizar este archivo junto con los artefactos afectados.
4. Registrar la enmienda en el historial de Git; el Sync Impact Report es material temporal de
   revisión y no forma parte de la gobernanza.

**Política de versionado** (semántico `MAJOR.MINOR.PATCH`):

- `MAJOR`: eliminación o redefinición incompatible de principios o reglas de gobernanza.
- `MINOR`: nuevo principio o sección, o ampliación material de la guía existente.
- `PATCH`: aclaraciones, correcciones de redacción o refinamientos no semánticos.

**Cumplimiento**: todo plan, revisión e integración verifica el cumplimiento de esta
constitución. Las desviaciones se documentan y aprueban explícitamente; el incumplimiento no
justificado bloquea la integración. La revisión de cumplimiento se realiza al cierre de cada
fase y en cada entrega evaluable del curso.

**Version**: 1.0.0 | **Ratified**: 2026-10-27 | **Last Amended**: 2026-10-27
