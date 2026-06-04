from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SectionProfile(BaseModel):
    field_id: str
    label: str
    anchor_text: str
    required: bool = False
    is_excluded: bool = False
    insert_mode: Literal["after_paragraph"] = "after_paragraph"
    source: Literal["heuristic", "ai"] = "heuristic"


class TableCellProfile(BaseModel):
    cell_id: str
    label: str
    row: int
    cell: int
    required: bool = False
    field_type: Literal["text", "textarea"] = "text"
    row_header: str = ""
    col_header: str = ""


class TableProfile(BaseModel):
    table_id: str
    label: str
    table_index: int = 0
    anchors: list[str] = Field(default_factory=list)
    row_count: int
    col_count: int
    cells: list[TableCellProfile] = Field(default_factory=list)


class ImageSlotProfile(BaseModel):
    slot_id: str
    label: str
    required: bool = True
    anchor_type: Literal["table_cell", "after_paragraph"] = "after_paragraph"
    anchor_ref: dict[str, Any] = Field(default_factory=dict)
    size_hint: dict[str, float] = Field(default_factory=lambda: {"width_cm": 14.0, "height_cm": 9.0})
    source: Literal["template", "suggested", "ai"] = "template"


class QuestionProfile(BaseModel):
    question_id: str
    label: str
    field_type: Literal["text", "textarea", "number"] = "textarea"
    required: bool = False
    source_hint: str = ""
    target: dict[str, Any] = Field(default_factory=dict)


class TemplateProfile(BaseModel):
    template_id: str
    template_name: str
    source_docx: str
    created_at: str = Field(default_factory=utc_now)
    sections: list[SectionProfile] = Field(default_factory=list)
    tables: list[TableProfile] = Field(default_factory=list)
    image_slots: list[ImageSlotProfile] = Field(default_factory=list)
    questions: list[QuestionProfile] = Field(default_factory=list)
    analysis_notes: list[str] = Field(default_factory=list)


class ReferenceFile(BaseModel):
    file_name: str
    saved_path: str
    usage: str = "reference"
    extracted_text_path: str = ""
    extracted_preview: str = ""


class EvidenceRequest(BaseModel):
    topic: str
    purpose: str = ""


class ImageRequest(BaseModel):
    slot_id: str
    label: str
    prompt: str = ""
    source: Literal["generated", "uploaded", "chart"] = "generated"


class ProjectInput(BaseModel):
    template_id: str
    project_meta: dict[str, Any] = Field(default_factory=dict)
    organization_profile: dict[str, Any] = Field(default_factory=dict)
    answers: dict[str, Any] = Field(default_factory=dict)
    references: list[ReferenceFile] = Field(default_factory=list)
    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    image_requests: list[ImageRequest] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class EvidenceSource(BaseModel):
    topic: str
    title: str
    url: str
    organization: str = ""
    checked_at: str = Field(default_factory=utc_now)
    summary: str = ""
    used_for: list[str] = Field(default_factory=list)


class GeneratedImage(BaseModel):
    slot_id: str
    label: str
    path: str
    caption: str = ""
    source: Literal["generated", "uploaded", "chart", "placeholder"] = "generated"


class ArtifactBundle(BaseModel):
    output_docx: str
    qa_report: str
    sources: str
    benchmark_compare: str = ""
    transfer_report: str = ""
    preview_manifest: str = ""
    generated_assets: list[str] = Field(default_factory=list)
    results_dir: str = ""
    results_docx: str = ""
    hwp_paste: str = ""
    copy_blocks: str = ""
    fill_map: str = ""
