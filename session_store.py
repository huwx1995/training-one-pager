"""In-memory document sessions for the local single-user server."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from document_parser import serializable_result


def document_version(document_id: str, revision: int) -> str:
    return hashlib.sha256(f"{document_id}:{revision}".encode("utf-8")).hexdigest()[:24]


class SessionStore:
    def __init__(self, lock: Any) -> None:
        self.lock = lock
        self.sessions: dict[str, dict[str, Any]] = {}

    def create(self, document_id: str, parsed: dict[str, Any], file_name: str, extension: str,
               source_path: Path | None = None) -> dict[str, Any]:
        serialized = serializable_result(parsed)
        session = {
            "id": document_id, "revision": 1, "version": document_version(document_id, 1),
            "file_name": file_name, "extension": extension, "page_count": int(parsed.get("page_count") or 1),
            "segments": serialized["segments"], "primary_segment_ids": [item["id"] for item in serialized["segments"]],
            "blocks": serialized["blocks"], "image_assets": serialized["image_assets"],
            "document_preview": serialized.get("document_preview", {}), "confirmations": {},
            "supplement_count": 0, "created_at": int(time.time()),
            "source_paths": [source_path] if source_path else [],
        }
        with self.lock:
            self.sessions[document_id] = session
        return session

    def get(self, document_id: str) -> dict[str, Any]:
        with self.lock:
            session = self.sessions.get(document_id)
        if not session:
            raise ValueError("文档会话已失效，请重新上传并抽取材料。")
        return session

    def append(self, document_id: str, parsed_items: list[dict[str, Any]],
               source_paths: list[Path] | None = None) -> dict[str, Any]:
        with self.lock:
            session = self.sessions.get(document_id)
            if not session:
                raise ValueError("主材料会话已失效，请重新上传主材料。")
            added_segments: list[dict[str, Any]] = []
            added_blocks: list[dict[str, Any]] = []
            added_assets: list[dict[str, Any]] = []
            added_previews: list[dict[str, Any]] = []
            for parsed in parsed_items:
                serialized = serializable_result(parsed)
                added_segments.extend(serialized["segments"])
                added_blocks.extend(serialized["blocks"])
                added_assets.extend(serialized["image_assets"])
                if serialized.get("document_preview"):
                    added_previews.append(serialized["document_preview"])
            session["supplement_count"] += len(parsed_items)
            session["segments"].extend(added_segments)
            session["blocks"].extend(added_blocks)
            session["image_assets"].extend(added_assets)
            session.setdefault("supplemental_previews", []).extend(added_previews)
            session["source_paths"].extend(source_paths or [])
            session["revision"] += 1
            session["version"] = document_version(document_id, session["revision"])
            session["confirmations"] = {}
            return {"segments": added_segments, "blocks": added_blocks, "image_assets": added_assets,
                    "document_previews": added_previews, "document_version": session["version"]}

    def remove(self, document_id: str) -> dict[str, Any] | None:
        with self.lock:
            return self.sessions.pop(document_id, None)
