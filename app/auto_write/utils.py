from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from uuid import uuid4


def slugify(value: str, prefix: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    compact = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    if compact:
        return compact[:48]
    return f"{prefix}_{uuid4().hex[:8]}"


def short_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def sanitize_user_filename(raw_name: str) -> str:
    name = (raw_name or "").strip()
    if not name:
        raise ValueError("참고자료 파일명이 비어 있습니다.")
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError("참고자료 파일명에 경로 구분자 또는 '..'는 사용할 수 없습니다.")
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "_", name).strip().strip(".")
    if not name:
        raise ValueError("참고자료 파일명에 사용할 수 있는 문자가 없습니다.")
    stem = Path(name).stem.strip()
    suffix = Path(name).suffix
    if not stem:
        raise ValueError("참고자료 파일명 본문이 비어 있습니다.")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Windows 예약어는 파일명으로 사용할 수 없습니다: {stem}")
    safe_stem = re.sub(r"\s+", " ", stem)
    if not safe_stem:
        raise ValueError("참고자료 파일명을 확인해 주세요.")
    safe_name = f"{safe_stem}{suffix}"
    if len(safe_name) > 180:
        trim = max(1, 180 - len(suffix))
        safe_name = f"{safe_stem[:trim]}{suffix}"
    return safe_name


def safe_console_text(value: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2022": "*",
        "\u25cf": "*",
        "\u2713": "[OK]",
        "\u2705": "[OK]",
        "\u26a0": "[WARN]",
        "\U0001F4F8": "[IMG]",
        "\u2550": "=",
    }
    result = value
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def log_line(message: str) -> None:
    print(safe_console_text(message))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def unique_lines(text: str) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines
