"use client";

import type { Reminder, ReminderUnit } from "@/lib/types";

const UNITS: ReminderUnit[] = ["minutes", "hours", "days", "weeks"];

const PRESETS: { label: string; reminder: Reminder }[] = [
  { label: "At time", reminder: { amount: 0, unit: "minutes" } },
  { label: "10 min", reminder: { amount: 10, unit: "minutes" } },
  { label: "1 hour", reminder: { amount: 1, unit: "hours" } },
  { label: "1 day", reminder: { amount: 1, unit: "days" } },
];

export function ReminderEditor({
  reminders,
  onChange,
}: {
  reminders: Reminder[];
  onChange: (reminders: Reminder[]) => void;
}) {
  const update = (i: number, patch: Partial<Reminder>) => {
    const next = reminders.slice();
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };
  const remove = (i: number) => onChange(reminders.filter((_, idx) => idx !== i));
  const add = (r: Reminder) => onChange([...reminders, r]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Reminders
        </span>
        <div className="flex flex-wrap gap-1">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => add({ ...p.reminder })}
              className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600 hover:border-indigo-400 hover:text-indigo-600"
            >
              + {p.label}
            </button>
          ))}
        </div>
      </div>

      {reminders.length === 0 && (
        <p className="text-xs text-slate-400">No reminders. Add one above.</p>
      )}

      {reminders.map((r, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            value={r.amount}
            onChange={(e) => update(i, { amount: Math.max(0, Number(e.target.value)) })}
            className="w-16 rounded border border-slate-200 px-2 py-1 text-sm"
          />
          <select
            value={r.unit}
            onChange={(e) => update(i, { unit: e.target.value as ReminderUnit })}
            className="rounded border border-slate-200 px-2 py-1 text-sm"
          >
            {UNITS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
          <span className="text-sm text-slate-500">before</span>
          <button
            type="button"
            onClick={() => remove(i)}
            className="ml-auto text-xs text-rose-500 hover:text-rose-700"
          >
            Remove
          </button>
        </div>
      ))}
    </div>
  );
}
