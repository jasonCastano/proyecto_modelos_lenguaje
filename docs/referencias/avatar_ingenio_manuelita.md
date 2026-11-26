---
file: avatar_ingenio_manuelita.png
sha256: dac47b3faccc992731f0d4abdf011ad08e7d53482f8098663b06234410067e7e
origin: ""
rights: ""
real_person: ""
brand_elements: ""
confirmed_by: ""
---

# Ficha de origen: imagen de referencia del video pitch (spec 028)

La imagen `avatar_ingenio_manuelita.png` (941×1672, PNG, sin metadatos) es el primer cuadro de las escenas que
genera MAGI-2 para el video pitch de Valer-IA (`specs/028-video-pitch-magi2/`).

Antes de generar, un integrante debe completar el encabezado (research R10, FR-008):

| Campo | Qué declarar |
|---|---|
| `origin` | Cómo se obtuvo la imagen: herramienta de IA y fecha |
| `rights` | Con qué derechos la usa el equipo |
| `real_person` | `false` si la imagen **no** representa a una persona real identificable |
| `brand_elements` | `false` si **no** contiene el logotipo ni piezas gráficas de Manuelita |
| `confirmed_by` | Integrante que lo declara |

Mientras falte algún campo, o si `real_person` o `brand_elements` no son `false`, `pml pitch validate` falla y no se
monta el video. La constitución (§3.7) exige que el avatar no imite a personas reales ni use la marca de Manuelita.
