from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

from models import RenderCheckResult


def _find_soffice() -> str | None:
    candidates = [
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    return None


def render_docx_check(docx_path: str, output_dir: str, expected_page_max: int = 20) -> RenderCheckResult:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    soffice = _find_soffice()
    if not soffice:
        return RenderCheckResult(
            pdf_generated=False,
            pdf_path=None,
            page_count=None,
            warnings=["LibreOffice(soffice)를 찾지 못했습니다. DOCX->PDF 변환 불가"],
        )

    docx = Path(docx_path)
    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return RenderCheckResult(
            pdf_generated=False,
            pdf_path=None,
            page_count=None,
            warnings=[f"PDF 변환 실패: {exc.stderr.strip() or exc.stdout.strip() or exc}"],
        )

    pdf_path = out_dir / f"{docx.stem}.pdf"
    if not pdf_path.exists():
        return RenderCheckResult(False, None, None, warnings=["변환은 완료됐지만 PDF 파일을 찾지 못했습니다."])

    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    warnings: list[str] = []
    if page_count > expected_page_max:
        warnings.append("page count exceeds expected range")

    preview_paths: list[str] = []
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(pdf_path))
        for i in range(min(3, len(pdf))):
            page = pdf[i]
            bitmap = page.render(scale=1.2)
            pil_image = bitmap.to_pil()
            out = out_dir / f"page{i+1}.png"
            pil_image.save(out)
            preview_paths.append(str(out))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"썸네일 생성 실패: {exc}")

    return RenderCheckResult(
        pdf_generated=True,
        pdf_path=str(pdf_path),
        page_count=page_count,
        preview_paths=preview_paths,
        warnings=warnings,
    )
