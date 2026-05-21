type Source = { ref: string; date?: string; kind: string };

export function ProvenanceCard({ sources, owners }: { sources: Source[]; owners?: string[] }) {
  return (
    <div className="card">
      <div className="card-head">Provenance</div>
      <div className="text-xs font-mono text-mneme-dim mb-1">Sources</div>
      {sources?.length ? (
        <ul className="space-y-1 mb-3">
          {sources.map((s, i) => (
            <li key={i} className="text-xs">
              <span className="chip mr-2">{s.kind}</span>
              <span className="text-mneme-dim mr-2">{s.date ?? '—'}</span>
              <span className="font-mono text-mneme-text break-all">{s.ref}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="text-xs text-mneme-bad mb-3">No sources cited.</div>
      )}
      {owners && owners.length > 0 && (
        <>
          <div className="text-xs font-mono text-mneme-dim mb-1 mt-3">Owners</div>
          <ul className="text-xs font-mono text-mneme-text">
            {owners.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
