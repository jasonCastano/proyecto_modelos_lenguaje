import type { FaqItem } from "../lib/types";
import { statusLabel } from "../lib/format";

export function FaqResults({ items }: { items: FaqItem[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="faq-list" aria-live="polite">
      {items.map((item, index) => (
        <details className="faq-item" key={`${item.question}-${index}`}>
          <summary>{item.question}</summary>
          <div className="faq-body">
            {item.answer}
            <div className="faq-status">
              {statusLabel(item.status)} · {item.model} · prompt {item.prompt_version}
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}
