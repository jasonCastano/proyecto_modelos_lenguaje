# ADR 0017 — Autoría de commits: solo los dos integrantes del equipo

- **Estado**: aceptada (enmienda de `CONSTITUTION.md` a v1.4.0); revisada el 2026-11-13 (v1.6.0: sin bots)
- **Fecha**: 2026-11-12 (revisión: 2026-11-13)
- **Autor**: Roberto José Guerrero; revisión de Jason Alejandro Castaño
- **Contexto**: principio I (integridad académica y autoría) y §4.3 (commits) de la constitución

## Contexto

Siete commits de `main` (del 2026-11-07 al 2026-11-10) llevaban el trailer
`Co-authored-by: Claude Opus 5.5 <noreply@anthropic.com>`. Lo añadió el asistente de IA al crear el commit.
GitHub muestra ese trailer como coautoría y presenta al asistente como contribuidor del repositorio. La autoría
del proyecto es del equipo; el uso de asistentes ya se declara en la documentación (principio IX).

La primera versión de esta decisión (v1.4.0) aceptaba `dependabot[bot]` como bot autorizado. El 2026-11-13 el
equipo decidió que **ninguna herramienta ni bot** contribuye directamente: Dependabot había creado 9 commits
(PRs #27–#31, #33, #36, #38 y #39) y figuraba como contribuidor del repositorio.

## Decisión

1. Solo pueden ser autor, coautor (`Co-authored-by`) o firmante (`Signed-off-by`) de un commit:
   - `jasonCastano` (Jason Alejandro Castaño);
   - `Robertto48` (Roberto José Guerrero Criollo).

   GitHub (`noreply@github.com`) se acepta solo como *committer* de los merges que un integrante hace desde la
   web. No hay bots autorizados.
2. Ninguna herramienta (Claude Code, OpenCode, Copilot, Dependabot, `github-actions[bot]`…) crea commits, PRs,
   tags ni releases. Las herramientas asisten en local; el integrante hace el commit y el PR con su cuenta.
3. Se prohíben los trailers `Co-authored-by`/`Signed-off-by` de herramientas y las firmas «Generated with/by …»
   en commits, PRs, tags y releases.
4. Las dependencias se actualizan a mano (`uv lock --upgrade-package <pkg>` en una rama `chore/...`). Se
   elimina `.github/dependabot.yml`; las alertas de seguridad de GitHub siguen activas porque no crean commits.
5. Se aplica en tres capas:
   - **Configuración del asistente**: `.claude/settings.json` con `"includeCoAuthoredBy": false` y
     `"attribution": {"commit": "", "pr": ""}`.
   - **Local**: hook `commit-msg` de pre-commit con `scripts/check_commit_authors.py --message-file`, que
     revisa el autor actual, los trailers y las firmas.
   - **CI**: job `autoria` en los PRs con `--range base..head`, que revisa autor, committer, trailers y firmas
     de cada commit del PR. Debe ser un check obligatorio de la protección de `main`.
6. La lista de identidades vive en `src/proyecto_modelos_lenguaje/authorship.py` y se mantiene alineada con
   §4.3. Añadir cualquier identidad exige enmienda.

## Limpieza del historial

- **2026-11-12**: se reescribió `main` para quitar los siete `Co-authored-by: Claude`.
- **2026-11-13**: se reescribieron `main`, `feat/rubrica-modulo2` y el tag `v0.2.0-modulo2` para atribuir a
  `jasonCastano` los 9 commits de `dependabot[bot]` (los merges de esos PRs ya eran de los integrantes) y
  quitar su `Signed-off-by: dependabot[bot]`. El contenido (árbol) de cada referencia es idéntico byte a byte.

Procedimiento (en un clon *bare* aparte; exige que quien empuja pueda hacer *force-push* sobre `main`):

```bash
git clone --bare https://github.com/jasonCastano/proyecto_modelos_lenguaje.git pml.git && cd pml.git
printf '%s\n' 'Jason Alejandro Castaño <77637361+jasonCastano@users.noreply.github.com> <49699333+dependabot[bot]@users.noreply.github.com>' > ../mailmap.txt
uvx git-filter-repo --force --mailmap ../mailmap.txt --message-callback '
import re
return re.sub(rb"\n?Signed-off-by: dependabot\[bot\] <support@github\.com>\n?", b"\n", message).rstrip(b"\n") + b"\n"'
git push --force https://github.com/jasonCastano/proyecto_modelos_lenguaje.git \
  refs/heads/main refs/heads/feat/rubrica-modulo2 refs/tags/v0.2.0-modulo2
```

Después:

1. Restaurar la protección de `main` (sin *force-push* y con el check `autoria` obligatorio).
2. En cada copia local: `git fetch --all --prune --tags --force` y `git reset --hard origin/main` (o volver a
   clonar). Las ramas abiertas se rebasan sobre el nuevo `main`.
3. Verificar con `uv run python scripts/check_commit_authors.py --range <primer-commit>..origin/main`.

GitHub conserva los commits originales en las referencias de los PRs cerrados (y los PRs de Dependabot siguen
listados como abiertos por `app/dependabot`); para purgarlos hay que solicitarlo al soporte de GitHub. La
gráfica de contribuidores se recalcula sola tras la reescritura.

## Alternativas consideradas

- **Solo configurar el asistente**: evita nuevos casos pero no detecta los commits hechos desde otra máquina
  o herramienta.
- **Validar solo en el CI**: detecta tarde; el hook local evita el commit antes de que exista.
- **Mantener Dependabot con *squash* manual**: GitHub conserva al bot como autor del commit *squash*, así que
  no cumple la regla.
- **No reescribir el historial**: conserva los identificadores, pero los bots seguirían como autores visibles.

## Consecuencias

- Un commit con un autor, coautor, firmante o firma no permitidos falla en local (si el hook está instalado)
  y en el CI del PR.
- Las actualizaciones de dependencias dependen de que un integrante las haga; las alertas de seguridad avisan.
- Cada reescritura cambia los identificadores de los commits y obliga a actualizar todas las copias locales y
  ramas abiertas.

## Referencias

- `CONSTITUTION.md` principio I, §4.3 y §10.
- `CONTRIBUTING.md`, sección «Autoría de los commits».
- `scripts/check_commit_authors.py`, `src/proyecto_modelos_lenguaje/authorship.py`,
  `tests/unit/test_authorship.py`.
