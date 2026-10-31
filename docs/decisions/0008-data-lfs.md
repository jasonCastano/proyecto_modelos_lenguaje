# ADR 0008 — Datos medallion en Git LFS

- **Estado**: aceptada
- **Fecha**: 2026-10-30
- **Autores**: Jason Alejandro Castaño, Roberto José Guerrero
- **Contexto**: Módulo 1, entrega de la fase final

## Contexto

La constitución establece que los datos y artefactos pesados no se versionan y se referencian por manifiesto
y hash. Para la fase final del Módulo 1, Roberto necesita los datos de bronce, plata y oro disponibles desde
GitHub sin depender de una regeneración local.

Los datos sin cuarentena ocupan aproximadamente:

| Capa | Archivos | Tamaño sin caché |
|------|---------:|-----------------:|
| Bronce | 610 | 366 MB |
| Plata | 450 | 22 MB |
| Oro | 36 | 101 MB |
| **Total** | **1.096** | **489 MB** |

El archivo mayor es `data/bronze/_meta/bronze.sqlite3` (86,8 MB). La cuarentena ocupa 8,93 GB y no se
necesita para ejecutar el Módulo 1.

## Decisión

Versionar **bronce, plata y oro** en **Git LFS**, excluyendo:

- `data/quarantine/`
- `data/*/_meta/cache/`
- `data/*/_meta/smoke/`
- `data/module1/`
- `*.sqlite3-wal` y `*.sqlite3-shm`

Las capas se declaran en `.gitattributes` con `filter=lfs diff=lfs merge=lfs -text`. La cuarentena y los
cachés permanecen en `.gitignore`.

## Consecuencias

- Un clon nuevo requiere `git lfs install` y `git lfs pull` para materializar los datos.
- El repositorio Git crece poco; los objetos pesados viven en LFS (cuota gratuita de 1 GB).
- El clon completo descarga ~489 MB; la cuarentena no se descarga.
- CI sigue funcionando sin LFS porque las pruebas usan fixtures temporales y no leen `data/`.
- La ficha de datos y el README deben indicar el procedimiento de clonación con LFS.
- La constitución se mantiene para el resto de artefactos; esta es una excepción explícita aprobada para la
  entrega del Módulo 1.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| No versionar datos y regenerarlos | Roberto necesitaba los datos sin ejecutar todo el pipeline |
| Subir la cuarentena | 8,93 GB; no se usa y excede la cuota |
| Release asset con un ZIP | Válido, pero el usuario pidió sincronizar en el repositorio |
| Repositorio separado solo de datos | Añade otra URL y otro flujo de clonación |
| Git normal sin LFS | Archivos de 86,8 MB y un repositorio de ~489 MB en el historial |

## Validación

- `git lfs install` en el repositorio.
- `git lfs ls-files` lista los archivos de bronce, plata y oro.
- `git show HEAD:data/gold/knowledge_units.jsonl` devuelve un puntero LFS, no el contenido.
- Un clon con `git lfs pull` materializa los datos.
- `git status` no muestra cuarentena, cachés ni archivos SQLite transitorios.

## Licencias

Los datos conservan la condición de uso académico y las licencias de sus fuentes. Git LFS no cambia la
licencia ni autoriza la redistribución fuera del ámbito académico.
