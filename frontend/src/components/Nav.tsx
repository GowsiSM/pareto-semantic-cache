import type { Theme } from "../hooks/useTheme";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "#architecture", label: "Architecture", icon: "⌘", tip: "Compare the cache pipelines" },
  { href: "#how-pareto-works", label: "Mechanism", icon: "◇", tip: "See Pareto's two objectives" },
  { href: "#run-experiment", label: "Run", icon: "▶", tip: "Configure and run a backend experiment" },
  { href: "#results", label: "Results", icon: "▦", tip: "View measured cache metrics" },
  { href: "#conclusion", label: "Conclusion", icon: "✦", tip: "Read the data-driven interpretation" },
];

interface NavProps {
  theme: Theme;
  onToggleTheme: () => void;
  onNavigate: (id: string) => void;
}

export function Nav({ theme, onToggleTheme, onNavigate }: NavProps) {
  return (
    <header className="nav">
      <div className="nav-inner">
        <a href="#top" className="nav-brand">
          Semanti<strong>Cache</strong>
        </a>
        <nav className="nav-links" aria-label="Primary navigation">
          {LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              title={link.tip}
              onClick={(event) => {
                event.preventDefault();
                onNavigate(link.href.slice(1));
              }}
            >
              <span className="nav-link-icon" aria-hidden="true">{link.icon}</span>
              <span>{link.label}</span>
              <span className="nav-tooltip" role="tooltip">{link.tip}</span>
            </a>
          ))}
        </nav>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
