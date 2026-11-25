/**
 * Perfiles de la plataforma para la entrada y el agente (spec 026). Las claves son las de
 * `config/profiles.toml`; los textos dicen qué puede pedir cada público, con consultas de ejemplo.
 */
import type { ProductKey } from "../components/brand/ProductGlyphs";

export interface AudienceCard {
  key: string;
  label: string;
  glyph: ProductKey;
  canAsk: string;
  example: string;
  suggestions: string[];
}

export const AUDIENCE_CARDS: AudienceCard[] = [
  {
    key: "visitante",
    label: "Visitante",
    glyph: "cane",
    canAsk: "Qué hace Manuelita, sus negocios, su historia y sus cifras públicas, con fuentes.",
    example: "¿Qué produce Manuelita y en qué países está?",
    suggestions: [
      "¿Qué produce Manuelita y en qué países está?",
      "¿Cuánta energía genera el ingenio con bagazo?",
      "Resume el último informe de sostenibilidad.",
    ],
  },
  {
    key: "cliente",
    label: "Cliente B2B",
    glyph: "sugar",
    canAsk: "Productos, certificaciones y fichas técnicas; una cotización pasa a un asesor con tu «Sí».",
    example: "Compro azúcar para mi empresa, ¿qué certificaciones tienen?",
    suggestions: [
      "Compro azúcar para mi empresa, ¿qué certificaciones tienen?",
      "¿Qué tipos de azúcar y de alcohol ofrecen?",
      "Quiero una cotización de azúcar refinada.",
    ],
  },
  {
    key: "proveedor",
    label: "Proveedor cañero",
    glyph: "cane",
    canAsk: "Programas para proveedores y buenas prácticas publicadas; no reemplaza la asistencia de campo.",
    example: "Soy proveedor de caña, ¿qué programas de apoyo tienen?",
    suggestions: [
      "Soy proveedor de caña, ¿qué programas de apoyo tienen?",
      "¿Qué prácticas de sostenibilidad piden a los proveedores?",
      "¿Cómo se mide la calidad de la caña que entrego?",
    ],
  },
  {
    key: "colaborador",
    label: "Colaborador",
    glyph: "molasses",
    canAsk: "Ética, línea de transparencia, seguridad y salud en el trabajo, según documentos públicos.",
    example: "¿Cómo reporto un caso a la línea ética?",
    suggestions: [
      "¿Cómo reporto un caso a la línea ética?",
      "¿Qué dice la política de seguridad y salud en el trabajo?",
      "¿Qué es el programa de transparencia empresarial?",
    ],
  },
  {
    key: "planificador",
    label: "Planificador industrial",
    glyph: "power",
    canAsk: "El reparto de la caña entre azúcar, etanol y energía con un optimizador, sobre datos sintéticos.",
    example: "Tenemos 15 % menos caña esta semana. ¿Cómo cumplimos azúcar, etanol y energía?",
    suggestions: [
      "Tenemos 15 % menos caña esta semana. ¿Cómo cumplimos azúcar, etanol y energía?",
      "¿Qué pasa si el precio del etanol sube 10 %?",
      "Muéstrame el estado de la planta y los compromisos de la semana.",
    ],
  },
];

export function audienceCard(key: string): AudienceCard {
  return AUDIENCE_CARDS.find((card) => card.key === key) ?? AUDIENCE_CARDS[0];
}
