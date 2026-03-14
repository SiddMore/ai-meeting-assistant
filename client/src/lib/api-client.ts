const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

type RequestOptions = Omit<RequestInit, "body"> & {
    body?: unknown
    token?: string             // optional Bearer token from NextAuth session
}

async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { body, headers, token, ...rest } = options

    const authHeader: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

    let res: Response;
    try {
        console.log(`[apiFetch] Fetching ${API_BASE}${path} with token: ${token ? "YES" : "NO"}`, { authHeader, restheaders: headers });
        res = await fetch(`${API_BASE}${path}`, {
            // Always send cookies so HTTP-only access/refresh tokens from the FastAPI
            // backend are included on cross-origin requests.
            credentials: "include",
            ...rest,
            headers: {
                "Content-Type": "application/json",
                ...authHeader,
                ...(headers as Record<string, string>),
            },
            body: body !== undefined ? JSON.stringify(body) : undefined,
        })
    } catch (err: any) {
        console.error(`[apiFetch] Network error for ${path}:`, err);
        throw new Error(`Network Error: ${err?.message ?? err} (url=${API_BASE}${path})`);
    }

    if (!res.ok) {
        console.error(`[apiFetch] Error response ${res.status} for ${path}`);
        const error = await res.json().catch(() => ({ detail: `Request failed with status ${res.status}` }))
        throw new Error(error.detail ?? `Request failed with status ${res.status}`)
    }

    if (res.status === 204) return {} as T
    return res.json() as Promise<T>
}

/**
 * createApiClient(token) — returns API objects pre-loaded with a session token.
 * Use this in React components: const api = createApiClient(session?.accessToken)
 */
export function createApiClient(token?: string) {
    const opts = (extra: RequestOptions = {}) => ({ ...extra, token })

    return {
        moms: {
            get: (id: string) => apiFetch<MOMOut>(`/moms/${id}`, opts()),
            list: () => apiFetch<MOMListItem[]>("/moms", opts()),
            search: (q: string) => apiFetch<MOMListItem[]>(`/moms/search?q=${q}`, opts()),
        },
        tasks: {
            updateStatus: (id: string, data: { status: string }) =>
                apiFetch<void>(`/tasks/${id}/status`, opts({ method: "PATCH", body: data })),
            updatePriority: (id: string, data: { priority: string }) =>
                apiFetch<void>(`/tasks/${id}/priority`, opts({ method: "PATCH", body: data })),
            update: (id: string, data: Partial<ActionItem>) =>
                apiFetch<void>(`/tasks/${id}`, opts({ method: "PATCH", body: data })),
            delete: (id: string) =>
                apiFetch<void>(`/tasks/${id}`, opts({ method: "DELETE" })),
        },
        meetings: {
            create: (data: MeetingCreate) =>
                apiFetch<MeetingOut>("/meetings", opts({ method: "POST", body: data })),
            list: () => apiFetch<MeetingListItem[]>("/meetings", opts()),
            get: (id: string) => apiFetch<MeetingOut>(`/meetings/${id}`, opts()),
            delete: (id: string) => apiFetch<void>(`/meetings/${id}`, opts({ method: "DELETE" })),
            getTranscript: (id: string) => apiFetch<TranscriptChunk[]>(`/transcripts/${id}`, opts()),
        },
        simulate: {
            start: (meetingId: string) =>
                apiFetch<unknown>(`/simulate/${meetingId}/start`, opts({ method: "POST" })),
            chunk: (meetingId: string, text: string, speaker?: string) =>
                apiFetch<unknown>(`/simulate/${meetingId}/chunk`, opts({
                    method: "POST",
                    body: { text, speaker: speaker ?? "Speaker 1", language: "en" },
                })),
            end: (meetingId: string) =>
                apiFetch<unknown>(`/simulate/${meetingId}/end`, opts({ method: "POST" })),
        },
        calendar: {
            integrations: () =>
                apiFetch<{ provider: string; connected: boolean; has_calendar_scopes: boolean }[]>(
                    "/integrations/calendar",
                    opts(),
                ),
            disconnect: (provider: string) =>
                apiFetch<{ status: string; provider: string }>(
                    `/integrations/calendar/${provider}/disconnect`,
                    opts({ method: "POST" }),
                ),
            events: (params: { start?: string; end?: string; status?: string; provider?: string } = {}) => {
                const qs = new URLSearchParams()
                if (params.start) qs.set("start", params.start)
                if (params.end) qs.set("end", params.end)
                if (params.status) qs.set("status", params.status)
                if (params.provider) qs.set("provider", params.provider)
                const query = qs.toString() ? `?${qs.toString()}` : ""
                return apiFetch<CalendarEventsResponse>(`/calendar/events${query}`, opts())
            },
        },
    }
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
    register: (data: { email: string; name: string; password: string }) =>
        apiFetch<{ message: string; user: unknown }>("/auth/register", {
            method: "POST",
            body: data,
        }),

    login: (data: { email: string; password: string }) =>
        apiFetch<{ message: string; user: unknown }>("/auth/login", {
            method: "POST",
            body: data,
        }),

    logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),

    refresh: () => apiFetch<{ message: string; user: unknown }>("/auth/refresh", { method: "POST" }),

    me: () => apiFetch<unknown>("/auth/me"),
}

// ── Meetings ───────────────────────────────────────────────────────────────────
export type MeetingCreate = { title?: string; platform: string; meeting_url: string }
export type MeetingOut = {
    id: string; owner_id: string; title: string | null; platform: string
    meeting_url: string; recall_bot_id: string | null; status: string
    started_at: string | null; ended_at: string | null; created_at: string
    participants: { id: string; name: string | null; email: string | null }[]
    transcript?: {
        id: string; content_raw: string | null; content_translated: string | null
        primary_language: string | null; file_url: string | null; audio_url: string | null
        created_at: string
    } | null
}
export type MeetingListItem = Omit<MeetingOut, "participants" | "recall_bot_id" | "owner_id">
export type TranscriptChunk = {
    id: string; speaker: string | null; text: string; language: string | null
    start_time: number | null; created_at: string
}

export type CalendarEvent = {
    id: string
    title: string
    start: string
    end: string
    provider: "google" | "microsoft" | "none"
    status: "todo" | "in_progress" | "done" | "cancelled"
    priority: "low" | "medium" | "high"
    mom_id?: string | null
    action_item_id: string
}

// ── MOM and Tasks ─────────────────────────────────────────────────────────────
export type MOMOut = {
    id: string;
    meeting_id: string;
    summary: string | null;
    key_decisions: string | null;
    full_content: string | null;
    pdf_url: string | null;
    email_sent: boolean;
    sent_at: string | null;
    created_at: string;
    action_items: ActionItemOut[];
    meeting: MeetingDetail;
}

export type ActionItemOut = {
    id: string;
    task: string;
    assignee_name: string | null;
    assignee_email: string | null;
    deadline: string | null;
    status: string;
    priority: string;
    created_at: string;
}

export type MeetingDetail = {
    id: string;
    title: string | null;
    platform: string;
    meeting_url: string;
    created_at: string;
    participants: Participant[];
}

export type Participant = {
    id: string;
    name: string | null;
    email: string | null;
}

export type ActionItem = {
    id: string;
    task: string;
    assignee_name: string | null;
    assignee_email: string | null;
    deadline: string | null;
    status: "todo" | "in_progress" | "done" | "cancelled";
    priority: "low" | "medium" | "high";
    created_at: string;
}

export type MOMListItem = {
    id: string;
    meeting: MeetingListItem;
    summary: string | null;
    created_at: string;
}

export type CalendarEventsResponse = {
    events: CalendarEvent[];
    total: number;
}
