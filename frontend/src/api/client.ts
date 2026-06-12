import type {
  HealthStatus,
  OrchestratorRequest,
  OrchestratorResult,
  PendingItem,
  SessionSummary,
  SessionHistory,
} from "@/types/api";

const BASE = "http://localhost:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch(`${BASE}/health`).then((r) => json<HealthStatus>(r)),

  orchestrate: (body: OrchestratorRequest) =>
    fetch(`${BASE}/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<OrchestratorResult>(r)),

  listPending: () =>
    fetch(`${BASE}/pending`).then((r) => json<PendingItem[]>(r)),

  approvePending: (id: string) =>
    fetch(`${BASE}/pending/${id}/approve`, { method: "POST" }).then((r) =>
      json<{ status: string; id: string }>(r)
    ),

  rejectPending: (id: string) =>
    fetch(`${BASE}/pending/${id}/reject`, { method: "POST" }).then((r) =>
      json<{ status: string; id: string }>(r)
    ),

  editDraft: ({ id, draft }: { id: string; draft: DraftReply }) =>
    fetch(`${BASE}/pending/${id}/draft`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    }).then((r) => json<{ status: string; id: string }>(r)),

  listSessions: () =>
    fetch(`${BASE}/sessions`).then((r) => json<SessionSummary[]>(r)),

  getSessionHistory: (sessionId: string) =>
    fetch(`${BASE}/sessions/${sessionId}/history`).then((r) =>
      json<SessionHistory>(r)
    ),
};
