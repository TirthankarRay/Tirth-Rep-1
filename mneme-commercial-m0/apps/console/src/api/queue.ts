import { api } from './client';

export type QueueItem = {
  id: string;
  target_path: string;
  agent_id: string;
  rationale: string;
  verdict_label: 'material' | 'attention' | 'routine' | 'reject';
  verdict_rule: string;
  state: string;
  created_at: string;
  roles: string[];
  signed_offs: boolean[];
  age_hours: number;
  sla_remaining_hours: number;
};

export type QueueResponse = { count: number; proposals: QueueItem[] };

export function getQueue(role: string | undefined, user: string) {
  const qs = role ? `?role=${encodeURIComponent(role)}` : '';
  return api<QueueResponse>(`/api/queue${qs}`, user);
}
