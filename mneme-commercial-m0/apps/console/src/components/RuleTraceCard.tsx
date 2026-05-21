type Trace = { rule: string; matched: boolean; reason: string };

export function RuleTraceCard({
  rule,
  label,
  trace,
}: {
  rule: string;
  label: string;
  trace: Trace[];
}) {
  return (
    <div className="card">
      <div className="card-head">Materiality verdict</div>
      <div className="flex items-baseline gap-3 mb-3">
        <span className={`chip chip-${label}`}>{label}</span>
        <span className="font-mono text-sm text-mneme-text">{rule}</span>
      </div>
      <div className="card-head mt-4">Rule trace</div>
      <ul className="text-xs font-mono space-y-1">
        {trace.map((t, i) => (
          <li
            key={i}
            className={t.matched ? 'text-mneme-accent' : 'text-mneme-dim'}
          >
            <span className="mr-2">{t.matched ? '✓' : '·'}</span>
            <span className="mr-2">{t.rule}</span>
            <span className="text-mneme-dim">{t.reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
