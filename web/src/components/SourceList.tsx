import type { Citation } from "../lib/types";
import { citationLocation } from "../lib/format";

export function SourceList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) {
    return null;
  }
  return (
    <div className="sources" data-testid="source-list">
      <h4>Fuentes</h4>
      <ul className="source-list">
        {citations.map((citation) => (
          <li className="source" key={`${citation.label}-${citation.url}`}>
            <a href={citation.url} target="_blank" rel="noreferrer noopener">
              <span className="source-label">[{citation.label}]</span> {citation.title}
            </a>
            <small>
              {citationLocation(citation)} · {citation.authority.replace("_", " ")}
            </small>
          </li>
        ))}
      </ul>
    </div>
  );
}
