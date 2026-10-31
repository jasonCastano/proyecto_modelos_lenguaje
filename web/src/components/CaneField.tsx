export function CaneField() {
  return (
    <svg
      className="cane-field"
      viewBox="0 0 520 620"
      role="img"
      aria-labelledby="cane-field-title"
    >
      <title id="cane-field-title">
        Cañaveral lineal que conecta el campo con la base de conocimiento
      </title>
      <path className="cane-stalk cane-stalk--light" d="M54 588 C64 450 40 314 70 166" />
      <path className="cane-stalk" d="M126 592 C112 450 140 300 122 104" />
      <path className="cane-stalk cane-stalk--light" d="M204 594 C224 468 192 330 214 174" />
      <path className="cane-stalk" d="M292 596 C276 438 310 300 288 88" />
      <path className="cane-stalk cane-stalk--light" d="M382 592 C402 450 366 320 394 144" />
      <path className="cane-stalk" d="M462 590 C446 470 474 342 452 222" />

      <path className="cane-leaf" d="M122 420 C76 390 58 350 46 302" />
      <path className="cane-leaf" d="M124 366 C168 338 190 304 194 258" />
      <path className="cane-leaf" d="M288 350 C238 320 220 278 218 228" />
      <path className="cane-leaf" d="M290 292 C338 268 356 232 354 186" />
      <path className="cane-leaf" d="M452 390 C498 364 512 326 512 278" />
      <path className="cane-leaf" d="M70 268 C106 248 122 218 124 180" />

      <path className="cane-signal" d="M126 540 C190 512 208 476 204 430 C200 386 244 360 288 342 C332 324 354 278 382 238 C408 198 430 174 452 158" />
      <circle className="cane-node" cx="126" cy="540" r="7" />
      <circle className="cane-node" cx="204" cy="430" r="7" />
      <circle className="cane-node" cx="288" cy="342" r="7" />
      <circle className="cane-node" cx="382" cy="238" r="7" />
      <circle className="cane-node" cx="452" cy="158" r="7" />

      <g fill="none" stroke="var(--orange)" strokeWidth="2">
        <path d="M332 96 L354 68 L376 96 L354 124 Z" />
        <path d="M390 148 L404 132 L418 148 L404 164 Z" />
        <path d="M250 178 L262 164 L274 178 L262 192 Z" />
      </g>
      <path
        d="M12 588 C120 574 404 574 508 588"
        fill="none"
        stroke="var(--forest)"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
