"use client";

import { useState } from "react";
import { EventCard } from "@/components/EventCard";
import { extractEvents } from "@/lib/api";
import { downloadCalendar } from "@/lib/download";
import type { CalendarEvent } from "@/lib/types";

const SAMPLE = `Team standup every Monday at 9:30am in Room 4.
Dentist appointment next Friday 2pm, remind me 1 day before.
Project deadline March 20. Flight to NYC on 2026-04-02 7:45am, add a 2 hour reminder.`;

export default function Home() {
  const [text, setText] = useState("");
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [calendarName, setCalendarName] = useState("My Events");
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usedLlm, setUsedLlm] = useState<boolean | null>(null);
  const [extracted, setExtracted] = useState(false);

  const handleExtract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await extractEvents(text);
      setEvents(res.events);
      setUsedLlm(res.used_llm);
      setExtracted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (format: "ics" | "ical") => {
    if (events.length === 0) return;
    setDownloading(true);
    setError(null);
    try {
      await downloadCalendar(events, calendarName, format);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  const updateEvent = (updated: CalendarEvent) =>
    setEvents((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
  const removeEvent = (id: string) =>
    setEvents((prev) => prev.filter((e) => e.id !== id));

  const singleEventGcalLink =
    events.length === 1 ? events[0].google_calendar_link : null;

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Text → Calendar</h1>
        <p className="mt-2 text-slate-500">
          Paste any text with event info. Review, then download a calendar file.
        </p>
      </header>

      {/* Input */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="mb-2 flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700">Paste your text</span>
          <button
            type="button"
            onClick={() => setText(SAMPLE)}
            className="text-xs text-indigo-600 hover:underline"
          >
            Try a sample
          </button>
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={7}
          placeholder="e.g. Lunch with Sam next Tuesday 12:30pm. Remind me 30 minutes before."
          className="w-full resize-y rounded-lg border border-slate-200 p-3 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Emails, chat, spreadsheet rows, notes — all work.
          </span>
          <button
            type="button"
            onClick={handleExtract}
            disabled={loading || !text.trim()}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Extracting…" : "Extract events"}
          </button>
        </div>
      </section>

      {error && (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Review + download */}
      {extracted && (
        <section className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {events.length} event{events.length === 1 ? "" : "s"} found
            </h2>
            {usedLlm !== null && (
              <span className="text-xs text-slate-400">
                {usedLlm ? "Extracted with AI model" : "Extracted with built-in parser"}
              </span>
            )}
          </div>

          {events.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              No events detected. Try adding a date/time, or edit your text.
            </div>
          ) : (
            <div className="space-y-4">
              {events.map((ev) => (
                <EventCard
                  key={ev.id}
                  event={ev}
                  onChange={updateEvent}
                  onRemove={() => removeEvent(ev.id)}
                />
              ))}
            </div>
          )}

          {events.length > 0 && (
            <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <label className="mb-3 block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Calendar name
                </span>
                <input
                  value={calendarName}
                  onChange={(e) => setCalendarName(e.target.value)}
                  className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                />
              </label>

              <p className="mb-2 text-sm font-semibold text-slate-700">Download</p>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => handleDownload("ics")}
                  disabled={downloading}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
                >
                  {downloading ? "Preparing…" : "Download .ics"}
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload("ical")}
                  disabled={downloading}
                  className="rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-400 disabled:opacity-50"
                >
                  Download .ical
                </button>
                {singleEventGcalLink && (
                  <a
                    href={singleEventGcalLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-400"
                  >
                    Add to Google Calendar ↗
                  </a>
                )}
              </div>
              <p className="mt-3 text-xs text-slate-400">
                <strong>.ics</strong> and <strong>.ical</strong> are the same file — pick
                whichever your calendar app expects. The file saves to your Downloads
                folder; open it to add the events (with reminders) to any calendar app.
                {events.length > 1 && " Google Calendar link is available when there's a single event — otherwise import the .ics."}
              </p>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
