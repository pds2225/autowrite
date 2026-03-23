from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from downloader import DownloadedImage


def _as_rows(images: Iterable[DownloadedImage]) -> list[dict]:
    rows = []
    for img in images:
        rows.append(
            {
                "section": img.section,
                "file_name": img.file_name,
                "file_path": img.file_path,
                "source_url": img.source_url,
                "image_url": img.image_url,
                "caption": img.caption,
                "width": img.width,
                "height": img.height,
                "content_sha256": img.content_sha256,
                "provider": img.provider,
                "query": img.query,
                "selected": img.selected,
            }
        )
    return rows


def write_manifest_json(images: Iterable[DownloadedImage], path: str) -> None:
    rows = _as_rows(images)
    Path(path).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def write_manifest_csv(images: Iterable[DownloadedImage], path: str) -> None:
    rows = _as_rows(images)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return

    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
