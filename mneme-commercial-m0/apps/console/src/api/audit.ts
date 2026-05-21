import { api } from './client';

export type AuditEvent = {
  id: number;
  event_type: string;
  subject: string;
  target: string | null;
  metadata: any;
  occurred_at: string;
};

export function getAudit(filters: { event_type?: string; subject?: string }, user: string) {
  const qs = new URLSearchParams();
  if (filters.event_type) qs.set('event_type', filters.event_type);
  if (filters.subject) qs.set('subject', filters.subject);
  const suffix = qs.toString() ? `?${qs}` : '';
  return api<{ count: number; events: AuditEvent[] }>(`/api/audit${suffix}`, user);
}
