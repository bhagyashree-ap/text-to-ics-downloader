import type { CalendarEvent, ExtractResponse } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

/** Guess the user's IANA timezone + locale from the browser. */
export function getUserContext() {
  const timezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
      : "UTC";
  const locale =
    typeof navigator !== "undefined" ? navigator.language || "en-US" : "en-US";
  return { timezone, locale };
}

export async function extractEvents(text: string): Promise<ExtractResponse> {
  const { timezone, locale } = getUserContext();
  const res = await fetch(`${API_BASE}/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, timezone, locale }),
  });
  if (!res.ok) {
    throw new Error(`Extraction failed (${res.status}): ${await res.text()}`);
  }
  return res.json();
}

/** Fetch the .ics file from the backend as a Blob. */
export async function fetchIcs(
  events: CalendarEvent[],
  calendarName: string
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/ics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ events, calendar_name: calendarName }),
  });
  if (!res.ok) {
    throw new Error(`ICS build failed (${res.status}): ${await res.text()}`);
  }
  return res.blob();
}
