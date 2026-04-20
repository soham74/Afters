export const ORCHESTRATOR_BASE =
  process.env.NEXT_PUBLIC_ORCHESTRATOR_BASE_URL ?? "http://localhost:8000";
export const MESSAGING_BASE =
  process.env.NEXT_PUBLIC_MESSAGING_BASE_URL ?? "http://localhost:3001";

export class UnreachableError extends Error {
  constructor(url: string, cause?: unknown) {
    super(`cannot reach ${url}. is the service running?`);
    this.name = "UnreachableError";
    (this as any).cause = cause;
  }
}

async function _fetch<T>(url: string, init?: RequestInit): Promise<T> {
  // Only attach Content-Type when we actually have a body. This keeps GETs as
  // CORS-simple requests (no preflight), which reduces the failure surface when
  // the backend is slow to boot or reload.
  const hasBody = init?.body != null;
  const headers: Record<string, string> = {
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  if (hasBody && !("Content-Type" in headers)) {
    headers["Content-Type"] = "application/json";
  }

  let resp: Response;
  try {
    resp = await fetch(url, {
      cache: "no-store",
      ...init,
      headers,
    });
  } catch (err) {
    // `TypeError: Failed to fetch` lands here: DNS miss, connection refused,
    // CORS preflight blocked. We surface a clearer message so the callsite can
    // render a "service unreachable" state instead of dumping a stack trace.
    throw new UnreachableError(url, err);
  }

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`HTTP ${resp.status} ${resp.statusText}: ${text}`);
  }
  return resp.json();
}

// Orchestrator
export const api = {
  listSessions: (params: { state?: string; campus?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.state) qs.set("state", params.state);
    if (params.campus) qs.set("campus", params.campus);
    return _fetch<any[]>(`${ORCHESTRATOR_BASE}/api/sessions?${qs}`);
  },
  getSession: (id: string) =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/sessions/${id}`),
  listTraces: (params: {
    kind?: string;
    agent_name?: string;
    session_id?: string;
    limit?: number;
    sort?: string;
    direction?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return _fetch<any[]>(`${ORCHESTRATOR_BASE}/api/traces?${qs}`);
  },
  metrics: () => _fetch<any>(`${ORCHESTRATOR_BASE}/api/metrics`),
  listScenarios: () => _fetch<any[]>(`${ORCHESTRATOR_BASE}/api/scenarios/`),
  triggerScenario: (name: string) =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/scenarios/${name}`, { method: "POST" }),
  resetDemo: () =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/admin/reset`, { method: "POST" }),
  startLiveSession: () =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/sessions/live`, { method: "POST" }),
  getActiveSession: (userId: string) =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/users/${userId}/active_session`),
  listClosureReviews: (status?: string) => {
    const qs = status ? `?status=${status}` : "";
    return _fetch<any[]>(`${ORCHESTRATOR_BASE}/api/closure${qs}`);
  },
  approveClosure: (id: string) =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/closure/${id}/approve`, {
      method: "POST",
    }),
  editClosure: (id: string, edited_message: string) =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/closure/${id}/edit`, {
      method: "POST",
      body: JSON.stringify({ edited_message }),
    }),
  rejectClosure: (id: string) =>
    _fetch<any>(`${ORCHESTRATOR_BASE}/api/closure/${id}/reject`, {
      method: "POST",
    }),
  thread: (userId: string, sessionId?: string) => {
    const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return _fetch<any[]>(`${ORCHESTRATOR_BASE}/api/messages/${userId}${qs}`);
  },
  listUsers: () => _fetch<any[]>(`${ORCHESTRATOR_BASE}/api/users`),
  getUser: (id: string) => _fetch<any>(`${ORCHESTRATOR_BASE}/api/users/${id}`),
};

// Messaging
export const messaging = {
  reply: (payload: { user_id: string; body: string; session_id?: string | null }) =>
    _fetch<any>(`${MESSAGING_BASE}/messages/reply`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  threads: () => _fetch<Array<{ user_id: string; last_at: string }>>(
    `${MESSAGING_BASE}/messages/threads`,
  ),
};
