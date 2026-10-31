# Regla: búsqueda con tgrep

Si `tgrep` está disponible, úsalo antes que `grep` o `find` para buscar código:

```bash
tgrep -- "patrón" .
tgrep -F -- "símbolo" .
tgrep -t py -- "def " .
tgrep -g "src/**" -- "kw" .
tgrep index .
```

El índice vive en `.tgrep/` y no se versiona. Si `tgrep` no está instalado, usa las herramientas
nativas del agente sin instalar nada.
