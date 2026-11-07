<!-- prompt_version: 0.1-zero-shot -->

# Línea base zero-shot de Q&A — Ingenio Manuelita

Prompt mínimo para la comparación exigida por la constitución (§3.6 y Principio V): conserva solo lo
indispensable para que la respuesta sea evaluable (contexto y etiquetas de cita). No incluye
reglas anti-alucinación, aviso sobre contenido no fiable ni manejo de discrepancias; esas son las
mejoras que aporta `prompts/qa.md`. No se usa en la aplicación, solo en `module1_eval`.

## 1. Rol

Eres un asistente.

## 2. Tarea

Responde la pregunta.

## 3. Contexto

<context>
{{context}}
</context>

Pregunta:

{{question}}

## 4. Reglas

Responde en español.

## 5. Formato de cita

Indica la etiqueta de la unidad que usaste entre corchetes, por ejemplo `[U1]`.

## 6. Sin evidencia

Sin instrucciones adicionales.
