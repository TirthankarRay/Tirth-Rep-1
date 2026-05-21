import { useEffect, useState } from 'react';
import { Link, useOutletContext, useParams } from 'react-router-dom';
import { AppContext, ROLE_USERS } from '../App';
import { getProposal, ProposalDetail, reject, signOff } from '../api/proposal';
import { DiffViewer } from '../components/DiffViewer';
import { ProvenanceCard } from '../components/ProvenanceCard';
import { RuleTraceCard } from '../components/RuleTraceCard';
import { SignOffButton } from '../components/SignOffButton';

export function Proposal() {
  const { id = '' } = useParams();
  const { user } = useOutletContext<AppContext>();
  const [data, setData] = useState<ProposalDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    if (!id) return;
    getProposal(id, user)
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, [id, user, refreshTick]);

  if (err) return <div className="p-8 card text-mneme-bad">{err}</div>;
  if (!data) return <div className="p-8 text-mneme-dim">Loading…</div>;

  const myRoles = ROLE_USERS.find((u) => u.id === user)
    ? [ROLE_USERS.find((u) => u.id === user)!.role]
    : [];
  const outstanding = data.review_queue.filter((q) => !q.signed_off).map((q) => q.role);
  const signedOff = data.review_queue.filter((q) => q.signed_off).map((q) => q.role);

  return (
    <div className="p-8 max-w-7xl">
      <div className="mb-4 text-mneme-dim font-mono text-xs">
        <Link to="/queue" className="hover:text-mneme-accent">← Queue</Link>
        <span className="mx-2">/</span>
        <span>{data.id}</span>
      </div>
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display text-mneme-text">{data.target_path}</h1>
          <div className="text-mneme-dim font-mono text-xs mt-1">
            Branch: {data.branch}
            {data.target?.type && (
              <span className="ml-3">Type: {data.target.type}</span>
            )}
            <span className="ml-3">Agent: {data.agent_id}</span>
            <span className="ml-3">State: {data.state}</span>
          </div>
        </div>
        <span className={`chip chip-${data.verdict.label}`}>{data.verdict.label}</span>
      </div>

      <div className="card mb-4">
        <div className="card-head">Rationale</div>
        <div className="text-sm">{data.rationale || '(no rationale)'}</div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 space-y-4">
          <DiffViewer blocks={data.diff_blocks} />
          <RuleTraceCard
            rule={data.verdict.rule}
            label={data.verdict.label}
            trace={data.verdict.trace}
          />
        </div>
        <div className="col-span-1 space-y-4">
          <ProvenanceCard
            sources={data.sources}
            owners={data.target?.frontmatter?.owners}
          />
          <SignOffButton
            myRoles={myRoles}
            outstandingRoles={outstanding}
            signedOffRoles={signedOff}
            onSignOff={async (role, comment) => {
              await signOff(data.id, role, comment, user);
              setRefreshTick((t) => t + 1);
            }}
            onReject={async (role, comment) => {
              await reject(data.id, role, comment, user);
              setRefreshTick((t) => t + 1);
            }}
            disabled={data.state !== 'needs_review'}
          />
          <div className="card">
            <div className="card-head">Review queue</div>
            <ul className="text-xs font-mono space-y-1">
              {data.review_queue.map((q) => (
                <li key={q.role} className={q.signed_off ? 'text-mneme-good' : 'text-mneme-dim'}>
                  {q.signed_off ? '✓' : '·'} {q.role}
                  {q.signed_by && <span className="ml-2">by {q.signed_by}</span>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
