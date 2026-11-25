# ADR 0031 — Perfiles abiertos en la web, incluido el planificador; autorización por canal

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-25
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0029 (plataforma de agentes de la idea 7: perfiles y planificador autorizado);
  - ADR 0030 (plataforma web en cuatro áreas y API v1);
  - `specs/027-perfiles-abiertos-web/` (spec, plan, `design.md`, contratos).

## Contexto

Desde la spec 025, el perfil planificador industrial solo se abría con una autorización configurada en el
servidor: `VALERIA_PLANNERS`, `MANUELITA_PLANNER_OPEN` o, en la web, `MANUELITA_PLANNER_WEB`. Sin ella:

- el selector mostraba el planificador deshabilitado («Solo equipo de planta autorizado»);
- la entrada lo mostraba con candado;
- `/planificacion` mostraba una pantalla de acceso denegado;
- `/api/v1/planning/*` respondía 403 `planner_forbidden`.

Esto confundió a quien clonaba el repositorio: el propietario no pudo ver la consola. Además, ocultaba la capacidad
central de la idea 7. Los datos de planificación son **sintéticos** y ninguna herramienta toca sistemas reales de
planta, así que el filtro no protegía información real en la web.

El integrante pidió que cualquier persona que use la aplicación web pueda elegir cualquiera de los cinco perfiles:
«el cliente escogerá cuál le conviene más».

## Decisión

1. **La autorización depende del canal**, en un solo punto: `profiles.is_authorized(user_id, channel)`.
   - En `web` devuelve siempre `True`.
   - En los demás canales (WhatsApp) se conservan `MANUELITA_PLANNER_OPEN` y `VALERIA_PLANNERS`.
   - `MANUELITA_PLANNER_WEB` deja de leerse; si está en un `.env` viejo, no tiene efecto.
2. Todos los guardias que ya usaban esa función quedan abiertos en la web sin cambiar su lógica:
   - el perfil del turno (`effective_profile`);
   - la validación del perfil en el chat (`validate_profile`);
   - la lista `/api/profiles`;
   - la API v1 de planificación.

   `requires_authorization` se informa por canal (`Profile.requires_authorization_in`).
3. **API v1**: `require_planner` pasa a `planner_user`, que solo devuelve el seudónimo para el registro.
   `/access` se conserva por compatibilidad y siempre responde `authorized: true`. El código `planner_forbidden`
   desaparece de la web.
4. **Interfaz** (diseño con frontend-design, `specs/027-perfiles-abiertos-web/design.md`):
   - Se retiran el candado, los rótulos «solo autorizados», las opciones deshabilitadas y `PlannerGate`.
   - El selector es un registro de cinco columnas con glifo, nombre y «para quién es».
   - Un aviso dice el perfil activo y, con el planificador, recuerda que los datos son sintéticos y ofrece abrir la
     consola.
   - Abrir `/planificacion` activa el perfil planificador.
5. **«Soy planificador»** cambia de perfil como en los otros perfiles (disparadores en `config/profiles.toml`).
   En WhatsApp sin autorización no se anuncia un perfil que no rige.
6. **Se conservan las salvaguardas**:
   - guardar una propuesta exige dos pasos, vence y tiene límite de pendientes;
   - cada llamada de la consola y cada propuesta quedan con el seudónimo de la sesión;
   - la advertencia de datos sintéticos aparece en cada pantalla y respuesta;
   - las cifras salen solo del optimizador (paridad 12/12);
   - el modo degradado no planifica.

## Alternativas consideradas

- **Activar `MANUELITA_PLANNER_WEB=1` por defecto en `.env.example`**: el control seguiría dependiendo de la
  configuración de cada equipo, que es justo lo que falló.
- **Quitar `requires_authorization` de `config/profiles.toml`**: abriría también WhatsApp, que usa el número real de
  un integrante y queda fuera de lo pedido.
- **Borrar cada comprobación por separado**: más cambios y más riesgo de dejar una viva. Un único punto de decisión
  evita que la UI y el backend vuelvan a divergir.

## Consecuencias

- Cualquier visitante de la web puede planificar y guardar propuestas sobre la planta sintética. El archivo de
  propuestas crece solo con confirmaciones en dos pasos, y cada propuesta lleva su seudónimo.
- La constitución sube a **2.2.0 (MINOR)**: se enmiendan §3.7 y la regla 20. Requiere la aprobación de jasonCastano.
- WhatsApp no cambia; una prueba de regresión lo fija (`tests/unit/channels/test_bridge_profile.py`).
- Las evaluaciones del planificador ya no necesitan fijar ninguna variable para correr.
