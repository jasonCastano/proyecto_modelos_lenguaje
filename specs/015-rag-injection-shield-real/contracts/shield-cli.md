# Contrato: comando `agent shield`

```bash
uv run python -m proyecto_modelos_lenguaje.agent shield [opciones]
```

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `--mode {demo,real}` | `demo` | `real` usa DeepSeek y exige `DEEPSEEK_API_KEY` |
| `--variants chain agent` | ambas | Variantes a evaluar |
| `--cases PATH` | `tests/fixtures/rag/malicious/shield_cases.jsonl` | Casos (ver `shield-cases.schema.json`) |
| `--repeat N` | `1` | Repeticiones por caso y variante (N ≥ 1); la corrida documentada usa 3 |
| `--no-neutralize` | apagado | Línea base: entrega los fragmentos sin neutralizar |
| `--run-id ID` | fecha y hora | Identificador de la corrida |
| `--json-out PATH` | `docs/evaluacion_blindaje.json` (neutralizado) o `docs/evaluacion_blindaje_base.json` (`--no-neutralize`), solo en `real` | Informe JSON (ver `shield-report.schema.json`); un archivo por corrida para que la línea base y la neutralización no se sobrescriban |
| `--report PATH` | `docs/evaluacion_blindaje.md` (solo en `real`) | Sección Markdown regenerada |

**Comportamiento**
- Activa internamente el corpus adversarial. No depende de que `MANUELITA_DEMO_CORPUS` esté definida.
- Checkpointer y Store en memoria. No escribe en `MANUELITA_STATE_DIR` ni en `data/`.
- En `demo` no escribe en `docs/` salvo que se pasen `--json-out` o `--report` explícitos.
- Imprime una tabla por caso y el resumen por variante.

**Códigos de salida**

| Código | Significado |
|--------|-------------|
| `0` | Todos los casos pasan (`passed = true`) |
| `1` | Al menos un caso falla; el informe se escribe igual, con los fallos tal como ocurrieron |
| `2` | Configuración inválida, falta la clave o el proveedor no responde; no se escribe informe |
