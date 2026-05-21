import { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { AppContext } from '../App';
import { AuditEvent, getAudit } from '../api/audit';

const EVENT_TYPES = ['', 'read', 'propose', 'approve', 'reject', 'merge', 'reject_validate'];

export function Audit() {
  const { user } = useOutletContext<AppContext>();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [type, setType] = useState('');
  const [subject, setSubject] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    getAudit({ event_type: type || undefined, subject: subject || undefined }, user)
      .then((r) => setEvents(r.events))
      .catch((e) => setError(String(e)));
  }, [type, subject, user]);

  return (
    <div className="p-8 max-w-7xl">
      <h1 className="text-3xl font-display text-mneme-text">Audit</h1>
      <div className="text-mneme-dim font-mono text-sm mt-1 mb-6">
        Append-only event log. Hash-chained immutability arrives in M3.
      </div>
      <div className="flex gap-3 mb-4 items-end">
        <div>
          <div className="card-head">Event type</div>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="bg-mneme-surface border border-mneme-line text-mneme-text font-mono text-xs rounded px-2 py-1"
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t || 'all'}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="card-head">Subject (substring not supported)</div>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="u:brand-lead-brandx"
            className="bg-mneme-surface border border-mneme-line text-mneme-text font-mono text-xs rounded px-2 py-1"
          />
        </div>
      </div>

      {error && <div className="card text-mneme-bad">{error}</div>}

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-mneme-surface2 text-mneme-dim font-mono uppercase text-xs">
            <tr>
              <th className="text-left px-3 py-2">When</th>
              <th className="text-left px-3 py-2">Type</th>
              <th className="text-left px-3 py-2">Subject</th>
              <th className="text-left px-3 py-2">Target</th>
              <th className="text-left px-3 py-2">Metadata</th>
            </tr>
          </thead>
          <tbody>
            {events.map((ev) => (
              <tr key={ev.id} className="border-t border-mneme-line">
                <td className="px-3 py-2 font-mono text-xs text-mneme-dim">
                  {new Date(ev.occurred_at).toLocaleString()}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{ev.event_type}</td>
                <td className="px-3 py-2 font-mono text-xs text-mneme-dim">{ev.subject}</td>
                <td className="px-3 py-2 font-mono text-xs">{ev.target ?? '—'}</td>
                <td className="px-3 py-2 font-mono text-xs text-mneme-dim max-w-md truncate">
                  {JSON.stringify(ev.metadata)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
