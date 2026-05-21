type Block = { section: string; before: string; after: string; unified: string };

export function DiffViewer({ blocks }: { blocks: Block[] }) {
  if (!blocks?.length) {
    return <div className="card text-mneme-dim">No diff blocks.</div>;
  }
  return (
    <div className="space-y-4">
      {blocks.map((b, i) => (
        <div key={i} className="card">
          <div className="card-head">
            ## {b.section}
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div>
              <div className="text-mneme-dim mb-1">before</div>
              <pre className="bg-mneme-bg border border-mneme-line rounded p-2 whitespace-pre-wrap text-mneme-dim min-h-24">
                {b.before || '(empty)'}
              </pre>
            </div>
            <div>
              <div className="text-mneme-accent mb-1">after</div>
              <pre className="bg-mneme-bg border border-mneme-accent rounded p-2 whitespace-pre-wrap text-mneme-text min-h-24">
                {b.after || '(empty)'}
              </pre>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
