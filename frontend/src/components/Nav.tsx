const LINKS = [
  { href: "#architecture", label: "Architecture" },
  { href: "#how-pareto-works", label: "How Pareto Works" },
  { href: "#run-experiment", label: "Run Experiment" },
  { href: "#results", label: "Results" },
  { href: "#conclusion", label: "Conclusion" },
];

export function Nav() {
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
      </div>
    </header>
  );
}
