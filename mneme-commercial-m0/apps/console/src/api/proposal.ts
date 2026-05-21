import { api } from './client';

export type ProposalDetail = {
  id: string;
  branch: string;
  target_path: string;
  target_id: string | null;
  agent_id: string;
  rationale: string;
  verdict: {
    label: string;
    rule: string;
    trace: { rule: string; matched: boolean; reason: string }[];
  };
  sources: { ref: string; date?: string; kind: string }[];
  diff_blocks: {
    section: string;
    before: string;
    after: string;
    unified: string;
  }[];
  review_queue: {
    role: string;
    signed_off: boolean;
    signed_by: string | null;
    signed_at: string | null;
    comment: string | null;
  }[];
  state: string;
  created_at: string;
  decided_at: string | null;
  target: { id: string; path: string; type: string; title: string; frontmatter: any } | null;
};

export function getProposal(id: string, user: string) {
  return api<ProposalDetail>(`/api/proposals/${id}`, user);
}

export function signOff(id: string, role: string, comment: string, user: string) {
  return api<{ ok: boolean; complete: boolean }>(`/api/proposals/${id}/signoff`, user, {
    method: 'POST',
    body: JSON.stringify({ role, comment }),
  });
}

export function reject(id: string, role: string, comment: string, user: string) {
  return api<{ ok: boolean }>(`/api/proposals/${id}/reject`, user, {
    method: 'POST',
    body: JSON.stringify({ role, comment }),
  });
}
