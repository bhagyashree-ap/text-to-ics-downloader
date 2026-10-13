import { fetchIcs } from "./api";
import type { CalendarEvent } from "./types";

/**
 * Trigger a browser download of a Blob. The file lands in the user's normal
 * Downloads folder. We create a temporary object URL and a hidden <a> that we
 * programmatically click, then clean up.
 */
export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoke on the next tick so the download has started.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function safeFilename(name: string): string {
  const cleaned = name.replace(/[^a-zA-Z0-9 _-]+/g, " ").trim().replace(/\s+/g, "_");
  return cleaned || "events";
}

export type CalendarFormat = "ics" | "ical";

/**
 * Download the events as a calendar file. `.ics` and `.ical` are the same
 * iCalendar content — only the file extension differs.
 */
export async function downloadCalendar(
  events: CalendarEvent[],
  calendarName: string,
  format: CalendarFormat
) {
  const blob = await fetchIcs(events, calendarName);
  // Re-type the blob with the right extension's MIME-friendly name.
  const filename = `${safeFilename(calendarName)}.${format}`;
  triggerDownload(blob, filename);
}
