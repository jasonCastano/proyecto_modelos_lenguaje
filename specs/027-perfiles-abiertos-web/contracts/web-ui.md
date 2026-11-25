# Contrato: interfaz web sin bloqueo de perfiles

Los selectores son los que usan las pruebas (Vitest y Playwright).

## Agente (`/agente`)

- `[role=radiogroup][aria-label="Perfil con el que te atiende el agente"]` contiene 5 `[role=radio]`, ninguno
  `disabled` ni `aria-disabled`.
- Cada radio muestra el nombre y el texto `forWhom` del perfil. Con las flechas se recorren los cinco.
- `[data-testid=profile-notice]` dice «Te atiende como {perfil}». Con el planificador contiene además el texto de
  datos sintéticos y un enlace «Abrir la planificación» a `/planificacion`.
- La vista técnica (`?vista=tecnica`) muestra el `<select>` de perfil con 5 `<option>` habilitados y sin «(solo
  autorizados)».

## Entrada (`/`)

- `.profile-ledger__row[data-profile=planificador]` contiene un botón con la consulta de ejemplo. No existe
  `.profile-ledger__locked`.
- La acción del héroe hacia la consola dice «Abrir la planificación».

## Planificación (`/planificacion`)

- Sin variables de autorización, carga el estado de planta y el escenario. No existe
  `[data-testid=planner-gate]`.
- Al montar, el perfil activo de la plataforma pasa a `planificador`.

## Toda la web

- El texto «solo autorizados» y «Solo equipo de planta autorizado» no aparece en ninguna página, de 360 a 1920 px.
- axe-core sin violaciones serias ni críticas en `/`, `/agente`, `/planificacion` y `/evidencia`.
