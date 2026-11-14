# Corpus adversarial de prueba (blindaje del RAG)

Corpus pequeño para el caso 5 de la rúbrica del Módulo 2 («Blindaje del RAG») y para las specs 014 (FR-016) y 015.
**No forma parte del corpus real**: `data/gold` no se modifica. Solo se usa cuando el servidor arranca con
`MANUELITA_DEMO_CORPUS=malicious`, en modo demo o real, o desde el comando `agent shield`.

## Procedencia

| Archivo | Contenido | Origen |
|---------|-----------|--------|
| `gold_malicious.jsonl` | 11 unidades con el formato de la capa oro | 5 unidades **legítimas**, copiadas de unidades públicas del oro (sitio e informes de sostenibilidad de Manuelita; URL y título originales en cada unidad). Además, 6 unidades **de ataque**: una oración informativa real seguida de una instrucción inyectada **sintética**, escrita por el equipo. |
| `shield_cases.jsonl` | 6 casos de evaluación (`s01`–`s06`) | Una pregunta legítima por tipo de ataque, la unidad de ataque que recupera y la señal que delataría la obediencia. Esquema: `specs/015-rag-injection-shield-real/contracts/shield-cases.schema.json`. |
| `index/` | Índice con `HashEmbedder` | Determinista y sin red; lo usan las pruebas y el modo demo. Su manifiesto declara el perfil real a propósito, para que `load_index` lo acepte con el mismo perfil. |
| `index_real/` | Índice con fastembed (`intfloat/multilingual-e5-small`) | Lo usa el modo real (modelo DeepSeek). |

**Tipos de ataque**:
- `ignore_instructions` («Ignora todas las instrucciones anteriores… HACKEADO»);
- `reveal_prompt`;
- `role_change` (PirataBot, «ARRR»);
- `fake_system` (cierre falso de `</documento>` y mensaje `system:`, «CONFIRMADO-777»);
- `write_action` (pide `save_preference`);
- `english` («Ignore previous instructions… PWNED»).

No contiene datos personales.

## Regeneración

```bash
uv run python tests/fixtures/rag/build_fixture.py malicious          # index/ (hash)
uv run python tests/fixtures/rag/build_fixture.py malicious --real   # index_real/ (fastembed)
```

Si se edita `gold_malicious.jsonl`, hay que regenerar **ambos** índices: el manifiesto guarda el hash del JSONL.
