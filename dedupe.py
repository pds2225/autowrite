from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List

import imagehash
from PIL import Image

from downloader import DownloadedImage

LOGGER = logging.getLogger(__name__)


def _compute_phash(path: str) -> imagehash.ImageHash | None:
    try:
        with Image.open(path) as img:
            return imagehash.phash(img)
    except Exception as exc:
        LOGGER.warning("Failed to compute pHash for %s: %s", path, exc)
        return None


def remove_duplicates(images: Iterable[DownloadedImage], phash_threshold: int = 8) -> List[DownloadedImage]:
    unique: List[DownloadedImage] = []
    hashes: list[imagehash.ImageHash] = []
    seen_sha256: set[str] = set()

    for item in images:
        if item.content_sha256 in seen_sha256:
            Path(item.file_path).unlink(missing_ok=True)
            continue

        current_hash = _compute_phash(item.file_path)
        is_dup = False
        if current_hash is not None:
            for existing_hash in hashes:
                if current_hash - existing_hash <= phash_threshold:
                    is_dup = True
                    break

        if is_dup:
            Path(item.file_path).unlink(missing_ok=True)
            continue

        seen_sha256.add(item.content_sha256)
        if current_hash is not None:
            hashes.append(current_hash)
        unique.append(item)

    return unique
