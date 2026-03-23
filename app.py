from __future__ import annotations

import argparse
from pathlib import Path

from injector import DocxInjectionEngine
from parser import analyze_template
from postprocess import cleanup_guidance_phrases, remove_tail_reference_block, remove_toc_block
from render_check import render_docx_check
from utils import WarningCollector, load_json, save_json, setup_logger


def run_pipeline(
    template: str,
    content_path: str,
    tables_path: str,
    images_path: str,
    output_docx: str,
    output_dir: str,
) -> None:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(out_dir / "logs" / "engine.log")
    warnings = WarningCollector()

    parsed = analyze_template(template)
    save_json(parsed.to_dict(), out_dir / "parsed_template.json")
    logger.info("template analyzed")

    content = load_json(content_path)
    tables = load_json(tables_path)
    images = load_json(images_path)

    engine = DocxInjectionEngine(template, parsed, warnings)
    engine.inject_sections(content)
    engine.inject_tables(tables)
    engine.inject_images(images, image_root=str(Path(images_path).parent))

    cleanup_guidance_phrases(engine.document, warnings)
    remove_toc_block(engine.document, warnings)
    remove_tail_reference_block(engine.document, warnings)

    engine.save(output_docx)
    save_json(warnings.to_list(), out_dir / "warnings.json")
    logger.info("docx saved")

    render = render_docx_check(output_docx, output_dir)
    save_json(render.to_dict(), out_dir / "render_check.json")
    logger.info("render check complete")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DOCX 양식 주입 안정화 엔진")
    parser.add_argument("--template", required=True)
    parser.add_argument("--content", required=True, help="content_master.json")
    parser.add_argument("--tables", required=True, help="tables.json")
    parser.add_argument("--images", required=True, help="images_manifest.json")
    parser.add_argument("--output-docx", default="output/result.docx")
    parser.add_argument("--output-dir", default="output")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.template, args.content, args.tables, args.images, args.output_docx, args.output_dir)
