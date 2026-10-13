# Architecture

## Logical flow

```
User
 └─ Next.js frontend  (HTTPS/REST)
     └─ FastAPI gateway  (orchestration only; no business logic)
         └─ gRPC ──> InputProcessingService
                     AIExtractionService (Qwen adapter / deterministic mock)
                     DateNormalizationService
                     EventValidationService
                     ClarificationService
                     ReminderService
                     ICSGenerationService
                     ICSValidationService
                     ArtifactService
         └─ Downloadable .ics artifact
```

## Service responsibilities

| Service | Responsibility | Deterministic? |
|---|---|---|
| InputProcessing | Normalize text, parse TXT/EML/PDF/DOCX, enforce limits, treat input as untrusted | Yes |
| AIExtraction | Qwen (or mock) → structured raw events; every field validated downstream | LLM + validation |
| DateNormalization | Resolve dates/times/timezones, overnight, DST gap/ambiguity | Yes |
| EventValidation | Title/date/time/tz/recurrence/reminder checks; statuses + issues | Yes |
| Clarification | Generate minimal questions; apply answers; revalidate | Yes |
| Reminder | Validate/dedupe reminders; apply batch defaults; per-event override | Yes |
| ICSGeneration | Build VCALENDAR/VEVENT/VALARM via `icalendar` | Yes |
| ICSValidation | Parse generated ICS and compare semantically to canonical input | Yes |
| Artifact | Temp storage, safe filenames, TTL, traversal protection | Yes |

## Key design rules

- **Local wall-clock vs UTC are separate.** Events store `start_date` + `start_time`
  + IANA `timezone`, never a single UTC instant. A 9 AM meeting stays 9 AM local
  across DST.
- **The LLM never serializes ICS.** It returns data; deterministic code builds the file.
- **Validation does not trust the model.** Dates/times/timezones are re-derived and
  checked independently.
- **MVP packaging:** all gRPC servicers run in one process; splitting them later is an
  env-var change (`GRPC_*_TARGET`), not a rewrite.

## Request tracing

Every gRPC request carries a `RequestContext.request_id`. Structured logs include
`request_id`, `service`, `operation`, `duration_ms`, `outcome`. Raw email/document
content and credentials are never logged.
