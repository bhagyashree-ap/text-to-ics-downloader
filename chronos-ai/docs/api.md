# HTTP API

Base URL: `http://localhost:8000`. Interactive docs at `/docs` (OpenAPI).

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/analyze` | Text → extracted + normalized + validated events + clarification questions |
| POST | `/api/v1/documents` | Upload TXT/EML/PDF/DOCX → extracted text |
| POST | `/api/v1/validate` | Re-validate edited events |
| POST | `/api/v1/clarifications` | Apply answers, revalidate |
| POST | `/api/v1/reminders/validate` | Validate reminder settings |
| POST | `/api/v1/calendar/generate` | Validate → generate → semantic-check → store artifact |
| GET | `/api/v1/calendar/download/{artifact_id}` | Download the `.ics` |
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/ready` | Readiness (checks gRPC reachability) |

## `POST /api/v1/analyze`

Request:
```json
{ "text": "Team meeting October 20, 2026 2-3 PM.", "email_subject": "", "timezone": "America/New_York" }
```

Response (abridged):
```json
{
  "batch_id": "…",
  "events": [ { "id": "…", "title": "Team meeting", "start_date": "2026-10-20",
                "start_time": "14:00:00", "end_time": "15:00:00",
                "timezone": "America/New_York", "validation_status": "VALID", "...": "..." } ],
  "questions": [],
  "used_mock": true,
  "model": "mock-deterministic",
  "total_events": 1, "valid_events": 1, "events_with_warnings": 0,
  "events_requiring_clarification": 0
}
```

## `POST /api/v1/calendar/generate`

Request:
```json
{ "events": [ /* CanonicalEvent[] */ ],
  "default_reminders": [ { "amount": 10, "unit": "MINUTES", "anchor": "START" } ],
  "calendar_name": "My Events" }
```

Response:
```json
{ "artifact_id": "…", "filename": "calendar_events_2026-10-13.ics",
  "event_count": 1, "ics_valid": true, "validation_issues": [] }
```

Blocking validation errors → `422`. ICS that fails the semantic re-parse → `500`
(the file is never served).

## Errors

Errors return `{"detail": "..."}` with an appropriate status. Internal stack traces,
model credentials, and backend config are never exposed.
