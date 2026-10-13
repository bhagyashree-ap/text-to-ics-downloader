# Text → Calendar (Text-to-ICS Downloader)

Paste any text that mentions one or more events (an email, a copied Excel/TSV row,
a chat message, free-form notes), click **Download**, and get a single `.ics` file
with all the events in it.

The flow is deliberately one-shot:

```
paste text  →  click Download
            →  Qwen3 (vLLM) extracts ALL events (title + date/time)
            →  reminder in the text? apply it per event.
               none found?           ONE popup asks (choice applies to all events).
            →  one .ics with every event downloads to your Downloads folder.
```

- Extracts **multiple events** into **one `.ics`** — no review/edit screen.
- Uses a **reminder found in the text** ("remind me 2 days before") when present;
  otherwise asks once via a popup (None / at time / 10 min / 1 hour / 1 day before).
- Produces a standards-compliant iCalendar file (RFC 5545) with `VEVENT` + `VALARM`.
- Works **today** with a built-in rules-based fallback — and upgrades to **Qwen3 on vLLM**
  (LoRA-ready) by changing a single environment variable. No code changes.

> This is the simple MVP. The architecture is intentionally one Python service + one
> Next.js frontend. The full roadmap (gRPC split, Postgres, tiered LLM routing, OCR,
> OAuth insert, eval harness) layers in on top without a rewrite.

## Architecture (MVP)

```
[ Next.js frontend ]           textarea + Download button + reminder popup
        │  HTTP/JSON
        ▼
[ FastAPI backend ]            one Python service
   ├── extractor.py            LLM (Qwen3 on vLLM, OpenAI-compatible) + rules fallback
   ├── validator.py            dateparser + python-dateutil normalize/validate, RRULE
   └── ics_builder.py          icalendar: VEVENT + VALARM, correct MIME/escaping
```

## The downloaded file

The UI produces a single **`.ics`** file (universal iCalendar — opens in Apple
Calendar and Outlook, imports into Google Calendar). It saves to the browser's
normal Downloads folder, triggered via a Blob with `text/calendar` MIME.

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: configure vLLM / Qwen3
uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000 (docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000.

## Wiring up Qwen3-14B/8B on vLLM (optional — the app works without it)

Start vLLM with an OpenAI-compatible server (optionally with a LoRA adapter):

```bash
vllm serve Qwen/Qwen3-14B \
  --enable-lora \
  --lora-modules text2ics=/path/to/your/lora-adapter
```

Then set `backend/.env`:

```ini
LLM_BASE_URL=http://localhost:8000/v1   # your vLLM server
LLM_API_KEY=EMPTY                        # vLLM ignores the key, but the client needs one
LLM_MODEL=Qwen/Qwen3-14B                 # or "text2ics" to use your LoRA adapter
```

- Switching from the base model to your **LoRA adapter** is just changing `LLM_MODEL`
  to the adapter name you registered — no code change.
- The extractor asks vLLM for **schema-constrained JSON** (guided decoding) so Qwen3
  returns clean, valid events. Qwen3 "thinking" is disabled for extraction.
- If `LLM_BASE_URL` is unset or the server is unreachable, the backend automatically
  uses the **rules-based fallback** so the app stays functional.

## Project layout

```
text-to-ics-downloader/
├── backend/
│   ├── app/
│   │   ├── main.py          FastAPI app + routes (/extract, /ics, /health)
│   │   ├── schema.py        Pydantic event schema (shared contract)
│   │   ├── extractor.py     vLLM/Qwen3 client + rules-based fallback
│   │   ├── validator.py     date/recurrence normalization + confidence
│   │   ├── ics_builder.py   icalendar VEVENT + VALARM builder
│   │   └── gcal.py          "Add to Google Calendar" link builder
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/                 Next.js App Router UI
    ├── lib/                 API client + download helpers
    ├── package.json
    └── ... (config)
```
