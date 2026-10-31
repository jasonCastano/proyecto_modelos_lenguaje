# Quickstart — identidad visual Manuelita

**Feature**: `009-manuelita-visual-identity`
**Fecha**: 2026-10-30

Guía de validación de la identidad visual aplicada a la app del Módulo 1. Todo se ejecuta en local, sin
conexión y sin Ollama gracias al modo de demostración.

## 1. Requisitos

```bash
uv sync
uv run ruff check .
uv run pytest -q
```

- `data/gold/` materializado (`git lfs pull`) para ver respuestas reales.
- Opcional: Ollama activo con `llama3.1:8b`; si no, usar `PML_DEMO=1`.

## 2. Arranque

```bash
uv run streamlit run app.py
```

Resultado esperado:

- La app abre en el navegador en menos de 15 segundos.
- La cabecera muestra «Grupo Manuelita · Ingenio Manuelita», el nombre del proyecto y el lema.
- La barra de estado muestra datos, modelo y, si aplica, el badge «Modo demo».
- Los colores visibles pertenecen a la paleta institucional (verde bosque y naranja como dominantes).

## 3. Modo de demostración (sin Ollama)

```bash
PML_DEMO=1 uv run streamlit run app.py
```

Resultado esperado:

- Badge «Modo demo» visible de forma persistente.
- Las tres pestañas responden con el modelo falso.
- La identidad visual es idéntica a la del modo real.

## 4. Cabecera y pie

1. Abrir la app sin desplazarse: la firma de marca y el nombre del proyecto deben estar visibles.
2. Desplazarse al final: debe aparecer la atribución de la marca y el aviso «no afiliado».
3. Redimensionar a 360 px de ancho: no debe aparecer scroll horizontal y el texto debe seguir legible.

## 5. Tarjetas de fuente

```text
Pestaña Q&A → preguntar «¿Qué productos ofrece Manuelita?» → revisar las fuentes
```

Resultado esperado:

- Cada cita aparece como tarjeta con etiqueta `[U#]`, título, ubicación y enlace.
- El enlace se abre en pestaña nueva y el foco es visible al navegar con Tab.
- Una cita sin sección declara «sin sección declarada».

## 6. Estados

| Acción | Estado esperado |
|--------|-----------------|
| Pregunta sin evidencia («fútbol baloncesto») | Badge informativo «Sin evidencia», no rojo |
| Pregunta vacía | Validación, sin llamada al modelo |
| Ollama detenido (sin demo) | Badge «Error» + mensaje accionable + reintento |
| `data/gold` ausente | Indicador de datos incompletos con `git lfs pull` |
| Modo demo activo | Badge «Modo demo» persistente |

## 7. Contraste y accesibilidad

```bash
uv run pytest tests/unit/test_brand.py -q
```

Resultado esperado:

- Todos los pares de contraste declarados cumplen su mínimo (4.5:1 o 3:1).
- Ningún token contiene URLs ni rutas absolutas.
- La paleta serializada valida contra `contracts/brand-tokens.schema.json`.

Comprobación manual: desaturar la pantalla (escala de grises) y verificar que cada estado sigue siendo
distinguible por su icono y su texto.

## 8. Pruebas de interfaz

```bash
uv run pytest tests/unit/test_app.py tests/integration/test_app_brand.py -q
```

Resultado esperado:

- Cabecera, badges y pie presentes en las tres pestañas.
- Sin excepciones en `AppTest`.
- Las pruebas de la spec 008 siguen pasando sin cambios de comportamiento.

## 9. Sin conexión

Desconectar la red (o bloquear el host del sitio oficial) y repetir los pasos 2 a 5.

Resultado esperado:

- La identidad se muestra completa: no hay fuentes, imágenes ni CSS remotos.

## 10. Criterios de aceptación

| Escenario | Criterio |
|-----------|----------|
| Reconocimiento | Dos de tres observadores identifican Manuelita en menos de 5 s |
| Contraste | 100% de los pares declarados cumplen 4.5:1 o 3:1 |
| Citas | 100% con etiqueta, título, ubicación y enlace |
| Estados | 100% distinguibles con color desaturado |
| Regresión | Suite de la spec 008 en verde |
| Offline | Identidad completa sin red |
| Ancho mínimo | Sin scroll horizontal a 360 px |
| Arranque | Incremento ≤ 2 s respecto de la versión anterior |
| Atribución | Aviso de no afiliación visible en el pie |
| Marca | Ninguna afirmación de respaldo o afiliación oficial |
