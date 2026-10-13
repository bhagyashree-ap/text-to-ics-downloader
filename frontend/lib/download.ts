import { fetchIcs } from "./api";
import type { CalendarEvent } from "./types";

/**
 * Trigger a browser download of a Blob. The file lands in the user's normal
 * Downloads folder: we create a temporary object URL and a hidden <a>, click it,
 * then clean up.
 */
export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function safeFilename(name: string): string {
  const cleaned = name.replace(/[^a-zA-Z0-9 _-]+/g, " ").trim().replace(/\s+/g, "_");
  return cleaned || "events";
}

/** Build one .ics containing all events and download it. */
export async function downloadCalendar(
  events: CalendarEvent[],
  calendarName: string,
  _format: "ics" = "ics"
) {
  const blob = await fetchIcs(events, calendarName);
  triggerDownload(blob, `${safeFilename(calendarName)}.ics`);
}
