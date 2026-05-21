// Tiny fetch wrapper. Identity passes via X-Mneme-User; no browser storage.

export async function api<T>(
  path: string,
  user: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Mneme-User': user,
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    throw new Error(`${path} → HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}
