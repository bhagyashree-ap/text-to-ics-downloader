"""Document/input processing tests (spec section 22, cases 22-27)."""
from __future__ import annotations

import pytest

from app.services.input_processing import InputError, process_file, process_text


def test_empty_input_rejected():
    with pytest.raises(InputError):
        process_text("   ")


def test_txt_file():
    content = b"Meeting on October 20, 2026 at 2 PM."
    text, _ = process_file("notes.txt", content)
    assert "Meeting" in text


def test_eml_file():
    eml = (
        b"Subject: Project Sync\r\n"
        b"From: alice@example.com\r\n"
        b"Content-Type: text/plain\r\n\r\n"
        b"Let's meet November 2, 2026 at 10 AM."
    )
    text, _ = process_file("mail.eml", eml)
    assert "Project Sync" in text
    assert "November 2" in text


def test_corrupt_pdf_rejected():
    with pytest.raises(InputError):
        # PDF magic but garbage content.
        process_file("broken.pdf", b"%PDF-1.4 this is not a real pdf body")


def test_oversized_upload_rejected(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(InputError):
        process_file("big.txt", b"this is definitely more than ten bytes")


def test_unsupported_type_rejected():
    with pytest.raises(InputError):
        process_file("evil.exe", b"MZ\x90\x00binarycontent")
