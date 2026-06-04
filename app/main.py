from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from app.generator.content_writer import render_business_plan_text
from app.generator.field_mapper import map_input_to_sections
from app.models import PipelineResult
from app.validator.completeness_checker import check_empty_outputs, check_required_inputs
from app.validator.scoring import score_result
from app.validator.style_checker import check_style
from app.config import DEFAULT_SECTIONS

def run_pipeline(input_data: Dict[str, str], section_names: List[str] | None = None) -> PipelineResult:
    sections = section_names or DEFAULT_SECTIONS
    input_issues = check_required_inputs(input_data)

    raw_mapping = map_input_to_sections(input_data, sections)
    generated = {
        section: render_business_plan_text(section, raw_value, input_data)
        for section, raw_value in raw_mapping.items()
    }

    issues = [*input_issues, *check_empty_outputs(generated), *check_style(generated)]
    score = score_result(generated, issues)

    return PipelineResult(
        mapped_fields=generated,
        validation_issues=issues,
        score_breakdown=score,
    )

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoWrite: Business-plan generation pipeline")
    parser.add_argument("--input", required=True, help="Input JSON path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    return parser.parse_args()

def main() -> None:
    args = _parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Loading input from: {input_path}")
    try:
        if not input_path.exists():
            print(f"[!] Error: Input file not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        with input_path.open("r", encoding="utf-8") as f:
            input_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[!] Error: Invalid JSON format: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("[*] Running generation pipeline...")
    result = run_pipeline(input_data)

    payload = {
        "mapped_fields": result.mapped_fields,
        "validation_issues": [
            {"field": x.field, "severity": x.severity, "message": x.message}
            for x in result.validation_issues
        ],
        "score_breakdown": result.score_breakdown,
    }

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[+] Successfully saved output to: {output_path}")
        print(f"[+] Final Score: {result.score_breakdown.get('total_score', 0)} / 100")
    except Exception as e:
        print(f"[!] Error saving output: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
