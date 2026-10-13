# gRPC & Protobuf Contracts

Proto files live in `backend/proto/`. Generate stubs with:

```bash
python scripts/gen_proto.py   # outputs into backend/app/grpc_gen/
```

## Files & services

| Proto | Service | RPCs |
|---|---|---|
| `common.proto` | — (shared messages) | `Event`, `LocalDate`, `LocalTime`, `Reminder`, `Recurrence`, enums, `RequestContext` |
| `input_processing.proto` | InputProcessingService | ProcessText, ProcessUploadedFile |
| `ai_extraction.proto` | AIExtractionService | ExtractEvents |
| `date_normalization.proto` | DateNormalizationService | NormalizeEvents |
| `event_validation.proto` | EventValidationService | ValidateEvents |
| `clarification.proto` | ClarificationService | GenerateClarificationQuestions, ApplyClarificationAnswers |
| `reminder.proto` | ReminderService | ValidateReminderSettings, BuildReminderSpecifications |
| `ics_generation.proto` | ICSGenerationService, ICSValidationService | GenerateCalendar, ValidateCalendar |
| `artifact.proto` | ArtifactService | CreateArtifact, GetArtifact, DeleteArtifact |

## Message design decisions

- **No opaque blobs.** Events are fully typed nested messages, not JSON strings.
- **Dates/times are typed.** `LocalDate` and `LocalTime` represent wall-clock values;
  the IANA `timezone` is a separate string field. We deliberately do **not** use a
  single `google.protobuf.Timestamp` as an event's primary representation, because a
  UTC instant cannot faithfully carry "9 AM local, every week, across DST".
- **All-day events** use `LocalDate` fields with `all_day=true` and no `LocalTime`.
- **Enums** cover stable categories/statuses; `EVENT_CATEGORY_OTHER` keeps it extensible.
- **Repeated** fields carry multiple events and reminders.

## Versioning rules

- Never reuse a field number after deleting a field; add `reserved` entries.
- Add new fields with new numbers; keep old ones optional.
- `RequestContext` is included on every request for tracing and defaults.

## Transport

- Explicit deadlines on every client call (`GRPC_DEADLINE_SECONDS`).
- gRPC status codes map to HTTP at the gateway (`INVALID_ARGUMENT`→400,
  `NOT_FOUND`→404, `DEADLINE_EXCEEDED`→504, `UNAVAILABLE`→503).
- Health checking (`grpc.health.v1`) and reflection enabled in development.
- Max message size 16 MiB on client and server.
