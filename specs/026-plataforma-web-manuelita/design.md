# Dirección visual: Valer-IA, plataforma de agentes de Manuelita (spec 026)

**Fecha**: 2026-11-24 · **Autor**: Roberto José Guerrero · **Método**: skill `frontend-design`

## 1. Tema, público y tarea principal

- **Tema**: la cadena que va de la caña al azúcar, al etanol y a la energía, y los públicos que la consultan. Es una
  agroindustria del Valle del Cauca con más de siglo y medio, y negocios de caña, palma, uvas y frutas, camarón y
  mejillón.
- **Público**: el jurado y los invitados de la sustentación, que la ven proyectada o en su teléfono. Los usuarios
  que simula la plataforma son un cliente B2B, un proveedor cañero, un colaborador y una persona del equipo de planta.
- **Tarea principal**: que se entienda en segundos que **un solo agente atiende a cada público** y que su perfil más
  potente **reparte la caña con un optimizador verificable**.

El vocabulario visual sale de la planta, no de un tablero SaaS:

- la caña se corta en tallos con nudos;
- el jugo se separa;
- el azúcar es cristal;
- el etanol es líquido ámbar;
- el bagazo se quema para vapor y electricidad;
- los compromisos se registran en un libro.

## 2. Sistema de tokens

### Color

La base es la paleta verificada de `brand.py`, extraída del logotipo público. Cada color de producto tiene un
significado fijo en toda la plataforma: el mismo color siempre es el mismo producto.

| Token | Hex | Rol |
|---|---|---|
| `--cane` | `#387C2B` | Verde bosque. La caña y la marca: navegación activa y origen del flujo. |
| `--cane-deep` | `#173512` | Verde profundo. Texto sobre claros y fondo del hero y del rail. |
| `--sugar` | `#FFD200` | Amarillo. Azúcar. Solo como relleno, nunca como texto: no da contraste sobre claro. |
| `--ethanol` | `#E86D1F` | Naranja. Etanol y acciones primarias. |
| `--power` | `#B0BC22` | Lima. Energía de cogeneración. |
| `--molasses` | `#F6A01A` | Naranja claro. Miel y alternativas. |
| `--field` | `#F5F7F3` | Fondo de trabajo: blanco verdoso de hoja, **no crema**. |
| `--ink` | `#14240F` | Texto. |
| `--shortfall` | `#B3261E` | Faltante o restricción violada. Solo con significado de alerta. |

Reglas de contraste:

- El texto sobre `--sugar` y `--power` va en `--ink`.
- El blanco solo va sobre `--cane`, `--cane-deep` y `--shortfall`.
- `--ethanol` como fondo de botón lleva texto `--ink` con peso 650, porque blanco sobre naranja no llega a 4,5:1.
- Se verifica con `brand.py` (`ContrastPair`), ampliando sus pares.

### Tipografía

Se usa una sola familia: **Archivo variable**, con ejes de peso y de ancho, servida por fontsource. Reemplaza a
Bricolage Grotesque y Public Sans. **El ancho es el sistema**:

- **Expandida** (`wdth` 112–125, peso 700–800): titulares y nombres de área. Tiene la presencia de una placa de
  maquinaria o de un bulto de azúcar estampado.
- **Normal** (`wdth` 100, peso 400–500): texto corrido y conversación, con interlineado de 1,55.
- **Condensada** (`wdth` 75–85, peso 500–600, `font-variant-numeric: tabular-nums`): cifras de planta, toneladas,
  MWh, margen y tablas. Así las columnas numéricas caben en un teléfono sin monoespaciada.

La escala es modular de razón 1,25 sobre 16 px: 12,8 · 16 · 20 · 25 · 31,25 · 39 · 48,8 px. El titular de la
entrada llega a `clamp(2.75rem, 6vw, 4.75rem)`. La medida del texto corrido es de 66 caracteres como máximo.

Lo que no se hace:

- etiquetas en mayúsculas espaciadas sobre cada título;
- una palabra del titular en otro color o en cursiva;
- monoespaciada para datos;
- flechas «→» pegadas a los botones.

### Forma

El radio tiene jerarquía, no un valor único:

- 2 px para tablas y chips de datos;
- 10 px para paneles;
- forma de píldora solo para el selector de perfil.

No hay sombras grises genéricas. La profundidad viene de capas de color: un panel sobre `--field` es blanco con un
filete de 1 px de `--ink` al 14 %, y la consola usa una banda `--cane-deep`.

### Movimiento

Hay **un solo momento orquestado**: al calcular un plan, las bandas del flujo de caña crecen desde «Caña» hasta su
grosor final en 600 ms. Así se ve qué cambió respecto al plan anterior. Fuera de eso, el movimiento solo responde a
acciones de la persona: abrir la traza o confirmar el guardado. Con `prefers-reduced-motion` las bandas aparecen sin
transición.

## 3. Composición

Todo se alinea a la izquierda, sobre una retícula de 12 columnas en escritorio y de 4 en teléfono.

### Marco de la aplicación

```text
┌──────────┬───────────────────────────────────────────────────────────┐
│ VALER-IA │  Barra superior: área actual · perfil activo · modo demo  │
│          ├───────────────────────────────────────────────────────────┤
│ Entrada  │                                                           │
│ Agente   │                 contenido del área                        │
│ Planif.  │                                                           │
│ Evidencia│                                                           │
│          │                                                           │
│ (tallo)  │  pie: proyecto académico, no afiliado · datos sintéticos  │
└──────────┴───────────────────────────────────────────────────────────┘
```

- El rail izquierdo es `--cane-deep`, con un **tallo de caña** vertical dibujado en SVG cuyos nudos marcan las
  cuatro áreas. El nudo del área activa se rellena de `--cane`. Por eso la navegación es una secuencia visual sin
  números.
- En teléfono, el rail pasa a ser una barra inferior de cuatro destinos.

### Entrada (`/`)

```text
┌─────────────────────────────────────────────────────────────────────┐
│  Un agente para cada persona     [ilustración: tallo que se abre en │
│  que trabaja con Manuelita.       azúcar, etanol, energía, palma,   │
│  texto breve: qué es, qué no es   uva, camarón y mejillón]          │
│  [Hablar con el agente] [Ver la planificación]                      │
├─────────────────────────────────────────────────────────────────────┤
│  ¿Quién eres?  cinco perfiles como filas de un libro de registro:   │
│  pictograma · perfil · qué puede pedir · ejemplo → entra al agente  │
├─────────────────────────────────────────────────────────────────────┤
│  Cómo responde: cita · calcula en código · pide «Sí» · recuerda     │
│  con permiso   (cuatro garantías, con la evidencia enlazada)        │
├─────────────────────────────────────────────────────────────────────┤
│  Módulos 1 y 2: consulta, resumen y FAQ (consola RAG existente)     │
└─────────────────────────────────────────────────────────────────────┘
```

El hero **no** usa un número grande con degradado. Usa un titular en Archivo expandido junto a la ilustración de la
cadena de productos: es lo más característico del tema.

Los perfiles se presentan como **filas de un libro de registro**, no como cinco tarjetas iguales. Cada fila tiene
el pictograma del público, el nombre, lo que puede pedir y una consulta de ejemplo que abre el agente con ese perfil.

### Agente (`/agente`)

```text
┌─────────────────────────────────────┬───────────────────────────────┐
│ selector de perfil (píldoras)       │ Fuentes del turno             │
├─────────────────────────────────────┤  [U1] informe 2024, p. 12     │
│ conversación                        │ Memoria                       │
│ (ChatView actual, re-estilizado)    │  perfil: cliente B2B  [Borrar]│
│ tarjetas de aprobación Sí / No      │ Sugerencias del perfil        │
├─────────────────────────────────────┤                               │
│ campo · micrófono · voz             │                               │
└─────────────────────────────────────┴───────────────────────────────┘
```

En teléfono, el panel derecho se pliega en un cajón que se abre con «Fuentes y memoria».

### Planificación (`/planificacion`): el elemento memorable

```text
┌──────────────────┬──────────────────────────────────────────────────┐
│ Escenario        │  Semana 2026-W48 · Datos sintéticos de           │
│  Caña  [-15 %]   │  demostración                                    │
│  Calidad [12,5]  │                                                  │
│  Precio etanol   │   CAÑA ████████████▶ Azúcar      54 %  41 200 t  │
│  Vapor máx.      │        ██████▶ Etanol           31 %   9 800 m³  │
│  Prioridad       │        ███▶ Energía             15 %   6 100 MWh │
│ [Calcular plan]  │                                                  │
│ [Comparar base]  │  Restricción que limita: molienda (valor 38/t)   │
├──────────────────┤  Alternativa: más energía, −2 % de margen         │
│ Estado de planta │──────────────────────────────────────────────────│
│  molino 92 %     │  Libro de compromisos                            │
│  caldera 100 %   │   Azúcar exportación  ██████████|  cumple +4 %   │
│  inventarios     │   Etanol E10          ████████|    falta 320 m³  │
│                  │  [Explicar con el agente]  [Guardar propuesta]   │
│                  │  El agente recomienda; el equipo de planta decide│
└──────────────────┴──────────────────────────────────────────────────┘
```

- El **flujo de caña** ocupa el centro: bandas con el color de cada producto, cuyo grosor es proporcional a las
  toneladas. Cada banda termina en el pictograma del producto: cristal de azúcar, gota de etanol, rayo sobre bagazo.
- Al comparar, el plan base aparece en contorno detrás del nuevo, y la diferencia se lee en las cifras condensadas.
- En el libro de compromisos, cada barra tiene una marca vertical en el mínimo contratado. Lo que falta se dibuja en
  `--shortfall` con trama diagonal, para que no dependa solo del color.
- Si no hay solución factible, el flujo **no se dibuja**. En su lugar aparece «No hay un plan que cumpla todos los
  compromisos» y la lista de faltantes por prioridad.
- En teléfono, el orden es escenario, flujo, compromisos y estado de planta, y las bandas se giran a vertical: la
  caña cae desde arriba.

### Evidencia (`/evidencia`)

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Servicios: modelo ● · Qdrant ● · WhatsApp ● · gateway ○ (razón)     │
├──────────────────────────────┬──────────────────────────────────────┤
│ Catálogo (26)                │ Traza del último turno               │
│  filtro: lectura/escritura/  │  ruta planning · 4 pasos             │
│  perfil                      │  1 get_plant_state   120 ms ok       │
│  tabla densa, Archivo cond.  │  2 get_commitments    80 ms ok       │
│                              │  3 optimize_plan     310 ms ok       │
│                              │  4 compare           ...             │
├──────────────────────────────┴──────────────────────────────────────┤
│ Evaluaciones publicadas: cifra · meta · fecha · informe (incluye 🟡)│
└─────────────────────────────────────────────────────────────────────┘
```

Los pasos de la traza **sí** son una secuencia, así que se numeran. Nada más en la plataforma lleva números de
sección.

## 4. Ilustraciones de productos

Son pictogramas propios en SVG en línea, de trazo de 1,75 px y color plano de producto. Viven en un solo módulo,
`web/src/components/brand/ProductGlyphs.tsx`:

- **caña**: tallo con tres nudos y hoja;
- **azúcar**: cristal facetado;
- **etanol**: gota con menisco;
- **energía**: rayo sobre un haz de bagazo;
- **miel**: gota densa;
- **palma**: racimo de fruto;
- **uva**: racimo;
- **camarón** y **mejillón**.

No se copian fotos ni piezas de la marca de Manuelita. Los existentes `CaneField` y `ProductMotifs` se reemplazan
por este módulo.

## 5. Revisión del plan frente al brief

Tres partes del primer borrador salían en «modo default». Se cambiaron así:

| Borrador | Por qué era genérico | Cambio |
|---|---|---|
| Hero con un número grande («26 herramientas») y degradado verde–naranja | Es la composición por defecto de cualquier landing de IA | Titular expandido junto a la ilustración de la cadena de productos: el tema habla por sí mismo |
| Cinco tarjetas iguales de perfil con sombra suave y radio de 16 px | Es el kit de tarjetas SaaS | Filas de un libro de registro con pictograma y consulta de ejemplo; la jerarquía la dan el ancho tipográfico y el filete |
| Cifras en una monoespaciada pequeña | Es un tic de interfaz «técnica» | Archivo condensada con cifras tabulares: misma familia y otro ancho, más legible en el proyector |

También se descartó un modo oscuro con un solo acento lima: la sustentación se proyecta en un salón iluminado, y la
paleta de la marca vive sobre claro.

La valentía está en **un solo lugar**: el flujo de caña de la consola, con su eco en el tallo del rail y en la
ilustración de la entrada. Todo lo demás es sobrio.

## 6. Piso de calidad

- AA de contraste en todo el texto.
- Foco visible de 2 px en `--ethanol` con desplazamiento.
- Orden de tabulación lógico y `skip-link`.
- `prefers-reduced-motion` respetado.
- Sin desplazamiento horizontal entre 360 y 1920 px.
- Los gráficos con texto alternativo y una tabla equivalente.
- Errores que dicen qué pasó y qué hacer, sin disculpas.
- Los botones nombran la acción y el aviso repite el verbo: «Guardar propuesta» → «Propuesta guardada».
