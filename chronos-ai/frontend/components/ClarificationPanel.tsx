"use client";

import { useState } from "react";
import type { ClarificationQuestion } from "@/lib/types";

export function ClarificationPanel({
  questions,
  onSubmit,
}: {
  questions: ClarificationQuestion[];
  onSubmit: (answers: { question_id: string; event_id: string; field: string; answer: string }[]) => void;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  if (questions.length === 0) return null;

  const submit = () => {
    const payload = questions
      .filter((q) => (answers[q.id] ?? "").trim())
      .map((q) => ({ question_id: q.id, event_id: q.event_id, field: q.field, answer: answers[q.id].trim() }));
    if (payload.length) onSubmit(payload);
  };

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 p-4">
      <h3 className="mb-2 text-sm font-semibold text-sky-800">
        A few questions to get these right
      </h3>
      <div className="space-y-3">
        {questions.map((q) => (
          <div key={q.id}>
            <label className="mb-1 block text-sm text-slate-700">{q.question}</label>
            {q.suggested_answers.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {q.suggested_answers.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setAnswers((a) => ({ ...a, [q.id]: s }))}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      answers[q.id] === s ? "border-sky-500 bg-sky-100 text-sky-700" : "border-slate-200 bg-white text-slate-600"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : (
              <input
                value={answers[q.id] ?? ""}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                placeholder={q.field === "start_date" ? "YYYY-MM-DD" : "Your answer"}
                className="input"
              />
            )}
          </div>
        ))}
      </div>
      <button type="button" onClick={submit} className="btn-primary mt-3">
        Apply answers
      </button>
    </div>
  );
}
