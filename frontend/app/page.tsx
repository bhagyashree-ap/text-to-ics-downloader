"use client";

import { useState } from "react";
import { ReminderPopup } from "@/components/ReminderPopup";
import { extractEvents } from "@/lib/api";
import { downloadCalendar } from "@/lib/download";
import type { CalendarEvent, Reminder } from "@/lib/types";

const SAMPLE = `Team standup every Monday at 9:30am in Room 4.
Dentist appointment next Friday 2pm, remind me 1 day before.
Flight to NYC on 2026-04-02 7:45am.`;

export default function Home() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Events held while we wait for the user's reminder choice in the popup.
  const [pendingEvents, setPendingEvents] = useState<CalendarEvent[] | null>(null);

  const anyReminderInText = (events: CalendarEvent[]) =>
    events.some((e) => e.reminders.length > 0);

  const buildAndDownload = async (events: CalendarEvent[]) => {
    await downloadCalendar(events, "My Events", "ics");
  };

  const handleDownloadClick = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await extractEvents(text);
      if (res.events.length === 0) {
        setError("No events found in the text. Add a date or time and try again.");
        return;
      }
      if (anyReminderInText(res.events)) {
        // Reminder(s) already in the text — download straight away.
        await buildAndDownload(res.events);
      } else {
        // Nothing in the text — ask once via the popup.
        setPendingEvents(res.events);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const handlePickReminder = async (reminder: Reminder | null) => {
    const events = pendingEvents ?? [];
    setPendingEvents(null);
    setBusy(true);
    setError(null);
    try {
      const withReminder = events.map((e) => ({
        ...e,
        reminders: reminder ? [reminder] : [],
      }));
      await buildAndDownload(withReminder);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-4 py-12">
      <header className="mb-6 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Text → Calendar</h1>
        <p className="mt-2 text-slate-500">
          Paste text with event details and download a calendar file.
        </p>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700">Your text</span>
          <button
            type="button"
            onClick={() => setText(SAMPLE)}
            className="text-xs text-indigo-600 hover:underline"
          >
            Try a sample
          </button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder="Paste an email, chat message, spreadsheet rows, or notes mentioning one or more events…"
          className="w-full resize-y rounded-lg border border-slate-200 p-3 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />

        <button
          type="button"
          onClick={handleDownloadClick}
          disabled={busy || !text.trim()}
          className="mt-4 w-full rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Working…" : "Download .ics"}
        </button>

        {error && (
          <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        <p className="mt-3 text-center text-xs text-slate-400">
          All events go into one .ics file, saved to your Downloads folder. Open it to
          add them to any calendar app.
        </p>
      </div>

      {pendingEvents && (
        <ReminderPopup
          eventCount={pendingEvents.length}
          onPick={handlePickReminder}
          onCancel={() => setPendingEvents(null)}
        />
      )}
    </main>
  );
}
