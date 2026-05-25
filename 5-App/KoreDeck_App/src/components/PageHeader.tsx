// =============================================================================
// PageHeader.tsx — En-tête de page (mono label + titre + slot droit)
// =============================================================================

interface Props {
  title:     string;
  subtitle?: string;
  right?:    React.ReactNode;
}

export function PageHeader({ title, subtitle, right }: Props) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-end", justifyContent: "space-between",
      padding: "16px 28px 18px",
    }}>
      <div>
        <div className="kd-mono">KORE DECK · {title.toUpperCase()}</div>
        <h1 style={{
          margin: "4px 0 0", fontSize: 32, fontWeight: 600,
          letterSpacing: "-0.035em", color: "var(--text-1)",
        }}>{title}</h1>
        {subtitle && (
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-3)" }}>
            {subtitle}
          </p>
        )}
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}
