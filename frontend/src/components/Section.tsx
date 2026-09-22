import type { ReactNode } from "react";

interface SectionProps {
  id: string;
  eyebrow?: string;
  title: string;
  description?: string;
  children: ReactNode;
  expanded?: boolean;
}

export function Section({ id, eyebrow, title, description, children, expanded = true }: SectionProps) {
  return (
    <section id={id} className={`section ${expanded ? "is-expanded" : "is-collapsed"}`}>
      <div className="section-header">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {description && <p className="section-description">{description}</p>}
      </div>
      {expanded && <div className="section-body">{children}</div>}
    </section>
  );
}
