"use client";

import { useEffect, useMemo, useState } from "react";
import { EventCard } from "@/components/EventCard";
import { ClarificationPanel } from "@/components/ClarificationPanel";
import {
  analyze,
  applyClarifications,
  detectTimezone,
  downloadUrl,
  generateCalendar,
  uploadDocument,
  validateEvents,
} from "@/lib/api";
import type { CanonicalEvent, ClarificationQuestion, Reminder } from "@/lib/types";

const SAMPLE = `Subject: Fall schedule

Team meeting on October 20, 2026 from 2 PM to 3 PM in Room 4.
Research paper due November 12, 2026 at 11:59 PM, remind me 1 day before.
Company holiday on December 25, 2026.`;

const DEFAULT_REMINDER_OPTIONS: { label: string; value: Reminder | null }[] = [
  { label: "None", value: null },
  { label: "At time", value: { amount: 0, unit: "MINUTES", anchor: "START" } },
  { label: "10 min before", value: { amount: 10, unit: "MINUTES", anchor: "START" } },
  { label: "1 hour before", value: { amount: 1, unit: "HOURS", anchor: "START" } },
  { label: "1 day before", value: { amount: 1, unit: "DAYS", anchor: "START" } },
];

export default function Home() {
  const [text, setText] = useState("");
  const [subject, setSubject] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [defaultReminderIdx, setDefaultReminderIdx] = useState(0);

  const [events, setEvents] = useState<CanonicalEvent[]>([]);
  const [questions, setQuestions] = useState<ClarificationQuestion[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [usedMock, setUsedMock] = useState<boolean | null>(null);
  const [analyzed, setAnalyzed] = useState(false);

  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<{ id: string; filename: string } | null>(null);
  const [calendarName, setCalendarName] = useState("My Events");

  useEffect(() => setTimezone(detectTimezone()), []);

  // Any edit to events invalidates a previously generated file (spec section 16).
  const invalidateArtifact = () => setArtifact(null);

  const summary = useMemo(() => {
    const count = (s: string) => events.filter((e) => e.validation_status === s).length;
    return {
      total: events.length,
      valid: count("VALID"),
      warnings: count("VALID_WITH_WARNINGS"),
      clarify: count("REQUIRES_CLARIFICATION"),
      invalid: count("INVALID"),
    };
  }, [events]);

  const anyBlocking = events.some((e) => e.issues.some((i) => i.blocks_export));

  const runAnalyze = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    invalidateArtifact();
    try {
      const res = await analyze({ text, email_subject: subject, timezone });
      setEvents(res.events);
      setQuestions(res.questions);
      setSelected(Object.fromEntries(res.events.map((e) => [e.id, true])));
      setUsedMock(res.used_mock);
      setAnalyzed(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const onFile = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const { text: extracted } = await uploadDocument(file);
      setText(extracted);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  const updateEvent = async (updated: CanonicalEvent) => {
    invalidateArtifact();
    const next = events.map((e) => (e.id === updated.id ? updated : e));
    setEvents(next);
    // Re-validate in the background so warnings/status stay accurate.
    try {
      const res = await validateEvents(next);
      setEvents(res.events);
    } catch {
      /* keep local edit even if revalidation fails */
    }
  };

  const deleteEvent = (id: string) => {
    invalidateArtifact();
    setEvents((prev) => prev.filter((e) => e.id !== id));
  };

  const duplicateEvent = (id: string) => {
    invalidateArtifact();
    const src = events.find((e) => e.id === id);
    if (!src) return;
    const copy = { ...src, id: `${id}-copy-${Date.now()}`, title: `${src.title} (copy)` };
    setEvents((prev) => [...prev, copy]);
    setSelected((s) => ({ ...s, [copy.id]: true }));
  };

  const addManualEvent = () => {
    invalidateArtifact();
    const id = `manual-${Date.now()}`;
    setEvents((prev) => [
      ...prev,
      {
        id, title: "", category: "OTHER", start_date: null, start_time: null,
        end_date: null, end_time: null, timezone, all_day: false, reminders: [],
        validation_status: "INVALID", issues: [], missing_fields: [], ambiguity_flags: [],
        provenance: [],
      },
    ]);
    setSelected((s) => ({ ...s, [id]: true }));
  };

  const onClarify = async (answers: { question_id: string; event_id: string; field: string; answer: string }[]) => {
    setError(null);
    invalidateArtifact();
    try {
      const res = await applyClarifications(events, answers);
      setEvents(res.events);
      const answeredIds = new Set(answers.map((a) => a.question_id));
      setQuestions((qs) => qs.filter((q) => !answeredIds.has(q.id)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not apply answers.");
    }
  };

  const doGenerate = async (onlySelected: boolean) => {
    const chosen = onlySelected ? events.filter((e) => selected[e.id]) : events;
    if (chosen.length === 0) {
      setError("No events selected.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const def = DEFAULT_REMINDER_OPTIONS[defaultReminderIdx].value;
      const res = await generateCalendar(chosen, def ? [def] : [], calendarName);
      setArtifact({ id: res.artifact_id, filename: res.filename });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight">Chronos AI</h1>
        <p className="mt-2 text-slate-500">
          Turn any text — emails, schedules, invites, notes — into a downloadable calendar file.
        </p>
      </header>

      {/* Input */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="label">Email subject (optional)</span>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} className="input" />
          </label>
          <label className="text-sm">
            <span className="label">Timezone</span>
            <input value={timezone} onChange={(e) => setTimezone(e.target.value)} className="input" />
          </label>
        </div>

        <div className="mb-2 flex items-center justify-between">
          <span className="label mb-0">Your text</span>
          <button type="button" onClick={() => setText(SAMPLE)} className="text-xs text-indigo-600 hover:underline">
            Try a sample
          </button>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder="Paste an email, schedule, invite, or notes…"
          className="input resize-y"
        />

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="btn-secondary cursor-pointer">
            Upload document
            <input
              type="file"
              accept=".txt,.eml,.pdf,.docx"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
          </label>
          <label className="text-sm">
            <span className="sr-only">Default reminder</span>
            <select
              value={defaultReminderIdx}
              onChange={(e) => { setDefaultReminderIdx(Number(e.target.value)); invalidateArtifact(); }}
              className="input"
            >
              {DEFAULT_REMINDER_OPTIONS.map((o, i) => (
                <option key={o.label} value={i}>Default reminder: {o.label}</option>
              ))}
            </select>
          </label>
          <button type="button" onClick={runAnalyze} disabled={loading || !text.trim()} className="btn-primary ml-auto">
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>
      </section>

      {error && (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      )}

      {analyzed && (
        <section className="mt-8 space-y-4">
          {/* Summary */}
          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <span><strong>{summary.total}</strong> events</span>
            <span className="text-emerald-700">{summary.valid} valid</span>
            <span className="text-amber-700">{summary.warnings} warnings</span>
            <span className="text-sky-700">{summary.clarify} need clarification</span>
            {summary.invalid > 0 && <span className="text-rose-700">{summary.invalid} invalid</span>}
            <span className="ml-auto text-xs text-slate-400">
              {usedMock ? "Extracted with built-in parser (mock mode)" : "Extracted with Qwen"}
            </span>
          </div>

          {questions.length > 0 && <ClarificationPanel questions={questions} onSubmit={onClarify} />}

          {events.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              No events detected. Edit your text or add one manually.
            </div>
          ) : (
            <div className="space-y-4">
              {events.map((ev) => (
                <EventCard
                  key={ev.id}
                  event={ev}
                  selected={!!selected[ev.id]}
                  onToggleSelect={() => setSelected((s) => ({ ...s, [ev.id]: !s[ev.id] }))}
                  onChange={updateEvent}
                  onDelete={() => deleteEvent(ev.id)}
                  onDuplicate={() => duplicateEvent(ev.id)}
                />
              ))}
            </div>
          )}

          <button type="button" onClick={addManualEvent} className="btn-secondary">+ Add event manually</button>

          {/* Generate / download */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <label className="mb-3 block text-sm">
              <span className="label">Calendar name</span>
              <input value={calendarName} onChange={(e) => setCalendarName(e.target.value)} className="input" />
            </label>

            {anyBlocking && (
              <p className="mb-3 rounded bg-rose-50 p-2 text-xs text-rose-700">
                Some events have blocking errors. Fix them before exporting.
              </p>
            )}

            {artifact ? (
              <a
                href={downloadUrl(artifact.id)}
                className="btn-primary inline-block"
                download={artifact.filename}
              >
                Download {artifact.filename}
              </a>
            ) : (
              <div className="flex flex-wrap gap-3">
                <button type="button" onClick={() => doGenerate(true)} disabled={generating || anyBlocking} className="btn-primary">
                  {generating ? "Generating…" : "Generate selected"}
                </button>
                <button type="button" onClick={() => doGenerate(false)} disabled={generating || anyBlocking} className="btn-secondary">
                  Generate all
                </button>
              </div>
            )}
            <p className="mt-3 text-xs text-slate-400">
              The .ics file validates on the server before download and saves to your Downloads folder.
              Embedded reminders request alarms in your calendar app (appearance varies by app).
            </p>
          </div>
        </section>
      )}
    </main>
  );
}
