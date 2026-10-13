"use client";

import type { Reminder, ReminderUnit } from "@/lib/types";

const UNITS: ReminderUnit[] = ["MINUTES", "HOURS", "DAYS", "WEEKS"];

const PRESETS: { label: string; r: Reminder }[] = [
  { label: "At time", r: { amount: 0, unit: "MINUTES", anchor: "START" } },
  { label: "5 min", r: { amount: 5, unit: "MINUTES", anchor: "START" } },
  { label: "10 min", r: { amount: 10, unit: "MINUTES", anchor: "START" } },
  { label: "15 min", r: { amount: 15, unit: "MINUTES", anchor: "START" } },
  { label: "30 min", r: { amount: 30, unit: "MINUTES", anchor: "START" } },
  { label: "1 hour", r: { amount: 1, unit: "HOURS", anchor: "START" } },
  { label: "2 hours", r: { amount: 2, unit: "HOURS", anchor: "START" } },
  { label: "1 day", r: { amount: 1, unit: "DAYS", anchor: "START" } },
  { label: "2 days", r: { amount: 2, unit: "DAYS", anchor: "START" } },
];

export function ReminderEditor({
  reminders,
  onChange,
}: {
  reminders: Reminder[];
  onChange: (r: Reminder[]) => void;
}) {
  const update = (i: number, patch: Partial<Reminder>) => {
    const next = reminders.slice();
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };
  const add = (r: Reminder) => onChange([...reminders, { ...r }]);
  const remove = (i: number) => onChange(reminders.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1">
        <span className="label mb-0 mr-1">Reminders</span>
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => add(p.r)}
            className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600 hover:border-indigo-400 hover:text-indigo-600"
          >
            + {p.label}
          </button>
        ))}
      </div>
      {reminders.length === 0 && <p className="text-xs text-slate-400">No reminders set.</p>}
      {reminders.map((r, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            aria-label="Reminder amount"
            value={r.amount}
            onChange={(e) => update(i, { amount: Math.max(0, Number(e.target.value)) })}
            className="w-16 rounded border border-slate-200 px-2 py-1 text-sm"
          />
          <select
            aria-label="Reminder unit"
            value={r.unit}
            onChange={(e) => update(i, { unit: e.target.value as ReminderUnit })}
            className="rounded border border-slate-200 px-2 py-1 text-sm"
          >
            {UNITS.map((u) => (
              <option key={u} value={u}>
                {u.toLowerCase()}
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
