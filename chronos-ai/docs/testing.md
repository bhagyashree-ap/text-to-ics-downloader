# Testing

```bash
cd backend
python scripts/gen_proto.py   # required for test_grpc.py / test_api.py
pytest
```

The suite runs in **mock mode** (no Qwen key). It asserts the **actual contents** of
generated calendars, not just that a file exists.

## Coverage map (spec section 22)

| Area | File | Cases |
|---|---|---|
| Extraction (meeting, exam, multi-event, email, deadline, all-day, reminder, large doc, no-events) | `test_extraction.py` | 1–9, 36 |
| Normalization & validation (missing end, deadline no-duration, overnight, weekday mismatch, bad tz, DST gap, title required, end<start, RRULE conflict, optional location) | `test_normalization_validation.py` | 11–15, 37–39 |
| ICS semantics (local time, all-day exclusive end, multiple VALARMs, Unicode, special chars, RRULE, multi-timezone, round-trip, count mismatch) | `test_ics.py` | 16–21, 40 |
| Reminders & clarification (batch default, override, dedupe, missing-date question, provenance, optional-location, deadline no end-time Q) | `test_reminders_clarification.py` | 10, 32–35 |
| Documents (empty, TXT, EML, corrupt PDF, oversized, unsupported type) | `test_documents.py` | 22–27 |
| Pipeline + malformed model response | `test_pipeline.py` | integration, 28 |
| gRPC transport (extract, generate+validate, deadline exceeded) | `test_grpc.py` | 29–31, serialization |
| HTTP API (health, analyze→generate→download, empty input, unknown artifact) | `test_api.py` | end-to-end |

## Verified in this environment

The build sandbox blocks PyPI/npm, so `pytest`, `protoc`, and `next build` could not be
executed here. What **was** run and passed:

- The real **mock extraction engine** (`MockQwenProvider`, stdlib-only): 21/21 logic
  checks for dates, 12h/24h times, categories, all-day, multi-event, reminders, URLs,
  and the no-events case — this caught and fixed a time-parsing bug.
- `python -m compileall` on the entire backend (all modules compile).

Run the full `pytest` suite on a machine with dependencies installed to validate the
gRPC/ICS/API layers end-to-end.

## Known limitations

- The deterministic **mock provider is heuristic** — it is for development/tests and to
  guarantee the app runs without credentials. Real extraction quality comes from Qwen.
- **Postgres/Redis/Celery/auth** are described as roadmap and not wired in this slice;
  the MVP is stateless with short-lived temp artifacts.
- **OCR, CSV/XLSX** inputs are not implemented here.
- `test_grpc.py` / `test_api.py` require generated stubs; without them they are skipped
  (via `importorskip`), not failed.
