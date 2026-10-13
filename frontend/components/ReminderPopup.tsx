"use client";

import type { Reminder } from "@/lib/types";

/** Options shown when the text contains no reminder. `null` = no reminder. */
const OPTIONS: { label: string; value: Reminder | null }[] = [
  { label: "No reminder", value: null },
  { label: "At time of event", value: { amount: 0, unit: "minutes" } },
  { label: "10 minutes before", value: { amount: 10, unit: "minutes" } },
  { label: "1 hour before", value: { amount: 1, unit: "hours" } },
  { label: "1 day before", value: { amount: 1, unit: "days" } },
];

export function ReminderPopup({
  eventCount,
  onPick,
  onCancel,
}: {
  eventCount: number;
  onPick: (reminder: Reminder | null) => void;
  onCancel: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-900">Add a reminder?</h2>
        <p className="mt-1 text-sm text-slate-500">
          No reminder was found in your text. Pick one to apply to{" "}
          {eventCount === 1 ? "your event" : `all ${eventCount} events`}.
        </p>

        <div className="mt-4 space-y-2">
          {OPTIONS.map((opt) => (
            <button
              key={opt.label}
              type="button"
              onClick={() => onPick(opt.value)}
              className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700"
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
