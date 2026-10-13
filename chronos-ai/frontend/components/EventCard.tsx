"use client";

import type { CanonicalEvent, Reminder } from "@/lib/types";
import { ReminderEditor } from "./ReminderEditor";

const CATEGORIES = [
  "MEETING", "EXAM", "DEADLINE", "APPOINTMENT", "TRAVEL",
  "HOLIDAY", "CLASS", "ANNOUNCEMENT", "OTHER",
];

function StatusBadge({ status }: { status: CanonicalEvent["validation_status"] }) {
  const map: Record<string, string> = {
    VALID: "bg-emerald-100 text-emerald-700",
    VALID_WITH_WARNINGS: "bg-amber-100 text-amber-700",
    REQUIRES_CLARIFICATION: "bg-sky-100 text-sky-700",
    INVALID: "bg-rose-100 text-rose-700",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${map[status]}`}>
      {status.replace(/_/g, " ").toLowerCase()}
    </span>
  );
}

export function EventCard({
  event,
  selected,
  onToggleSelect,
  onChange,
  onDelete,
  onDuplicate,
}: {
  event: CanonicalEvent;
  selected: boolean;
  onToggleSelect: () => void;
  onChange: (e: CanonicalEvent) => void;
  onDelete: () => void;
  onDuplicate: () => void;
}) {
  const set = (patch: Partial<CanonicalEvent>) => onChange({ ...event, ...patch });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
          aria-label="Select event"
          className="h-4 w-4"
        />
        <input
          value={event.title}
          onChange={(e) => set({ title: e.target.value })}
          placeholder="Event title"
          className="flex-1 rounded border border-slate-200 px-3 py-2 text-base font-semibold"
        />
        <StatusBadge status={event.validation_status} />
        <button type="button" onClick={onDuplicate} className="text-xs text-slate-500 hover:text-indigo-600" title="Duplicate">⎘</button>
        <button type="button" onClick={onDelete} className="text-xs text-slate-400 hover:text-rose-600" title="Delete">✕</button>
      </div>

      {event.issues.length > 0 && (
        <ul className="mb-3 space-y-1 rounded bg-amber-50 p-2 text-xs">
          {event.issues.map((iss, i) => (
            <li key={i} className={iss.severity === "ERROR" ? "text-rose-700" : "text-amber-800"}>
              {iss.severity === "ERROR" ? "✖" : "⚠"} {iss.message}
            </li>
          ))}
        </ul>
      )}
      {event.ambiguity_flags.length > 0 && (
        <ul className="mb-3 space-y-1 rounded bg-sky-50 p-2 text-xs text-sky-800">
          {event.ambiguity_flags.map((f, i) => (<li key={i}>❔ {f}</li>))}
        </ul>
      )}

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="label">Category</span>
          <select value={event.category} onChange={(e) => set({ category: e.target.value })} className="input">
            {CATEGORIES.map((c) => (<option key={c} value={c}>{c.toLowerCase()}</option>))}
          </select>
        </label>
        <label className="flex items-end gap-2 pb-1 text-sm text-slate-600">
          <input type="checkbox" checked={event.all_day} onChange={(e) => set({ all_day: e.target.checked })} />
          All day
        </label>

        <label className="text-sm">
          <span className="label">Start date</span>
          <input type="date" value={event.start_date ?? ""} onChange={(e) => set({ start_date: e.target.value || null })} className="input" />
        </label>
        {!event.all_day && (
          <label className="text-sm">
            <span className="label">Start time</span>
            <input type="time" value={event.start_time?.slice(0, 5) ?? ""} onChange={(e) => set({ start_time: e.target.value ? `${e.target.value}:00` : null })} className="input" />
          </label>
        )}

        <label className="text-sm">
          <span className="label">End date</span>
          <input type="date" value={event.end_date ?? ""} onChange={(e) => set({ end_date: e.target.value || null })} className="input" />
        </label>
        {!event.all_day && (
          <label className="text-sm">
            <span className="label">End time</span>
            <input type="time" value={event.end_time?.slice(0, 5) ?? ""} onChange={(e) => set({ end_time: e.target.value ? `${e.target.value}:00` : null })} className="input" />
          </label>
        )}

        <label className="text-sm">
          <span className="label">Timezone</span>
          <input value={event.timezone} onChange={(e) => set({ timezone: e.target.value })} className="input" />
        </label>
        <label className="text-sm">
          <span className="label">Location</span>
          <input value={event.location ?? ""} onChange={(e) => set({ location: e.target.value || null })} className="input" />
        </label>
      </div>

      <label className="mt-3 block text-sm">
        <span className="label">Description</span>
        <textarea value={event.description ?? ""} onChange={(e) => set({ description: e.target.value || null })} rows={2} className="input" />
      </label>

      <div className="mt-4 border-t border-slate-100 pt-3">
        <ReminderEditor reminders={event.reminders} onChange={(reminders: Reminder[]) => set({ reminders })} />
      </div>
    </div>
  );
}
