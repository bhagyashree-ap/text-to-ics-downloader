"use client";

import type { CalendarEvent, Reminder } from "@/lib/types";
import { ReminderEditor } from "./ReminderEditor";

/** Convert an ISO value into the value a datetime-local / date input expects. */
function toInputValue(iso: string | null, allDay: boolean): string {
  if (!iso) return "";
  if (allDay) return iso.slice(0, 10);
  // datetime-local wants "YYYY-MM-DDTHH:mm"
  return iso.slice(0, 16);
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.8
      ? "bg-emerald-100 text-emerald-700"
      : value >= 0.5
      ? "bg-amber-100 text-amber-700"
      : "bg-rose-100 text-rose-700";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      {pct}% confident
    </span>
  );
}

export function EventCard({
  event,
  onChange,
  onRemove,
}: {
  event: CalendarEvent;
  onChange: (e: CalendarEvent) => void;
  onRemove: () => void;
}) {
  const set = (patch: Partial<CalendarEvent>) => onChange({ ...event, ...patch });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start gap-2">
        <input
          value={event.title}
          onChange={(e) => set({ title: e.target.value })}
          placeholder="Event title"
          className="flex-1 rounded border border-slate-200 px-3 py-2 text-base font-semibold"
        />
        <ConfidenceBadge value={event.confidence} />
        <button
          type="button"
          onClick={onRemove}
          className="rounded px-2 py-1 text-xs text-slate-400 hover:text-rose-600"
          title="Remove event"
        >
          ✕
        </button>
      </div>

      {event.warnings.length > 0 && (
        <ul className="mb-3 space-y-1 rounded bg-amber-50 p-2 text-xs text-amber-800">
          {event.warnings.map((w, i) => (
            <li key={i}>⚠ {w}</li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Start
          </span>
          <input
            type={event.all_day ? "date" : "datetime-local"}
            value={toInputValue(event.start, event.all_day)}
            onChange={(e) => set({ start: e.target.value || null })}
            className="w-full rounded border border-slate-200 px-2 py-1.5"
          />
        </label>

        {!event.all_day && (
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
              End
            </span>
            <input
              type="datetime-local"
              value={toInputValue(event.end, false)}
              onChange={(e) => set({ end: e.target.value || null })}
              className="w-full rounded border border-slate-200 px-2 py-1.5"
            />
          </label>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={event.all_day}
            onChange={(e) => set({ all_day: e.target.checked })}
          />
          All day
        </label>
        <span className="text-xs text-slate-400">Timezone: {event.timezone}</span>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Location
          </span>
          <input
            value={event.location ?? ""}
            onChange={(e) => set({ location: e.target.value || null })}
            placeholder="Room, address…"
            className="w-full rounded border border-slate-200 px-2 py-1.5"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Link
          </span>
          <input
            value={event.url ?? ""}
            onChange={(e) => set({ url: e.target.value || null })}
            placeholder="Zoom / Meet / Teams"
            className="w-full rounded border border-slate-200 px-2 py-1.5"
          />
        </label>
      </div>

      {event.recurrence_phrase && (
        <p className="mt-3 text-xs text-indigo-600">
          🔁 Repeats: {event.recurrence_phrase}
          {event.rrule ? ` (${event.rrule})` : ""}
        </p>
      )}

      <div className="mt-4 border-t border-slate-100 pt-3">
        <ReminderEditor
          reminders={event.reminders}
          onChange={(reminders: Reminder[]) => set({ reminders })}
        />
      </div>

      {event.source_text && (
        <details className="mt-3 text-xs text-slate-400">
          <summary className="cursor-pointer select-none">Show source text</summary>
          <pre className="mt-1 whitespace-pre-wrap rounded bg-slate-50 p-2">
            {event.source_text}
          </pre>
        </details>
      )}
    </div>
  );
}
