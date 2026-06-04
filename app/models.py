from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ValidationIssue:
    field: str
    severity: str  # error, warning
    message: str

@dataclass
class PipelineResult:
    mapped_fields: Dict[str, str]
    validation_issues: List[ValidationIssue] = field(default_factory=list)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
