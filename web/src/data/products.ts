/**
 * Productos y plataformas de Manuelita (spec 031, data-model): un color y un glifo fijos por producto en
 * toda la plataforma. Nombres como los presenta el sitio oficial; glifos propios, sin piezas de la marca.
 */
import type { ProductKey } from "../components/brand/ProductGlyphs";
import type { PhotoId } from "./photos";

export interface Product {
  key: Exclude<ProductKey, "shrimp">;
  name: string;
  platform: PlatformKey;
  /** Variable CSS de tokens.css. */
  color: string;
}

export type PlatformKey = "cana" | "palma" | "frutas" | "acuicultura";

export const PRODUCTS: Product[] = [
  { key: "cane", name: "Caña de azúcar", platform: "cana", color: "var(--cane)" },
  { key: "sugar", name: "Azúcar", platform: "cana", color: "var(--sugar)" },
  { key: "ethanol", name: "Bioetanol", platform: "cana", color: "var(--ethanol)" },
  { key: "power", name: "Energía renovable", platform: "cana", color: "var(--power)" },
  { key: "molasses", name: "Miel", platform: "cana", color: "var(--molasses)" },
  { key: "palm", name: "Palma de aceite", platform: "palma", color: "var(--palm)" },
  { key: "grape", name: "Uva de mesa", platform: "frutas", color: "var(--grape)" },
  { key: "mussel", name: "Mejillones", platform: "acuicultura", color: "var(--mussel)" },
];

export interface Platform {
  key: PlatformKey;
  name: string;
  line: string;
  photo: PhotoId;
  products: Product["key"][];
}

/** Las cuatro plataformas de negocio públicas de Manuelita (copy.md, negocios). */
export const PLATFORMS: Platform[] = [
  {
    key: "cana",
    name: "Caña de azúcar",
    line: "Azúcar, bioetanol y energía renovable, en Colombia y Perú.",
    photo: "cana",
    products: ["cane", "sugar", "ethanol", "power"],
  },
  {
    key: "palma",
    name: "Palma de aceite",
    line: "Aceite de palma y biodiésel, en Colombia.",
    photo: "palma",
    products: ["palm"],
  },
  {
    key: "frutas",
    name: "Frutas y hortalizas",
    line: "Uva de mesa y hortalizas, en Perú.",
    photo: "uva",
    products: ["grape"],
  },
  {
    key: "acuicultura",
    name: "Acuicultura",
    line: "Mejillones, en Chile.",
    photo: "mejillones",
    products: ["mussel"],
  },
];

export function productByKey(key: Product["key"]): Product {
  const product = PRODUCTS.find((item) => item.key === key);
  if (!product) throw new Error(`Producto desconocido: ${key}`);
  return product;
}
