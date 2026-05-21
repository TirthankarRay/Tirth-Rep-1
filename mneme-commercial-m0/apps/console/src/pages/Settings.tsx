import { useOutletContext } from 'react-router-dom';
import { AppContext } from '../App';

export function Settings() {
  const { user } = useOutletContext<AppContext>();
  return (
    <div className="p-8 max-w-3xl space-y-4">
      <h1 className="text-3xl font-display text-mneme-text">Settings</h1>
      <div className="card">
        <div className="card-head">Active identity</div>
        <div className="font-mono text-sm">{user}</div>
        <div className="text-xs text-mneme-dim mt-2">
          Switch identities from the sidebar dropdown. M0 simulates SSO via the
          <code className="font-mono mx-1">X-Mneme-User</code> header. OAuth 2.1 +
          OIDC federation belong to M3.
        </div>
      </div>
      <div className="card">
        <div className="card-head">Vault</div>
        <div className="text-sm">commercial-onco-brandx · US</div>
        <div className="text-xs text-mneme-dim mt-2">
          Rule pack: <span className="font-mono">commercial-mlr-strict</span>
        </div>
      </div>
      <div className="card">
        <div className="card-head">M0 limitations</div>
        <ul className="text-xs text-mneme-dim list-disc list-inside space-y-1">
          <li>Section-level ABAC redaction is M1.</li>
          <li>Hash-chained immutable audit is M3.</li>
          <li>OAuth / OIDC SSO is M3.</li>
          <li>Source connectors (Veeva, IQVIA) are M2.</li>
          <li>See <code className="font-mono">docs/future-work.md</code>.</li>
        </ul>
      </div>
    </div>
  );
}
