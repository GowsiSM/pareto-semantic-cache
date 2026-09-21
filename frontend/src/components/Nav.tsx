import type { Theme } from "../hooks/useTheme";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "#architecture", label: "Architecture", icon: "⌘" },
  { href: "#how-pareto-works", label: "Mechanism", icon: "◇" },
  { href: "#run-experiment", label: "Run", icon: "▶" },
  { href: "#results", label: "Results", icon: "▦" },
  { href: "#conclusion", label: "Conclusion", icon: "✦" },
];

interface NavProps {
  theme: Theme;
  onToggleTheme: () => void;
}

export function Nav({ theme, onToggleTheme }: NavProps) {
  return (
    <header className="nav">
      <div className="nav-inner">
        <a href="#top" className="nav-brand">
          Semanti<strong>Cache</strong>
        </a>
        <nav className="nav-links" aria-label="Primary navigation">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href}>
              <span className="nav-link-icon" aria-hidden="true">{link.icon}</span>
              <span>{link.label}</span>
            </a>
          ))}
        </nav>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
