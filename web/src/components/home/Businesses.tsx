/**
 * Los negocios de Manuelita sobre los que responde Valer-IA (spec 031): las cuatro plataformas públicas
 * en una rejilla (sin carrusel), cada una con su foto sustituta de licencia libre, sus glifos de producto
 * y una línea. Sin pie de foto: los créditos van en el pie de la página.
 */
import { PHOTOS, photoSrc, photoSrcSet } from "../../data/photos";
import { PLATFORMS, productByKey } from "../../data/products";
import { PRODUCT_GLYPHS } from "../brand/ProductGlyphs";

export function Businesses() {
  return (
    <section aria-labelledby="negocios-title" className="site-section" id="negocios">
      <div className="wrap">
        <div className="sec-head">
          <h2 className="site-h2" id="negocios-title">
            Los negocios de Manuelita que conoce
          </h2>
          <p className="site-lead">Valer-IA responde sobre las cuatro plataformas públicas de Manuelita.</p>
        </div>
        <ul className="businesses">
          {PLATFORMS.map((platform) => {
            const photo = PHOTOS[platform.photo];
            return (
              <li className="businesses__item" data-platform={platform.key} key={platform.key}>
                <div className="photo businesses__photo">
                  <img
                    alt={photo.alt}
                    data-source="stand-in"
                    data-subject={photo.subject}
                    decoding="async"
                    height={525}
                    width={700}
                    loading="lazy"
                    sizes="(min-width: 1024px) 480px, (min-width: 640px) 60vw, 100vw"
                    src={photoSrc(photo.id)}
                    srcSet={photoSrcSet(photo.id)}
                  />
                </div>
                <h3>{platform.name}</h3>
                <p>{platform.line}</p>
                <ul aria-label={`Productos de ${platform.name}`} className="businesses__products">
                  {platform.products.map((key) => {
                    const product = productByKey(key);
                    const Glyph = PRODUCT_GLYPHS[key];
                    return (
                      <li key={key} style={{ "--product": product.color } as React.CSSProperties}>
                        <Glyph size={20} />
                        {product.name}
                      </li>
                    );
                  })}
                </ul>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
