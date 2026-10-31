import type { EvidenceLink } from "../lib/types";

export function EvidenceLinks({ links }: { links: EvidenceLink[] }) {
  if (links.length === 0) {
    return null;
  }
  return (
    <div className="story-evidence">
      {links.map((link) => (
        <a href={link.href} key={`${link.kind}-${link.href}`}>
          {link.label} ↗
        </a>
      ))}
    </div>
  );
}
