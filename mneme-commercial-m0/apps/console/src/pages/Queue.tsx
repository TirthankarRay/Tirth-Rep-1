import { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { AppContext, ROLE_USERS } from '../App';
import { getQueue, QueueItem } from '../api/queue';

export function Queue() {
  const { user } = useOutletContext<AppContext>();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState<string>(
    ROLE_USERS.find((u) => u.id === user)?.role ?? ''
  );

  useEffect(() => {
    setLoading(true);
    setError(null);
    getQueue(roleFilter || undefined, user)
      .then((r) => setItems(r.proposals))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [user, roleFilter]);

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-3xl font-display text-mneme-text">Review queue</h1>
          <div className="text-mneme-dim font-mono text-sm mt-1">
            Material + attention proposals awaiting co-sign.
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-mneme-dim">Filter by role</label>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-mneme-surface border border-mneme-line text-mneme-text font-mono text-xs rounded px-2 py-1"
          >
            <option value="">All open</option>
            {Array.from(new Set(ROLE_USERS.map((u) => u.role))).map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <div className="card text-mneme-dim">Loading…</div>}
      {error && <div className="card text-mneme-bad">{error}</div>}

      {!loading && items.length === 0 && (
        <div className="card text-mneme-dim">
          No proposals to review. Run <code>make demo</code> from the repo to generate
          some agent traffic.
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-mneme-surface2 text-mneme-dim font-mono uppercase text-xs">
              <tr>
                <th className="text-left px-4 py-2">Title</th>
                <th className="text-left px-4 py-2">Materiality</th>
                <th className="text-left px-4 py-2">Rule</th>
                <th className="text-left px-4 py-2">Agent</th>
                <th className="text-left px-4 py-2">In queue</th>
                <th className="text-left px-4 py-2">SLA remaining</th>
                <th className="text-left px-4 py-2">Co-signers</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr
                  key={it.id}
                  className="border-t border-mneme-line hover:bg-mneme-surface2"
                >
                  <td className="px-4 py-2">
                    <Link
                      to={`/proposal/${it.id}`}
                      className="text-mneme-accent hover:underline font-mono text-xs"
                    >
                      {it.target_path}
                    </Link>
                    <div className="text-mneme-dim text-xs mt-1 max-w-md truncate">
                      {it.rationale}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`chip chip-${it.verdict_label}`}>
                      {it.verdict_label}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-mneme-dim">
                    {it.verdict_rule}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-mneme-dim">
                    {it.agent_id}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-mneme-dim">
                    {it.age_hours.toFixed(1)}h
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">
                    <span
                      className={
                        it.sla_remaining_hours < 0
                          ? 'text-mneme-bad'
                          : it.sla_remaining_hours < 6
                          ? 'text-mneme-warn'
                          : 'text-mneme-dim'
                      }
                    >
                      {it.sla_remaining_hours.toFixed(1)}h
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">
                    {it.roles.map((role, idx) => (
                      <span
                        key={role}
                        className={`mr-1 ${
                          it.signed_offs[idx] ? 'text-mneme-good' : 'text-mneme-dim'
                        }`}
                      >
                        {role}
                        {it.signed_offs[idx] ? '✓' : ''}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
