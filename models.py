from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Literal

RiskLevel = Literal["safe", "caution", "manual"]
TableType = Literal["team", "budget", "schedule", "org", "unknown"]


@dataclass
class TableDiagnosis:
    table_index: int
    row_count: int
    estimated_col_count: int
    has_gridspan: bool
    has_vmerge: bool
    header_texts: list[str]
    repeated_row_candidate: bool
    table_risk_level: RiskLevel
    table_type_candidate: TableType
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedTemplate:
    template_path: str
    table_diagnostics: list[TableDiagnosis] = field(default_factory=list)
    section_anchors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_path": self.template_path,
            "table_diagnostics": [t.to_dict() for t in self.table_diagnostics],
            "section_anchors": self.section_anchors,
        }


@dataclass
class WarningEntry:
    category: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RenderCheckResult:
    pdf_generated: bool
    pdf_path: str | None
    page_count: int | None
    preview_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
