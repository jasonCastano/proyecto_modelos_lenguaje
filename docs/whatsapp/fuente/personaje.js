/*
 * Valer-IA en caricatura (spec 030, stickers). Ilustración vectorial propia dibujada en código: la
 * presentadora de la imagen de referencia (pelo oscuro ondulado, chaqueta verde, camisa blanca,
 * aretes dorados) en estilo de caricatura de los años 50 (contorno negro grueso, colores planos,
 * guiño, insignia redonda y borde blanco troquelado). Toma el estilo, no el personaje de otra obra.
 * Sin modelos generativos ni red. Colores corporativos de las portadas (base.css).
 */
(function () {
  const C = {
    ink: "#1b1a17",
    skin: "#efb98f",
    blush: "#e8836f",
    hair: "#3b2418",
    hairHi: "#5c3a26",
    jacket: "#497536",
    jacketHi: "#5f8f48",
    shirt: "#ffffff",
    gold: "#f3b21b",
    badge: "#d64729",
    badgeHi: "#e2603f",
    orange: "#f39200",
    yellow: "#ffd100",
    green: "#497536",
  };
  const S = `stroke="${C.ink}" stroke-linejoin="round" stroke-linecap="round"`;

  // --- partes del personaje en una caja de 300×300; la insignia es el círculo (150, 150) r 140 ---
  function hairBack() {
    return `
      <path class="hair-back" d="M150 22 C 98 20 64 58 68 108 C 70 132 58 146 64 166 C 54 182 62 200 74 210 C 66 222 74 236 90 240 C 100 232 106 220 108 206 L 192 206 C 194 220 200 232 210 240 C 226 236 234 222 226 210 C 238 200 246 182 236 166 C 242 146 230 132 232 108 C 236 58 202 20 150 22 Z" fill="${C.hair}" ${S} stroke-width="5"/>
      <path d="M74 150 C 66 170 76 188 70 204 M226 150 C 234 170 224 188 230 204" fill="none" stroke="${C.hairHi}" stroke-width="4" stroke-linecap="round"/>`;
  }
  function torso() {
    return `
      <path d="M58 302 C 60 244 96 208 150 204 C 204 208 240 244 242 302 Z" fill="${C.jacket}" ${S} stroke-width="5"/>
      <path d="M86 250 C 96 232 112 220 126 214" fill="none" stroke="${C.jacketHi}" stroke-width="6" stroke-linecap="round"/>
      <path d="M121 207 L150 266 L179 207 Z" fill="${C.shirt}" ${S} stroke-width="4"/>
      <path d="M121 207 L138 252 L120 236 L112 214 Z" fill="${C.shirt}" ${S} stroke-width="4"/>
      <path d="M179 207 L162 252 L180 236 L188 214 Z" fill="${C.shirt}" ${S} stroke-width="4"/>
      <path d="M116 212 L142 262 L126 302" fill="none" ${S} stroke-width="4"/>
      <path d="M184 212 L158 262 L174 302" fill="none" ${S} stroke-width="4"/>`;
  }
  function neck() {
    return `<path d="M134 168 L134 206 Q150 218 166 206 L166 168 Z" fill="${C.skin}" ${S} stroke-width="4"/>`;
  }
  function face(eyes) {
    const openL = `<ellipse class="eye eye-l" cx="131" cy="116" rx="5.5" ry="8" fill="${C.ink}"/>`;
    const openR = `<ellipse class="eye eye-r" cx="169" cy="116" rx="5.5" ry="8" fill="${C.ink}"/>`;
    const winkR = `<path d="M160 118 Q169 109 178 118" fill="none" ${S} stroke-width="4.5"/>`;
    const happyL = `<path d="M122 118 Q131 109 140 118" fill="none" ${S} stroke-width="4.5"/>`;
    const happyR = `<path d="M160 118 Q169 109 178 118" fill="none" ${S} stroke-width="4.5"/>`;
    const lookUpL = `<ellipse class="eye eye-l" cx="133" cy="112" rx="5.5" ry="8" fill="${C.ink}"/>`;
    const lookUpR = `<ellipse class="eye eye-r" cx="171" cy="112" rx="5.5" ry="8" fill="${C.ink}"/>`;
    const eyeSet = {
      open: openL + openR,
      wink: openL + winkR,
      happy: happyL + happyR,
      up: lookUpL + lookUpR,
    }[eyes || "open"];
    const browUp = eyes === "up" ? -4 : 0;
    return `
      <ellipse cx="102" cy="132" rx="9" ry="13" fill="${C.skin}" ${S} stroke-width="4"/>
      <ellipse cx="198" cy="132" rx="9" ry="13" fill="${C.skin}" ${S} stroke-width="4"/>
      <ellipse cx="150" cy="120" rx="49" ry="58" fill="${C.skin}" ${S} stroke-width="5"/>
      <circle class="earring" cx="100" cy="150" r="6" fill="${C.gold}" ${S} stroke-width="3"/>
      <circle class="earring" cx="200" cy="150" r="6" fill="${C.gold}" ${S} stroke-width="3"/>
      <path d="M119 ${99 + browUp} Q130 ${91 + browUp} 142 ${97 + browUp}" fill="none" ${S} stroke-width="4.5"/>
      <path d="M158 ${97 + browUp} Q170 ${91 + browUp} 181 ${99 + browUp}" fill="none" ${S} stroke-width="4.5"/>
      ${eyeSet}
      <path d="M150 118 Q144 134 152 138" fill="none" ${S} stroke-width="3.5"/>
      <circle cx="121" cy="140" r="8" fill="${C.blush}" opacity="0.45"/>
      <circle cx="179" cy="140" r="8" fill="${C.blush}" opacity="0.45"/>
      <path d="M126 148 Q150 174 174 148 Q150 160 126 148 Z" fill="${C.shirt}" ${S} stroke-width="4.5"/>
      <path d="M131 152 Q150 168 169 152" fill="none" stroke="#c9584f" stroke-width="2.5" stroke-linecap="round"/>`;
  }
  function hairFront() {
    return `
      <path d="M98 116 C 92 70 120 42 156 42 C 194 42 214 70 206 116 C 200 98 192 86 182 78 C 170 90 148 92 128 86 C 114 92 104 102 98 116 Z" fill="${C.hair}" ${S} stroke-width="4.5"/>
      <path d="M128 86 C 140 66 162 56 186 60" fill="none" stroke="${C.hairHi}" stroke-width="4.5" stroke-linecap="round"/>
      <path d="M118 64 C 128 54 142 50 156 50" fill="none" stroke="${C.hairHi}" stroke-width="4" stroke-linecap="round"/>`;
  }

  // --- brazos (fuera del recorte de la insignia) ---
  function armThumb() {
    return `
      <g class="arm-thumb">
        <path d="M84 232 C 60 218 40 204 26 190 L 44 168 C 58 184 78 198 100 208 Z" fill="${C.jacket}" ${S} stroke-width="5"/>
        <path d="M30 186 L 46 170 L 40 166 L 22 182 Z" fill="${C.shirt}" ${S} stroke-width="3.5"/>
        <g class="thumb">
          <rect x="-12" y="148" width="48" height="42" rx="15" fill="${C.skin}" ${S} stroke-width="5"/>
          <path d="M-10 161 H32 M-10 174 H32" fill="none" ${S} stroke-width="3"/>
          <path d="M6 151 C 2 128 4 108 16 106 C 28 104 31 120 28 151 Z" fill="${C.skin}" ${S} stroke-width="5"/>
        </g>
      </g>`;
  }
  function armWave() {
    return `
      <g class="arm-wave">
        <path d="M216 232 C 240 214 256 192 266 170 L 244 158 C 236 180 220 200 200 212 Z" fill="${C.jacket}" ${S} stroke-width="5"/>
        <path d="M262 172 L 244 160 L 248 154 L 268 166 Z" fill="${C.shirt}" ${S} stroke-width="3.5"/>
        <g class="hand">
          <path d="M248 156 C 238 140 238 118 246 104 L 250 80 C 252 72 262 74 261 82 L 259 104 L 264 74 C 266 66 276 68 275 76 L 271 104 L 278 80 C 280 72 290 74 288 82 L 282 108 L 290 92 C 293 85 302 89 299 96 L 288 128 C 284 146 272 158 260 160 Z" fill="${C.skin}" ${S} stroke-width="4.5"/>
          <path d="M248 120 C 238 114 230 116 230 124 C 232 132 240 136 248 138" fill="${C.skin}" ${S} stroke-width="4.5"/>
        </g>
      </g>`;
  }
  function armThink() {
    return `
      <g class="arm-think">
        <path d="M214 236 C 226 222 224 204 206 192 L 190 206 C 202 214 202 224 196 232 Z" fill="${C.jacket}" ${S} stroke-width="5"/>
        <path d="M206 192 C 196 180 180 174 168 176 C 160 178 160 188 168 190 L 186 192 C 176 194 170 202 176 208 C 184 214 198 206 206 196 Z" fill="${C.skin}" ${S} stroke-width="4.5"/>
        <path d="M168 176 C 166 166 172 160 178 164" fill="${C.skin}" ${S} stroke-width="4"/>
      </g>`;
  }

  function character({ pose = "neutral", eyes = "open" } = {}) {
    const arms = { pulgar: armThumb(), saludo: armWave(), pensando: armThink(), neutral: "" }[pose];
    return `
      <defs>
        <clipPath id="badge-clip"><circle cx="150" cy="150" r="140"/></clipPath>
      </defs>
      <circle cx="150" cy="150" r="140" fill="${C.badge}" ${S} stroke-width="6"/>
      <path d="M44 96 A 120 120 0 0 1 118 32" fill="none" stroke="${C.badgeHi}" stroke-width="10" stroke-linecap="round"/>
      ${hairBack()}
      ${neck()}
      <g clip-path="url(#badge-clip)">${torso()}</g>
      <g class="head">
        ${face(eyes)}
        ${hairFront()}
      </g>
      ${arms}`;
  }

  // --- extras animables ---
  const extras = {
    sparkles: () => `
      <g class="sparkle s1"><path d="M0 -16 L4 -4 L16 0 L4 4 L0 16 L-4 4 L-16 0 L-4 -4 Z" fill="${C.yellow}" ${S} stroke-width="3"/></g>
      <g class="sparkle s2"><path d="M0 -12 L3 -3 L12 0 L3 3 L0 12 L-3 3 L-12 0 L-3 -3 Z" fill="${C.orange}" ${S} stroke-width="3"/></g>
      <g class="sparkle s3"><path d="M0 -10 L2.5 -2.5 L10 0 L2.5 2.5 L0 10 L-2.5 2.5 L-10 0 L-2.5 -2.5 Z" fill="${C.yellow}" ${S} stroke-width="3"/></g>`,
    heart: () => `
      <g class="heart h1"><path d="M0 8 C -14 -2 -18 -14 -10 -20 C -4 -24 0 -18 0 -14 C 0 -18 4 -24 10 -20 C 18 -14 14 -2 0 8 Z" fill="${C.badge}" ${S} stroke-width="3.5"/></g>
      <g class="heart h2"><path d="M0 8 C -14 -2 -18 -14 -10 -20 C -4 -24 0 -18 0 -14 C 0 -18 4 -24 10 -20 C 18 -14 14 -2 0 8 Z" fill="${C.orange}" ${S} stroke-width="3.5"/></g>`,
    question: () => `
      <g class="question">
        <circle r="34" fill="#ffffff" ${S} stroke-width="5"/>
        <text y="16" text-anchor="middle" font-family="Archivo" font-weight="900" font-size="48" fill="${C.badge}">?</text>
      </g>`,
    sun: () => {
      let rays = "";
      // Rayos como líneas con coordenadas calculadas: sin transform, que fill-box desplazaría.
      for (let i = 0; i < 12; i++) {
        const a = (i * Math.PI) / 6;
        const [x1, y1, x2, y2] = [42 * Math.cos(a), 42 * Math.sin(a), 60 * Math.cos(a), 60 * Math.sin(a)];
        rays += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${C.ink}" stroke-width="13" stroke-linecap="round"/>`;
        rays += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${C.yellow}" stroke-width="7" stroke-linecap="round"/>`;
      }
      return `<g class="sun"><g class="rays"><circle r="61" fill="none" stroke="none"/>${rays}</g><circle r="34" fill="${C.yellow}" ${S} stroke-width="5"/><path d="M-14 4 Q0 18 14 4" fill="none" ${S} stroke-width="4"/><circle cx="-11" cy="-6" r="3.5" fill="${C.ink}"/><circle cx="11" cy="-6" r="3.5" fill="${C.ink}"/></g>`;
    },
    thought: () => `
      <g class="thought">
        <circle class="t1" cx="0" cy="0" r="9" fill="#ffffff" ${S} stroke-width="4"/>
        <circle class="t2" cx="22" cy="-26" r="13" fill="#ffffff" ${S} stroke-width="4"/>
        <g class="t3"><ellipse cx="62" cy="-70" rx="44" ry="32" fill="#ffffff" ${S} stroke-width="5"/>
          <circle class="d1" cx="44" cy="-70" r="6" fill="${C.ink}"/><circle class="d2" cx="62" cy="-70" r="6" fill="${C.ink}"/><circle class="d3" cx="80" cy="-70" r="6" fill="${C.ink}"/></g>
      </g>`,
    check: () => `
      <g class="check"><circle r="40" fill="${C.green}" ${S} stroke-width="6"/>
        <path class="tick" d="M-18 0 L-5 14 L20 -14" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" pathLength="100"/></g>`,
  };

  // --- catálogo de stickers: pose, ojos, texto y extras con su posición en el lienzo de 512 ---
  const STICKERS = {
    pulgar: { pose: "pulgar", eyes: "wink", big: true, extras: [["sparkles", 120, 120]] },
    bienvenido: { pose: "neutral", eyes: "open", text: ["¡Bienvenido!"], extras: [["sparkles", 256, 120]] },
    "gracias-confianza": { pose: "neutral", eyes: "happy", text: ["¡Gracias", "por confiar", "en nosotros!"], extras: [["heart", 420, 120]] },
    consulta: { pose: "neutral", eyes: "open", text: ["¿Cuál es", "tu consulta?"], extras: [["question", 418, 92]] },
    hola: { pose: "saludo", eyes: "open", text: ["Hola"], extras: [] },
    "lindo-dia": { pose: "neutral", eyes: "wink", text: ["Lindo día"], extras: [["sun", 420, 92]] },
    gracias: { pose: "neutral", eyes: "happy", text: ["¡Gracias!"], extras: [["heart", 96, 120]] },
    pensando: { pose: "pensando", eyes: "up", text: ["Pensando"], extras: [["thought", 372, 96]] },
    listo: { pose: "pulgar", eyes: "wink", text: ["¡Listo!"], extras: [["check", 420, 100]] },
  };

  const DIE = `
    <filter id="die" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">
      <feGaussianBlur in="SourceAlpha" stdDeviation="7" result="b2"/>
      <feComponentTransfer in="b2" result="m2"><feFuncA type="linear" slope="14" intercept="-0.6"/></feComponentTransfer>
      <feFlood flood-color="#000000" flood-opacity="0.18"/><feComposite in2="m2" operator="in" result="edge"/>
      <feGaussianBlur in="SourceAlpha" stdDeviation="6" result="b1"/>
      <feComponentTransfer in="b1" result="m1"><feFuncA type="linear" slope="14" intercept="-0.6"/></feComponentTransfer>
      <feFlood flood-color="#ffffff"/><feComposite in2="m1" operator="in" result="white"/>
      <feMerge><feMergeNode in="edge"/><feMergeNode in="white"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>`;

  function sticker(id) {
    const cfg = STICKERS[id];
    // Insignia según cuántas líneas de texto lleve; el texto cabe en 440 px de ancho.
    const lines = cfg.text || [];
    const layout = cfg.big
      ? { cx: 282, cy: 262, r: 196 }
      : [
          null,
          { cx: 256, cy: 192, r: 146, cap: 74, first: 430 },
          { cx: 256, cy: 172, r: 128, cap: 62, first: 382 },
          { cx: 256, cy: 152, r: 112, cap: 54, first: 340 },
        ][lines.length];
    const { cx, cy, r } = layout;
    const s = r / 140;
    const ox = cx - 150 * s;
    const oy = cy - 150 * s;
    let text = "";
    if (lines.length) {
      const longest = Math.max(...lines.map((l) => l.length));
      const size = Math.min(layout.cap, Math.floor(440 / (longest * 0.6)));
      text = `<g class="caption">${lines
        .map(
          (line, i) =>
            `<text x="256" y="${layout.first + i * (size + 4)}" text-anchor="middle" font-family="Archivo" font-weight="850" font-size="${size}" fill="${C.ink}" stroke="#ffffff" stroke-width="10" paint-order="stroke" stroke-linejoin="round">${line}</text>`,
        )
        .join("")}</g>`;
    }
    const extra = (cfg.extras || [])
      .map(([name, x, y]) => `<g transform="translate(${x} ${y})"><g class="extra-${name}">${extras[name]()}</g></g>`)
      .join("");
    return `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
        <defs>${DIE}</defs>
        <g filter="url(#die)">
          <g class="figure" transform="translate(${ox} ${oy}) scale(${s})">
            <g class="bob">${character(cfg)}</g>
          </g>
          ${extra}
          ${text}
        </g>
      </svg>`;
  }

  // Insignia sola (sin texto ni borde troquelado) para las tarjetas del bot.
  function badge({ pose = "neutral", eyes = "open", size = 300 } = {}) {
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-30 -6 360 326" width="${size}" height="${(size * 326) / 360}">${character({ pose, eyes })}</svg>`;
  }

  window.ValerIA = { sticker, badge, STICKERS, C };
})();
