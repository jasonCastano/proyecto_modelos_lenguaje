# ADR 0017 — Autoría de commits: solo integrantes del equipo y bots autorizados

- **Estado**: aceptada (enmienda de `CONSTITUTION.md` a v1.4.0); limpieza del historial pendiente
- **Fecha**: 2026-11-12
- **Autor**: Roberto José Guerrero
- **Contexto**: principio I (integridad académica y autoría) y §4.3 (commits) de la constitución

## Contexto

Siete commits de `main` (del 2026-11-07 al 2026-11-10) llevan el trailer
`Co-authored-by: Claude Opus 5.5 <noreply@anthropic.com>`. Lo añadió el asistente de IA al crear el commit.
GitHub muestra ese trailer como coautoría y presenta al asistente como contribuidor del repositorio, y dos
descripciones de PR (#35 y #40) terminan con «Generated with Claude Code». La autoría del proyecto es del
equipo; el uso de asistentes ya se declara en la documentación (principio IX).

## Decisión

1. Solo pueden ser autor o coautor de un commit:
   - `jasonCastano` (Jason Alejandro Castaño);
   - `Robertto48` (Roberto José Guerrero Criollo);
   - los bots autorizados, hoy solo `dependabot[bot]`.

   GitHub (`noreply@github.com`) se acepta solo como *committer* de los merges hechos desde la web.
2. Se prohíben los trailers `Co-authored-by` de asistentes de IA y las firmas «Generated with …» en commits,
   PRs, tags y releases.
3. Se aplica en tres capas:
   - **Configuración del asistente**: `.claude/settings.json` con `"includeCoAuthoredBy": false`.
   - **Local**: hook `commit-msg` de pre-commit con `scripts/check_commit_authors.py --message-file`, que
     revisa el autor actual y los trailers.
   - **CI**: job `autoria` en los PRs con `--range base..head`, que revisa autor, committer y trailers de cada
     commit del PR.
4. La lista de identidades vive en `src/proyecto_modelos_lenguaje/authorship.py` y se mantiene alineada con
   §4.3. Añadir un bot exige enmienda.

## Limpieza del historial (pendiente)

Quitar el coautor de los siete commits exige reescribir `main` y hacer *force-push*. El 2026-11-12 la
protección de `main` exige los checks `test` y `web` a quienes no son administradores, y la cuenta
`Robertto48` no es administradora. Por eso la reescritura la ejecuta el mantenedor (`jasonCastano`) o se
hace tras permitir temporalmente el *force-push* en la regla de `main`:

```bash
git clone --mirror https://github.com/jasonCastano/proyecto_modelos_lenguaje.git pml-limpio.git
cd pml-limpio.git
uvx git-filter-repo --message-callback '
import re
message = re.sub(rb"(?im)^[ \t]*co-authored-by:[ \t]*claude[^\n]*\n?", b"", message)
message = re.sub(rb"(?im)^[^\n]*generated with \[?claude code[^\n]*\n?", b"", message)
return message.rstrip() + b"\n"
'
git remote add origin https://github.com/jasonCastano/proyecto_modelos_lenguaje.git
git push --force origin 'refs/heads/*' 'refs/tags/*'
```

Después:

1. Restaurar la protección de `main`.
2. Volver a clonar, o ejecutar `git fetch --all --prune --tags --force` y `git reset --hard origin/main` en
   cada copia local.
3. Verificar con `uv run python scripts/check_commit_authors.py --range <primer-commit>..origin/main`.
4. Editar las descripciones de los PRs #35 y #40.

GitHub conserva los commits originales en las referencias de los PRs cerrados; para purgarlos hay que
solicitarlo al soporte de GitHub.

## Alternativas consideradas

- **Solo configurar el asistente**: evita nuevos casos pero no detecta los commits hechos desde otra máquina
  o herramienta.
- **Validar solo en el CI**: detecta tarde; el hook local evita el commit antes de que exista.
- **No reescribir el historial**: conserva los identificadores, pero el asistente seguiría como coautor
  visible en `main`.

## Consecuencias

- Un commit con un coautor no permitido falla en local (si el hook está instalado) y en el CI del PR.
- La reescritura cambia los identificadores de los commits desde el 2026-11-07 y obliga a actualizar todas
  las copias locales y ramas abiertas.
- El job `autoria` aún no es un check obligatorio; el mantenedor puede añadirlo a la protección de `main`.

## Referencias

- `CONSTITUTION.md` principio I, §4.3 y §10.
- `CONTRIBUTING.md`, sección «Autoría de los commits».
- `scripts/check_commit_authors.py`, `src/proyecto_modelos_lenguaje/authorship.py`,
  `tests/unit/test_authorship.py`.
