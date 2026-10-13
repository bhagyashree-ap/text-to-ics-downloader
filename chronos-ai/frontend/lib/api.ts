import type {
  AnalyzeResponse,
  CanonicalEvent,
  ClarificationQuestion,
  GenerateResponse,
  Reminder,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function analyze(input: {
  text: string;
  email_subject?: string;
  sender?: string;
  input_type?: string;
  timezone: string;
}): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>("/api/v1/analyze", { locale: "en-US", ...input });
}

export function validateEvents(events: CanonicalEvent[]): Promise<{ events: CanonicalEvent[] }> {
  return post("/api/v1/validate", { events });
}

export function applyClarifications(
  events: CanonicalEvent[],
  answers: { question_id: string; event_id: string; field: string; answer: string }[]
): Promise<{ events: CanonicalEvent[] }> {
  return post("/api/v1/clarifications", { events, answers });
}

export function generateCalendar(
  events: CanonicalEvent[],
  defaultReminders: Reminder[],
  calendarName: string
): Promise<GenerateResponse> {
  return post<GenerateResponse>("/api/v1/calendar/generate", {
    events,
    default_reminders: defaultReminders,
    calendar_name: calendarName,
  });
}

export async function uploadDocument(file: File): Promise<{ text: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  return res.json();
}

export function downloadUrl(artifactId: string): string {
  return `${API_BASE}/api/v1/calendar/download/${artifactId}`;
}

export type { ClarificationQuestion };
