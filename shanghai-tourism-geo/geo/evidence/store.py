"""Evidence Store — version-controlled JSON-per-capture (truth plane = git).

证据落地为 git 友好的 JSON 文件，可审计、可 diff、可回溯。
  evidence/captures/<id>.json   解析后的 Capture
  evidence/raw/<id>.json        归档的原始引擎响应体（不可篡改）
"""
from __future__ import annotations

from pathlib import Path

from .schema import Capture


class EvidenceStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.captures_dir = self.root / "captures"
        self.raw_dir = self.root / "raw"
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def archive_raw(self, capture_id: str, raw: bytes | str, suffix: str = ".json") -> Path:
        path = self.raw_dir / f"{capture_id}{suffix}"
        data = raw.encode("utf-8") if isinstance(raw, str) else raw
        path.write_bytes(data)
        return path

    def save(self, capture: Capture) -> Path:
        path = self.captures_dir / f"{capture.id}.json"
        path.write_text(capture.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, capture_id: str) -> Capture:
        path = self.captures_dir / f"{capture_id}.json"
        return Capture.model_validate_json(path.read_text(encoding="utf-8"))

    def load_all(self) -> list[Capture]:
        return [
            Capture.model_validate_json(p.read_text(encoding="utf-8"))
            for p in sorted(self.captures_dir.glob("*.json"))
        ]
