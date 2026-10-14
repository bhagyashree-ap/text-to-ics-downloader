from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from analysis import router as analysis_router
from calendar_export import router as calendar_router

app = FastAPI(title="Text to Calendar")
INDEX = Path(__file__).with_name("index.html")


@app.get("/", response_class=HTMLResponse)
def home():
    return INDEX.read_text()


@app.get("/api/v1/health")
def health():
    return {"ok": True}


app.include_router(analysis_router)
app.include_router(calendar_router)
