import type { Theme } from "../hooks/useTheme";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "#architecture", label: "Architecture" },
  { href: "#how-pareto-works", label: "How Pareto Works" },
  { href: "#run-experiment", label: "Run Experiment" },
  { href: "#results", label: "Results" },
  { href: "#conclusion", label: "Conclusion" },
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
        <nav className="nav-links">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
