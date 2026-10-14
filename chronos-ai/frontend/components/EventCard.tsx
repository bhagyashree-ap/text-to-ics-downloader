import type { CanonicalEvent } from "@/lib/types";

function formatEventDate(event: CanonicalEvent): string {
  if (!event.start_date) return "Date not found";
  const [year, month, day] = event.start_date.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  const dateLabel = new Intl.DateTimeFormat(undefined, {
    month: "short", day: "numeric", year: "numeric",
  }).format(date);
  if (event.all_day || !event.start_time) return `${dateLabel} · All day`;

  const [hours, minutes] = event.start_time.split(":").map(Number);
  const time = new Date(year, month - 1, day, hours, minutes);
  const timeLabel = new Intl.DateTimeFormat(undefined, {
    hour: "numeric", minute: "2-digit",
  }).format(time);
  return `${dateLabel} · ${timeLabel}${event.timezone ? ` · ${event.timezone}` : ""}`;
}

export function EventCard({ event }: { event: CanonicalEvent }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">{event.title || "Untitled event"}</h2>
      <p className="mt-1 text-sm text-slate-600">{formatEventDate(event)}</p>
      {event.location && <p className="mt-1 text-sm text-slate-500">{event.location}</p>}
    </article>
  );
}
