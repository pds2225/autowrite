from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from PIL import Image

from image_search import ImageCandidate

LOGGER = logging.getLogger(__name__)


@dataclass
class DownloadedImage:
    section: str
    file_name: str
    file_path: str
    source_url: str
    image_url: str
    caption: str
    width: int
    height: int
    content_sha256: str
    provider: str
    query: str
    selected: bool = True


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z가-힣]+", "_", text.strip().lower())
    return cleaned.strip("_") or "image"


def infer_extension(image_url: str, content_type: Optional[str]) -> str:
    if content_type and "image/" in content_type:
        ext = content_type.split("image/")[-1].split(";")[0].strip()
        if ext == "jpeg":
            return ".jpg"
        return f".{ext}"

    parsed = urlparse(image_url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
        return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def generate_caption(section: str, summary: str, title: str) -> str:
    title = (title or "").strip()
    summary_core = " ".join(summary.split()[:16])
    return f"[{section}] {title} — {summary_core}".strip()


class ImageDownloader:
    def __init__(self, output_dir: str, min_width: int = 800, min_height: int = 600, timeout: int = 20) -> None:
        self.output_dir = Path(output_dir)
        self.min_width = min_width
        self.min_height = min_height
        self.timeout = timeout
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(self, candidate: ImageCandidate, summary: str, index: int) -> Optional[DownloadedImage]:
        try:
            response = requests.get(candidate.image_url, timeout=self.timeout)
            response.raise_for_status()
        except Exception as exc:
            LOGGER.exception("Download failed: %s", exc)
            return None

        ext = infer_extension(candidate.image_url, response.headers.get("Content-Type"))
        base_title = slugify(candidate.title)[:36]
        file_name = f"{slugify(candidate.section)}_{index:02d}_{base_title}{ext}"
        file_path = self.output_dir / file_name
        file_path.write_bytes(response.content)

        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception as exc:
            LOGGER.exception("Invalid image format (%s): %s", file_path, exc)
            file_path.unlink(missing_ok=True)
            return None

        if width < self.min_width or height < self.min_height:
            LOGGER.info("Skip small image: %s (%dx%d)", file_name, width, height)
            file_path.unlink(missing_ok=True)
            return None

        digest = hashlib.sha256(response.content).hexdigest()
        return DownloadedImage(
            section=candidate.section,
            file_name=file_name,
            file_path=str(file_path),
            source_url=candidate.source_url,
            image_url=candidate.image_url,
            caption=generate_caption(candidate.section, summary, candidate.title),
            width=width,
            height=height,
            content_sha256=digest,
            provider=candidate.provider,
            query=candidate.query,
        )
