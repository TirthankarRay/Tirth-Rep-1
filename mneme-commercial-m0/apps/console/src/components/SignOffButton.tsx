import { useState } from 'react';

export function SignOffButton({
  myRoles,
  outstandingRoles,
  signedOffRoles,
  onSignOff,
  onReject,
  disabled,
}: {
  myRoles: string[];
  outstandingRoles: string[];
  signedOffRoles: string[];
  onSignOff: (role: string, comment: string) => Promise<void>;
  onReject: (role: string, comment: string) => Promise<void>;
  disabled?: boolean;
}) {
  const canSignRoles = myRoles.filter((r) => outstandingRoles.includes(r));
  const [comment, setComment] = useState('');
  const [pending, setPending] = useState(false);
  const [role, setRole] = useState(canSignRoles[0] ?? '');
  const [msg, setMsg] = useState<string | null>(null);

  const alreadySigned = myRoles.filter((r) => signedOffRoles.includes(r));

  if (canSignRoles.length === 0) {
    return (
      <div className="card">
        <div className="card-head">Sign-off</div>
        <div className="text-xs text-mneme-dim">
          You have no outstanding sign-off responsibility on this proposal.
        </div>
        {alreadySigned.length > 0 && (
          <div className="text-xs text-mneme-good mt-2 font-mono">
            ✓ You signed as: {alreadySigned.join(', ')}
          </div>
        )}
      </div>
    );
  }

  async function go(action: 'approve' | 'reject') {
    if (!role) return;
    setPending(true);
    setMsg(null);
    try {
      if (action === 'approve') {
        await onSignOff(role, comment);
        setMsg('Signed off.');
      } else {
        await onReject(role, comment || 'Rejected by reviewer.');
        setMsg('Rejected.');
      }
      setComment('');
    } catch (e) {
      setMsg(`Failed: ${e}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="card">
      <div className="card-head">Sign-off</div>
      <div className="space-y-2">
        {canSignRoles.length > 1 && (
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full bg-mneme-bg border border-mneme-line text-mneme-text font-mono text-xs rounded px-2 py-1"
          >
            {canSignRoles.map((r) => (
              <option key={r} value={r}>
                Sign as: {r}
              </option>
            ))}
          </select>
        )}
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          placeholder="Sign-off rationale (optional for approve, required for reject)"
          className="w-full bg-mneme-bg border border-mneme-line text-mneme-text text-xs rounded px-2 py-1"
        />
        <div className="flex gap-2">
          <button
            disabled={pending || disabled}
            onClick={() => go('approve')}
            className="btn btn-primary disabled:opacity-50"
          >
            Approve as {role}
          </button>
          <button
            disabled={pending || disabled || !comment.trim()}
            onClick={() => go('reject')}
            className="btn disabled:opacity-50"
          >
            Reject
          </button>
        </div>
        {msg && <div className="text-xs font-mono text-mneme-dim">{msg}</div>}
      </div>
    </div>
  );
}
