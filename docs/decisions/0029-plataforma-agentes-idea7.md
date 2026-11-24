# ADR 0029 — Valer-IA como plataforma de agentes por perfil, con planificación industrial sobre datos sintéticos

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-24
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0022 (Valer-IA Caña) y ADR 0028 (WhatsApp con OpenClaw);
  - `specs/025-agentes-manuelita-idea7/`;
  - idea 7 de [`docs/alucinaciones/ideas_negocio_ia_manuelita.md`](../alucinaciones/ideas_negocio_ia_manuelita.md).

## Contexto

El producto del Módulo 3 (spec 024) es un asistente de preguntas para visitantes en WhatsApp. El documento de ideas
de negocio identifica la **idea 7** como la de mejor relación entre impacto y esfuerzo, porque reutiliza la
arquitectura existente. La idea 7 propone agentes para cuatro públicos:

1. clientes B2B;
2. proveedores;
3. colaboradores;
4. planificación industrial (§7.4).

La sustentación final (Anuncio 007) premia el function calling, la planificación de varios pasos y el valor de
negocio del pitch (ítems 1.1, 1.2 y 5.1).

Restricciones:

- quedan cuatro días hasta el sábado 28 de noviembre de 2026;
- no hay acceso al ERP, a los históricos de planta ni a documentos internos de Manuelita;
- las reglas de la spec 024 (un solo agente, catálogo único, MCP de solo lectura, seudónimos, hardening) no deben
  romperse;
- la demo actual debe seguir disponible como respaldo.

## Decisión

1. **Perfiles en vez de agentes separados.** Un solo agente (el mismo `ChatService`) con cinco perfiles: visitante,
   cliente B2B, proveedor, colaborador y planificador.
   - Cada perfil declara su foco y su subconjunto de herramientas en un solo lugar.
   - El router combina ruta y perfil.
   - Se descartan agentes independientes por público: duplicarían memoria, blindaje y evaluación, y romperían la
     regla de un solo agente de la ADR 0028.
2. **Planificación industrial con simulador y optimizador deterministas.**
   - El LLM coordina y explica. Las cifras salen de herramientas: un simulador de balances lineal y un optimizador
     de programación lineal.
   - Se descarta que el LLM «razone» el plan: no es verificable y contradice el principio IV (cifras desde código,
     como `calculate` y `compare_indicator`).
3. **Datos sintéticos declarados.**
   - La planta de caña (y, si alcanza el tiempo, la de palma) se modela con datos generados con semilla y con ficha
     propia.
   - Las respuestas los etiquetan como sintéticos, y nunca se mezclan con el corpus público ni se atribuyen a
     Manuelita.
   - Se descarta esperar datos reales: no llegarían a tiempo, y presentarlos como reales violaría el principio III.
4. **Autorización y aprobación.**
   - El perfil planificador es solo para usuarios autorizados.
   - Guardar una propuesta exige «SÍ/NO» con vencimiento.
   - El modo degradado no planifica.
   - El agente recomienda y el equipo decide.
5. **Catálogo de 26 herramientas.** Se suman cinco de lectura (estado de planta, compromisos, procedimientos,
   simulación y optimización) y una de escritura (guardar propuesta). La regla «mínimo 20» se mantiene.

## Consecuencias

- **Positivas:**
  - El pitch pasa de «un chatbot que cita» a «una plataforma de agentes que también recomienda decisiones de planta».
  - La planificación de varios pasos queda visible en la traza.
  - El catálogo gana herramientas con lógica real, no solo búsquedas.
- **Negativas:**
  - Más superficie para la demo y cuatro días de margen.
  - Los datos sintéticos limitan lo que se puede afirmar del impacto: se presenta como demostración, no como
    resultado.
- **Mitigación:**
  - Calendario con corte el miércoles 25 por la noche.
  - Si el optimizador no está en verde, la planificación se muestra solo en la web y WhatsApp vuelve a la secuencia
    de la spec 024.
- **Constitución:** enmienda **2.0.0** (MAJOR, porque cambia el propósito y alcance del producto) en §1, en la Fase 3
  (reglas 16–21), en §8.4 y en el historial.
