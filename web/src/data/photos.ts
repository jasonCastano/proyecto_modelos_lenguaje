/**
 * Fotos sustitutas de la entrada (spec 031, research R5): Wikimedia Commons, licencia libre, sin marca
 * de Manuelita ni personas reconocibles. Ilustran los cultivos y productos sobre los que responde
 * Valer-IA; no son fotos de Manuelita. Créditos completos en `public/media/fotos/CREDITOS.md`.
 */
export type PhotoId = "cana" | "cosecha" | "azucar" | "palma" | "uva" | "mejillones";

export const ALLOWED_LICENSES = ["CC0", "Dominio público", "CC BY 2.0", "CC BY-SA 4.0"] as const;

export interface Photo {
  id: PhotoId;
  commons: string;
  alt: string;
  author: string;
  license: (typeof ALLOWED_LICENSES)[number];
  sourceUrl: string;
  subject: string;
  standIn: true;
}

export const PHOTOS: Record<PhotoId, Photo> = {
  cana: {
    id: "cana",
    commons: "f75362180",
    alt: "Surcos de caña de azúcar joven en un campo",
    author: "Thamizhpparithi Maari",
    license: "CC BY-SA 4.0",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:Sugarcane_field_in_Salem.jpg",
    subject: "campo de caña de azúcar",
    standIn: true,
  },
  cosecha: {
    id: "cosecha",
    commons: "f144258619",
    alt: "Plantación de caña con cerros al fondo y caña cortada apilada",
    author: "Don Christie",
    license: "CC BY-SA 4.0",
    sourceUrl:
      "https://commons.wikimedia.org/wiki/File:Sugar_cane_plantation_near_Murwillumbah,_November_1961.jpg",
    subject: "plantación y corte de caña",
    standIn: true,
  },
  azucar: {
    id: "azucar",
    commons: "f111139028",
    alt: "Cristales de azúcar iluminados a contraluz",
    author: "Tobias Erbsland",
    license: "CC BY-SA 4.0",
    sourceUrl:
      "https://commons.wikimedia.org/wiki/File:Granulated_White_Sugar_with_Large_Crystals,_Light_Through_the_Crystals.jpg",
    subject: "cristales de azúcar",
    standIn: true,
  },
  palma: {
    id: "palma",
    commons: "f144703693",
    alt: "Plantación de palma de aceite junto a una carretera",
    author: "Kistara",
    license: "CC0",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:Oil_palm_plantation_in_Paloh_Hinai,_Pahang.jpg",
    subject: "plantación de palma de aceite",
    standIn: true,
  },
  uva: {
    id: "uva",
    commons: "f67603219",
    alt: "Viñedo en otoño al pie de una cordillera",
    author: "South African Tourism",
    license: "CC BY 2.0",
    sourceUrl:
      "https://commons.wikimedia.org/wiki/File:Hex_River_Valley_-_Western_Cape,_South_Africa_(3880658723).jpg",
    subject: "viñedo de uva",
    standIn: true,
  },
  mejillones: {
    id: "mejillones",
    commons: "f3801518",
    alt: "Mejillones adheridos a una roca",
    author: "Wilson44691",
    license: "Dominio público",
    sourceUrl: "https://commons.wikimedia.org/wiki/File:CornishMussels.JPG",
    subject: "mejillones",
    standIn: true,
  },
};

/** Ruta de la foto en el tamaño pedido (700 por defecto, 1400 para pantallas densas). */
export function photoSrc(id: PhotoId, width: 700 | 1400 = 700): string {
  return `/media/fotos/${id}-${width}.webp`;
}

export function photoSrcSet(id: PhotoId): string {
  return `${photoSrc(id, 700)} 700w, ${photoSrc(id, 1400)} 1400w`;
}

/** Línea única de créditos del pie (regla de la skill: una línea, enlace a la lista). */
export const PHOTO_CREDITS_LINE = "Fotografías vía Wikimedia Commons";
export const PHOTO_CREDITS_URL = "/media/fotos/CREDITOS.md";
