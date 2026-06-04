from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import ensure_directories, get_settings
from .autofill import build_autofill_values, merge_form_with_autofill
from .document_ingest import (
    is_supported_template_file,
    reference_accept_value,
    template_accept_value,
    template_upload_detail,
)
from .services.evaluation_service import EvaluationService
from .services.evidence_service import EvidenceService
from .services.image_service import ImageService
from .services.openai_client import OpenAIService
from .services.project_service import ProjectService
from .services.qa_service import QAService
from .services.render_service import RenderService
from .storage import Storage
from .utils import read_json

settings = get_settings()
ensure_directories(settings)
storage = Storage(settings)
openai_service = OpenAIService(settings)
evidence_service = EvidenceService(openai_service)
evaluation_service = EvaluationService(openai_service)
image_service = ImageService(openai_service)
render_service = RenderService()
qa_service = QAService()
project_service = ProjectService(storage, openai_service, evidence_service, image_service, render_service, qa_service)

app = FastAPI(title="Auto Write", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(settings.static_root)), name="static")
templates = Jinja2Templates(directory=str(settings.template_view_root))


def _templates_list_context() -> list[dict]:
    rows: list[dict] = []
    for profile in storage.list_template_profiles():
        rows.append(
            {
                "template_id": profile.template_id,
                "template_name": profile.template_name,
                "docx_ready": project_service.template_docx_ready(profile),
            }
        )
    return rows


def _common_context() -> dict:
    return {
        "settings": settings,
        "ai_status_text": openai_service.status_text,
        "ai_provider": openai_service.provider,
        "templates_list": _templates_list_context(),
        "projects": storage.list_projects(),
        "template_accept": template_accept_value(),
        "reference_accept": reference_accept_value(),
    }


def _read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _upload_has_file(upload: UploadFile | object) -> bool:
    return hasattr(upload, "filename") and hasattr(upload, "read") and bool(str(getattr(upload, "filename", "") or "").strip())


def _extract_text_from_upload(file_name: str, content: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix in {".txt", ".md", ".json"}:
        return content.decode("utf-8", errors="ignore")
    safe_name = Path(file_name).name or f"source{suffix or '.txt'}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / safe_name
        path.write_bytes(content)
        return project_service.extract_reference_text(path)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    context = {"request": request, **_common_context()}
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/api/templates")
async def upload_template(file: UploadFile = File(...)):
    if not is_supported_template_file(file.filename):
        raise HTTPException(status_code=400, detail=template_upload_detail())
    content = await file.read()
    profile = project_service.analyze_uploaded_template(file.filename, content)
    return RedirectResponse(url=f"/templates/{profile.template_id}", status_code=303)


@app.get("/templates/{template_id}", response_class=HTMLResponse)
async def template_detail(request: Request, template_id: str):
    profile = project_service.normalize_profile(storage.load_template_profile(template_id))
    context = {
        "request": request,
        "profile": profile,
        "profile_json": json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        "template_docx_ready": project_service.template_docx_ready(profile),
        **_common_context(),
    }
    return templates.TemplateResponse(request, "template_detail.html", context)


@app.post("/api/templates/{template_id}/finalize")
async def finalize_template(template_id: str, profile_json: str = Form(...)):
    try:
        project_service.finalize_template(template_id, profile_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/templates/{template_id}", status_code=303)


@app.post("/api/projects")
async def create_project(template_id: str = Form(...), project_name: str = Form("")):
    project_id = project_service.create_project(template_id, project_name)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str):
    profile = project_service.load_profile_for_project(project_id)
    project_input_path = storage.project_dir(project_id) / "project_input.json"
    project_input = _read_json_if_exists(project_input_path)
    visible_questions = project_service.visible_questions(profile)
    hidden_question_count = max(len(profile.questions) - len(visible_questions), 0)
    artifacts = {}
    results_artifacts = {}
    qa_report = {}
    transfer_report = {}
    preview_manifest = {}
    hwp_paste_text = ""
    generation_summary = ""
    copy_blocks: list[dict] = []
    results_folder = str(storage.results_dir(project_id))
    artifact_dir = storage.project_dir(project_id) / "output"
    if artifact_dir.exists():
        for name in ("output.docx", "qa_report.json", "sources.json", "benchmark_compare.json", "transfer_report.json", "preview_manifest.json"):
            path = artifact_dir / name
            if path.exists():
                artifacts[name] = str(path)
        qa_path = artifact_dir / "qa_report.json"
        transfer_path = artifact_dir / "transfer_report.json"
        preview_path = artifact_dir / "preview_manifest.json"
        qa_report = _read_json_if_exists(qa_path)
        transfer_report = _read_json_if_exists(transfer_path)
        preview_manifest = _read_json_if_exists(preview_path)
    results_dir = storage.results_dir(project_id)
    if results_dir.exists():
        for path in sorted(results_dir.iterdir()):
            if path.is_file():
                results_artifacts[path.name] = str(path)
        hwp_path = results_dir / "hwp_paste.txt"
        if hwp_path.exists():
            hwp_paste_text = hwp_path.read_text(encoding="utf-8")
        summary_path = results_dir / "generation_summary.txt"
        if summary_path.exists():
            generation_summary = summary_path.read_text(encoding="utf-8")
        blocks_path = results_dir / "copy_blocks.json"
        if blocks_path.exists():
            blocks_data = _read_json_if_exists(blocks_path)
            raw_blocks = blocks_data.get("blocks", [])
            copy_blocks = raw_blocks if isinstance(raw_blocks, list) else []
        if not qa_report and (results_dir / "qa_report.json").exists():
            qa_report = _read_json_if_exists(results_dir / "qa_report.json")
    source_status = project_service.template_source_status(profile, project_id)
    context = {
        "request": request,
        "project_id": project_id,
        "generate_error": request.query_params.get("error", ""),
        "template_source_ready": bool(source_status.get("ready")),
        "template_source_warning": str(source_status.get("message", "")),
        "profile": profile,
        "project_input": project_input,
        "visible_questions": visible_questions,
        "hidden_question_count": hidden_question_count,
        "artifacts": artifacts,
        "results_artifacts": results_artifacts,
        "results_folder": results_folder,
        "hwp_paste_text": hwp_paste_text,
        "generation_summary": generation_summary,
        "copy_blocks": copy_blocks,
        "qa_report": qa_report,
        "transfer_report": transfer_report,
        "preview_manifest": preview_manifest,
        **_common_context(),
    }
    return templates.TemplateResponse(request, "project_detail.html", context)


@app.post("/projects/{project_id}/generate")
async def generate_project(request: Request, project_id: str):
    form = await request.form()
    reference_files = []
    autofill_values = {}

    source_file = form.get("source_file")
    if _upload_has_file(source_file):
        source_content = await source_file.read()
        if source_content:
            source_name = str(source_file.filename or "source.txt")
            source_text = _extract_text_from_upload(source_name, source_content)
            autofill_values = build_autofill_values(source_text)
            # The same file is also kept as a project reference so the generated plan can cite it.
            reference_files.append((source_name, source_content))

    for value in form.getlist("reference_files"):
        if _upload_has_file(value):
            reference_files.append((value.filename, await value.read()))

    form_core_values = {
        "project_title": str(form.get("project_title", "")),
        "organization_name": str(form.get("organization_name", "")),
        "user_brief": str(form.get("user_brief", "")),
        "user_notes": str(form.get("user_notes", "")),
        "evidence_topics": str(form.get("evidence_topics", "")),
    }
    merged_core_values = merge_form_with_autofill(form_core_values, autofill_values)

    answers = {}
    for key, value in form.items():
        if key in {
            "project_title",
            "organization_name",
            "evidence_topics",
            "source_file",
            "reference_files",
            "writing_provider",
            "writing_model",
            "improve_partial",
            "psst_only",
            "disable_images",
        }:
            continue
        if isinstance(value, UploadFile):
            continue
        answers[key] = value
    answers["user_brief"] = merged_core_values["user_brief"]
    answers["user_notes"] = merged_core_values["user_notes"]
    try:
        project_service.save_project_form(
            project_id=project_id,
            answers=answers,
            project_title=merged_core_values["project_title"],
            organization_name=merged_core_values["organization_name"],
            evidence_topics=merged_core_values["evidence_topics"],
            reference_files=reference_files,
            writing_provider=str(form.get("writing_provider", "")),
            writing_model=str(form.get("writing_model", "")),
            improve_partial=str(form.get("improve_partial", "on")).lower() in {"1", "true", "on", "yes"},
            psst_only=str(form.get("psst_only", "on")).lower() in {"1", "true", "on", "yes"},
            disable_images=str(form.get("disable_images", "on")).lower() in {"1", "true", "on", "yes"},
        )
        project_service.generate(project_id)
    except ValueError as exc:
        from urllib.parse import quote

        return RedirectResponse(
            url=f"/projects/{project_id}?error={quote(str(exc), safe='')}",
            status_code=303,
        )
    except Exception as exc:
        import logging
        from urllib.parse import quote

        logging.getLogger(__name__).exception("generate failed project=%s", project_id)
        message = f"계획서 생성 중 오류: {exc}"
        return RedirectResponse(
            url=f"/projects/{project_id}?error={quote(message[:400], safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@app.post("/api/projects/{project_id}/generate")
async def generate_project_api(project_id: str):
    try:
        artifacts = project_service.generate(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return artifacts.model_dump()


@app.post("/api/projects/{project_id}/evaluate")
async def evaluate_project(
    project_id: str,
    announcement_text: str = Form(default=""),
    announcement_file: UploadFile | None = File(default=None),
    max_iterations: int = Form(default=3),
):
    """공고문(텍스트 또는 파일)을 기준으로 사업계획서를 채점하고 평가 결과를 반환한다.
    공고문 없이 호출하면 내부 QA 기준으로만 채점한다."""
    # 1. 공고문 텍스트 수집
    ann_text = announcement_text.strip()
    if not ann_text and announcement_file and announcement_file.filename:
        content = await announcement_file.read()
        file_name = str(announcement_file.filename or "")
        suffix = Path(file_name).suffix.lower()
        ann_path = Path(tempfile.mktemp(suffix=suffix))
        ann_path.write_bytes(content)
        try:
            ann_text = project_service.extract_reference_text(ann_path)
        finally:
            ann_path.unlink(missing_ok=True)

    # 2. 평가기준 파싱
    criteria = evaluation_service.parse_announcement(ann_text) if ann_text else []

    # 3. 사업계획서 텍스트 추출
    output_docx = storage.project_dir(project_id) / "output" / "output.docx"
    if not output_docx.exists():
        raise HTTPException(status_code=404, detail="먼저 사업계획서를 생성해주세요.")
    try:
        from docx import Document as _DocxDoc
        _doc = _DocxDoc(str(output_docx))
        doc_lines = [p.text.strip() for p in _doc.paragraphs if p.text.strip()]
        for tbl in _doc.tables:
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    doc_lines.append(" | ".join(dict.fromkeys(cells)))
        doc_text = "\n".join(doc_lines)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DOCX 읽기 실패: {exc}") from exc

    # 4. 평가기준 없으면 기본 품질 지표만 반환
    if not criteria:
        return {
            "status": "no_criteria",
            "message": "평가기준이 파싱되지 않았습니다. 공고문 텍스트 또는 파일을 함께 제출하세요.",
            "doc_length": len(doc_text),
        }

    # 5. 채점
    profile = project_service.load_profile_for_project(project_id)
    profile_questions = [q.model_dump() for q in profile.questions]
    scores = evaluation_service.score_document(doc_text, criteria, profile_questions)
    eval_result = evaluation_service.build_eval_result(1, scores, profile_questions)

    # 6. 결과 저장
    eval_path = storage.project_dir(project_id) / "output" / "eval_report.json"
    from .services.evaluation_service import EvalLoopReport as _ELR
    loop_report = _ELR(
        project_id=project_id,
        iterations=[eval_result],
        final_score=eval_result.total_score,
        final_max=eval_result.max_total,
        final_pass_ratio=eval_result.pass_ratio,
        converged=True,
        announcement_criteria=[
            {"name": c.name, "max_score": c.max_score, "description": c.description}
            for c in criteria
        ],
    )
    report_dict = evaluation_service.to_report_dict(loop_report)
    import json as _json
    eval_path.write_text(_json.dumps(report_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    return report_dict


@app.get("/api/projects/{project_id}/eval_report")
async def get_eval_report(project_id: str):
    """저장된 평가 결과를 반환한다."""
    eval_path = storage.project_dir(project_id) / "output" / "eval_report.json"
    if not eval_path.exists():
        raise HTTPException(status_code=404, detail="평가 결과가 없습니다. /evaluate 먼저 호출하세요.")
    import json as _json
    return _json.loads(eval_path.read_text(encoding="utf-8"))


@app.get("/api/projects/{project_id}/artifacts")
async def get_artifacts(project_id: str):
    artifact_dir = storage.project_dir(project_id) / "output"
    result = {}
    for name in ("output.docx", "qa_report.json", "sources.json", "benchmark_compare.json", "transfer_report.json", "preview_manifest.json"):
        path = artifact_dir / name
        if path.exists():
            result[name] = str(path)
    return result


@app.get("/downloads/{project_id}/{artifact_name}")
async def download_artifact(project_id: str, artifact_name: str):
    if ".." in artifact_name or "/" in artifact_name or "\\" in artifact_name:
        raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
    results_path = storage.results_dir(project_id) / artifact_name
    output_path = storage.project_dir(project_id) / "output" / artifact_name
    if results_path.exists():
        path = results_path
    elif output_path.exists():
        path = output_path
    else:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path=str(path), filename=artifact_name)


@app.get("/preview/{project_id}/{page_name}")
async def preview_artifact(project_id: str, page_name: str):
    if "/" in page_name or "\\" in page_name:
        raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
    path = storage.project_dir(project_id) / "output" / "preview" / page_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="미리보기 파일을 찾을 수 없습니다.")
    return FileResponse(path=str(path), filename=page_name)


@app.get("/health")
async def health():
    payload = {
        "status": "ok",
        "ai_available": openai_service.available,
        "ai_provider": openai_service.provider,
        "status_text": openai_service.status_text,
    }
    # Backward compatibility for existing clients that read old key name.
    payload["openai_available"] = payload["ai_available"]
    return payload
