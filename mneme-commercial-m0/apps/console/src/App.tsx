import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

const NAV = [
  { to: '/queue', label: 'Queue' },
  { to: '/audit', label: 'Audit' },
  { to: '/settings', label: 'Settings' },
];

// No browser storage — identity lives in React state only.
export type AppContext = {
  user: string;
  setUser: (u: string) => void;
};

export const ROLE_USERS: { id: string; role: string; label: string }[] = [
  { id: 'u:brand-lead-brandx', role: 'brand', label: 'Brand Lead' },
  { id: 'u:medical-lead-brandx', role: 'medical', label: 'Medical Lead' },
  { id: 'u:mlr-reviewer', role: 'mlr', label: 'MLR Reviewer' },
  { id: 'u:market-access-lead', role: 'market-access', label: 'Market Access' },
  { id: 'u:legal-lead', role: 'legal', label: 'Legal' },
];

export function App() {
  const loc = useLocation();
  const [user, setUser] = useState<string>(ROLE_USERS[0].id);

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-mneme-line bg-mneme-surface flex flex-col">
        <div className="p-5 border-b border-mneme-line">
          <div className="font-display text-xl text-mneme-accent">Mneme</div>
          <div className="font-mono text-xs text-mneme-dim mt-1">Reviewer Console · M0</div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ to, label }) => {
            const active = loc.pathname.startsWith(to);
            return (
              <Link
                key={to}
                to={to}
                className={`block px-3 py-2 rounded text-sm font-mono uppercase tracking-wider ${
                  active
                    ? 'bg-mneme-surface2 text-mneme-accent'
                    : 'text-mneme-dim hover:text-mneme-text hover:bg-mneme-surface2'
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-mneme-line">
          <div className="card-head">Signed in as</div>
          <select
            className="w-full bg-mneme-bg border border-mneme-line text-mneme-text font-mono text-xs rounded px-2 py-1"
            value={user}
            onChange={(e) => setUser(e.target.value)}
          >
            {ROLE_USERS.map((u) => (
              <option key={u.id} value={u.id}>
                {u.label} ({u.role})
              </option>
            ))}
          </select>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet context={{ user, setUser } satisfies AppContext} />
      </main>
    </div>
  );
}
