---
name: bitacora
description: Genera una bitácora fechada del proyecto RAG Ingenio Manuelita con el contexto de CONSTITUTION.md, el estado local y remoto de Git, el avance por fase, los objetivos cumplidos, los pendientes, la cascada secuencial de tareas con dependencias y puertas de calidad, y los próximos pasos. Úsala cuando el usuario pida "bitácora", "estado del proyecto", "avance", "qué falta", "qué sigue" o "tareas pendientes en orden".
---

# Bitácora del Proyecto (Claude Code)

Esta skill es un puente hacia la skill canónica de opencode. **No dupliques su contenido aquí.**

1. Lee y sigue al pie de la letra `.opencode/skills/bitacora/SKILL.md` (flujo obligatorio, reglas,
   contenido esperado y diagnóstico).
2. El generador vive en `.opencode/skills/bitacora/scripts/generate_bitacora.py`; ejecútalo desde la raíz
   del repositorio:

   ```bash
   uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py
   ```

   Opciones: `--dry-run` (sin escribir), `--skip-checks` (sin pruebas/Ruff), `--no-fetch` (sin remoto).

Cualquier cambio de la skill se hace en `.opencode/skills/bitacora/`, no en este archivo.
