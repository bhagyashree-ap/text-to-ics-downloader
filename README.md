# Text to .ICS

Paste event text, review the extracted details, and download an `.ics` calendar.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

Event extraction uses Ollama at `http://localhost:11434/v1/chat/completions` with the `llama3` model by default. Start Ollama and install the model with:

```bash
ollama serve
ollama pull llama3
```

Set `LLAMA_API_URL` or `LLAMA_MODEL` to use a different OpenAI-compatible endpoint or model. The app also includes deterministic parsing for supported structured schedules and meeting invitations.
