from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from models import WarningEntry

SECTION_KEYWORDS = {
    "problem": ["문제", "현황", "problem"],
    "solution": ["해결", "솔루션", "solution"],
    "scaleup": ["성장", "확장", "시장", "scaleup"],
    "team": ["팀", "인력", "조직", "team"],
    "budget": ["예산", "자금", "budget"],
    "schedule": ["일정", "로드맵", "schedule"],
    "org": ["조직", "거버넌스", "org"],
}

TABLE_TYPE_ALIASES = {
    "team": ["성명", "역할", "담당", "보유역량", "확보현황", "경력"],
    "budget": ["비목", "금액", "산출", "예산", "단가", "수량"],
    "schedule": ["기간", "일정", "마일스톤", "단계", "월", "분기"],
    "org": ["조직", "부서", "직책", "권한", "협업"],
}


def setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("docx_engine")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    return logger


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def infer_table_type(header_texts: list[str]) -> str:
    score: dict[str, int] = {k: 0 for k in TABLE_TYPE_ALIASES}
    header_blob = " ".join(header_texts)
    for table_type, aliases in TABLE_TYPE_ALIASES.items():
        for alias in aliases:
            if alias.lower() in header_blob.lower():
                score[table_type] += 1
    winner = max(score, key=score.get)
    return winner if score[winner] > 0 else "unknown"


class WarningCollector:
    def __init__(self) -> None:
        self.items: list[WarningEntry] = []

    def add(self, category: str, message: str, **context: Any) -> None:
        self.items.append(WarningEntry(category=category, message=message, context=context))

    def to_list(self) -> list[dict[str, Any]]:
        return [w.to_dict() for w in self.items]
