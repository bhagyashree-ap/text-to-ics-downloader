"use client";

import { useEffect, useState } from "react";
import { EventCard } from "@/components/EventCard";
import { analyze, detectTimezone, downloadUrl, generateCalendar, uploadDocument } from "@/lib/api";
import type { CanonicalEvent } from "@/lib/types";

export default function Home() {
  const [text, setText] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [events, setEvents] = useState<CanonicalEvent[]>([]);
  const [analyzed, setAnalyzed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<{ id: string; filename: string } | null>(null);
  const [calendarName, setCalendarName] = useState("My Events");

  useEffect(() => setTimezone(detectTimezone()), []);

  const runAnalyze = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setArtifact(null);
    try {
      const result = await analyze({ text, timezone });
      setEvents(result.events);
      setAnalyzed(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not extract events.");
    } finally {
      setLoading(false);
    }
  };

  const onFile = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadDocument(file);
      setText(result.text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the document.");
    } finally {
      setLoading(false);
    }
  };

  const generate = async () => {
    if (!events.length) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generateCalendar(events, [], calendarName);
      setArtifact({ id: result.artifact_id, filename: result.filename });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate the calendar.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">TEXT to ICS download</h1>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <label htmlFor="event-text" className="label">Enter Text</label>
        <textarea
          id="event-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder="Paste text containing your event details…"
          className="input resize-y"
        />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <label className="btn-secondary cursor-pointer">
            Upload document
            <input
              type="file"
              accept=".txt,.eml,.pdf,.docx"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
          </label>
          <button type="button" onClick={runAnalyze} disabled={loading || !text.trim()} className="btn-primary">
            {loading ? "Extracting…" : "Extract"}
          </button>
        </div>
      </section>

      {error && <div role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      {analyzed && (
        <section className="mt-8 space-y-5">
          <p className="text-sm font-medium text-slate-600">{events.length} events</p>

          {events.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              No events found. Try adding a title, date, and time to the text.
            </div>
          ) : (
            <div className="space-y-3">
              {events.map((event) => <EventCard key={event.id} event={event} />)}
            </div>
          )}

          {events.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <label className="mb-4 block text-sm">
                <span className="label">Calendar name</span>
                <input value={calendarName} onChange={(e) => { setCalendarName(e.target.value); setArtifact(null); }} className="input" />
              </label>
              {artifact ? (
                <a href={downloadUrl(artifact.id)} className="btn-primary inline-block" download={artifact.filename}>
                  Download .ics
                </a>
              ) : (
                <button type="button" onClick={generate} disabled={generating} className="btn-primary">
                  {generating ? "Preparing…" : "Download .ics"}
                </button>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
