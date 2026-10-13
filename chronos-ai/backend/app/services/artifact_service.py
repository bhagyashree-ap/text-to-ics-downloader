"""Temporary artifact storage with TTL and safe access (spec sections 4.10 & 19)."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

from ..core.config import settings


@dataclass
class ArtifactMeta:
    artifact_id: str
    filename: str
    content_type: str
    size_bytes: int
    expires_at_unix: int


def _storage_root() -> Path:
    root = Path(settings.ARTIFACT_STORAGE_PATH)
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_filename(name: str) -> str:
    name = os.path.basename(name)  # strip any path components
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "calendar.ics"


class ArtifactStore:
    def __init__(self) -> None:
        self.root = _storage_root()

    def create(self, content: bytes, content_type: str, suggested_filename: str) -> ArtifactMeta:
        self.cleanup_expired()
        artifact_id = uuid.uuid4().hex
        filename = safe_filename(suggested_filename)
        expires = int(time.time()) + settings.ARTIFACT_TTL_SECONDS

        data_path = self.root / f"{artifact_id}.bin"
        data_path.write_bytes(content)
        meta = ArtifactMeta(artifact_id, filename, content_type, len(content), expires)
        (self.root / f"{artifact_id}.json").write_text(json.dumps(asdict(meta)))
        return meta

    def get(self, artifact_id: str) -> tuple[ArtifactMeta, bytes] | None:
        if not re.fullmatch(r"[0-9a-f]{32}", artifact_id):  # prevent traversal/injection
            return None
        meta_path = self.root / f"{artifact_id}.json"
        data_path = self.root / f"{artifact_id}.bin"
        if not meta_path.exists() or not data_path.exists():
            return None
        meta = ArtifactMeta(**json.loads(meta_path.read_text()))
        if meta.expires_at_unix < int(time.time()):
            self.delete(artifact_id)
            return None
        return meta, data_path.read_bytes()

    def delete(self, artifact_id: str) -> bool:
        if not re.fullmatch(r"[0-9a-f]{32}", artifact_id):
            return False
        deleted = False
        for suffix in (".bin", ".json"):
            p = self.root / f"{artifact_id}{suffix}"
            if p.exists():
                p.unlink()
                deleted = True
        return deleted

    def cleanup_expired(self) -> int:
        now = int(time.time())
        removed = 0
        for meta_file in self.root.glob("*.json"):
            try:
                meta = json.loads(meta_file.read_text())
                if meta.get("expires_at_unix", 0) < now:
                    self.delete(meta["artifact_id"])
                    removed += 1
            except Exception:
                continue
        return removed


store = ArtifactStore()
