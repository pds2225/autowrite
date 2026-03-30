#!/usr/bin/env python3
"""
inject.py  —  사업계획서 자동 주입 CLI
----------------------------------------
사용법:
    python inject.py --template template.docx --content content.json --output output.docx
    python inject.py --analyze template.docx
    python inject.py --skeleton template.docx --output content_skeleton.json
    python inject.py --generate company_info.json --base content.json --output ai_content.json
    python inject.py --validate --content content.json [--template template.docx]
    python inject.py --profile company_info.json --generate output/sections.json
"""

import argparse
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from core import BizPlanInjector, analyze_docx, generate_content_skeleton


# ── 헬퍼 ──────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """파일명에서 Windows/Unix 모두 금지된 특수문자를 제거한다."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip(". ")
    return name or "output"


def _require_file(path: str, label: str = "파일") -> None:
    """파일이 없으면 메시지 출력 후 종료한다."""
    if not os.path.exists(path):
        print(f"{label} 없음: {path}")
        sys.exit(1)


def _load_ai_writer():
    """
    anthropic 패키지가 설치된 경우에만 generate_from_company_info를 반환한다.
    설치되지 않은 경우 안내 메시지를 출력하고 종료한다.
    """
    try:
        from core import HAS_AI_WRITER
        if not HAS_AI_WRITER:
            raise ImportError
        from core.ai_writer import generate_from_company_info
        return generate_from_company_info
    except ImportError:
        print("AI 생성 기능을 사용하려면 anthropic 패키지를 설치하세요:")
        print("  pip install anthropic")
        sys.exit(1)


# ── 핵심 주입 함수 ─────────────────────────────────────────────────

def run_injection(
    template_path: str,
    content_path: str,
    output_path: str | None = None,
) -> dict:
    """
    DOCX 양식에 JSON 내용을 주입하고 결과 파일을 저장한다.

    Args:
        template_path: 원본 양식 DOCX 경로
        content_path:  주입할 내용 JSON 경로
        output_path:   저장 경로 (None 이면 output/<템플릿명>_완성.docx)

    Returns:
        {
          "output":   저장된 파일 경로,
          "size":     파일 크기 (bytes),
          "stats":    BizPlanInjector.run() 반환값,
          "warnings": 경고 메시지 목록,
        }
    """
    warnings: list[str] = []

    if not output_path:
        base = _sanitize_filename(os.path.splitext(os.path.basename(template_path))[0])
        os.makedirs("output", exist_ok=True)
        output_path = f"output/{base}_완성.docx"
    else:
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    inj = BizPlanInjector(template_path)
    inj.load_content(content_path)
    stats = inj.run()
    inj.save(output_path)

    if not os.path.exists(output_path):
        warnings.append(f"저장 후 파일을 확인할 수 없습니다: {output_path}")

    return {
        "output":   output_path,
        "size":     os.path.getsize(output_path) if os.path.exists(output_path) else 0,
        "stats":    stats,
        "warnings": warnings,
    }


# ── CLI 진입점 ────────────────────────────────────────────────────

def main():
    """
    사업계획서 자동 주입 CLI 진입점.

    실행 모드:
      --analyze  DOCX            : 표·단락 구조를 분석하여 콘솔에 출력
      --skeleton DOCX            : content.json 스켈레톤 파일 자동 생성
      --generate JSON            : AI로 사업계획서 콘텐츠 생성 (기업정보 JSON 입력)
      --validate                 : content.json / profile 검증 리포트 생성
      --profile JSON --generate P: 기업정보 정규화 후 AI 생성
      --template + --content     : JSON 내용을 양식 DOCX에 주입하여 출력

    종료 코드:
      0 — 정상 완료
      1 — 파일 없음, 필수 인수 누락, 또는 검증 실패(--validate)
    """
    parser = argparse.ArgumentParser(
        description="사업계획서 DOCX 자동 주입 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python inject.py --template template.docx --content content.json
  python inject.py --analyze template.docx
  python inject.py --skeleton template.docx --output content_skeleton.json
  python inject.py --generate company_info.json --base content.json --output ai_content.json
  python inject.py --validate --content content.json --template template.docx
  python inject.py --profile company_info.json --generate output/sections.json
        """,
    )
    parser.add_argument("--template",    "-t", help="원본 양식 DOCX 파일 경로")
    parser.add_argument("--content",     "-c", help="내용 JSON 파일 경로")
    parser.add_argument("--output",      "-o", help="출력 파일 경로 (기본: output/결과.docx)")
    parser.add_argument("--analyze",     "-a", metavar="DOCX", help="DOCX 구조 분석 (표/단락 목록 출력)")
    parser.add_argument("--skeleton",    "-s", metavar="DOCX", help="content.json 스켈레톤 자동 생성")
    parser.add_argument("--generate",    "-g", metavar="JSON", help="AI 콘텐츠 생성 (기업정보 JSON)")
    parser.add_argument("--validate",    "-V", action="store_true", help="content.json / profile 검증 리포트 생성")
    parser.add_argument("--profile",     "-p", help="기업정보 JSON (정규화 후 AI 생성에 사용)")
    parser.add_argument("--base",        "-b", help="기존 content.json (표 데이터 유지용, --generate와 함께 사용)")
    parser.add_argument("--api-key",           help="Anthropic API 키 (기본: ANTHROPIC_API_KEY 환경변수)")
    parser.add_argument("--model",             help="AI 모델 ID (기본: claude-sonnet-4-20250514)")
    parser.add_argument("--temperature", type=float, help="AI 생성 온도 (기본: 0.3)")

    args = parser.parse_args()

    # ── 분석 모드 ──────────────────────────────────────────────
    if args.analyze:
        _require_file(args.analyze, "분석 대상 파일")
        analyze_docx(args.analyze, verbose=True)
        return

    # ── 스켈레톤 생성 모드 ─────────────────────────────────────
    if args.skeleton:
        _require_file(args.skeleton, "스켈레톤 대상 파일")
        out = args.output or "output/content_skeleton.json"
        os.makedirs("output", exist_ok=True)
        generate_content_skeleton(args.skeleton, out)
        return

    # ── 검증 모드 ─────────────────────────────────────────────
    if args.validate:
        from core import validate_content, normalize_content, generate_template_schema, load_and_normalize

        content = {}
        profile = None
        template_schema = None

        if args.content:
            _require_file(args.content, "content JSON")
            with open(args.content, encoding="utf-8") as f:
                content = normalize_content(json.load(f))

        if args.profile:
            _require_file(args.profile, "profile JSON")
            profile = load_and_normalize(args.profile)

        if args.template:
            _require_file(args.template, "템플릿 파일")
            # schema 저장 경로는 output과 독립적으로 고정
            os.makedirs("output", exist_ok=True)
            template_schema = generate_template_schema(args.template, "output/template_schema.json")

        report = validate_content(content, profile=profile, template_schema=template_schema)

        report_path = args.output if (args.output and args.output.endswith(".json")) \
                      else "validation_report.json"
        os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        s = report["summary"]
        status = "PASSED" if s["passed"] else "FAILED"
        print(f"\n검증 결과: {status}")
        print(f"  ERROR: {s['errors']}  WARNING: {s['warnings']}  INFO: {s['infos']}")
        for issue in report["issues"]:
            prefix = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(issue["level"], "")
            print(f"  {prefix} [{issue['level']}] {issue['code']}: {issue['message']}")
        print(f"\n리포트 저장: {report_path}")
        sys.exit(0 if s["passed"] else 1)

    # ── 프로필 정규화 + AI 생성 모드 ─────────────────────────
    if args.profile and args.generate:
        _require_file(args.profile, "profile JSON")
        from core import load_and_normalize

        profile = load_and_normalize(args.profile)
        os.makedirs("output", exist_ok=True)
        norm_path = "output/normalized_profile.json"
        with open(norm_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"정규화된 프로필 저장: {norm_path}")

        gen_fn = _load_ai_writer()
        out = args.generate
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        gen_fn(
            company_info_path=args.profile,
            base_content_path=args.base,
            output_path=out,
            api_key=args.api_key,
            verbose=True,
        )
        return

    # ── AI 콘텐츠 생성 모드 ───────────────────────────────────
    if args.generate:
        _require_file(args.generate, "기업정보 JSON")
        gen_fn = _load_ai_writer()
        out = args.output or "output/ai_content.json"
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        gen_fn(
            company_info_path=args.generate,
            base_content_path=args.base,
            output_path=out,
            api_key=args.api_key,
            verbose=True,
        )
        return

    # ── 주입 모드 ──────────────────────────────────────────────
    if not args.template or not args.content:
        parser.print_help()
        sys.exit(1)

    _require_file(args.template, "템플릿 파일")
    _require_file(args.content,  "내용 파일")

    print(f"\n사업계획서 자동 주입 시작")
    print(f"  템플릿: {args.template}")
    print(f"  내용:   {args.content}")

    result = run_injection(args.template, args.content, args.output)

    print(f"  출력:   {result['output']}")
    print(f"\n완성!")
    print(f"  파일 크기: {result['size']:,} bytes ({result['size'] // 1024} KB)")
    print(f"  파란 안내문구 제거: {result['stats']['blue_removed']}개")
    print(f"  빈 단락 정리: {result['stats']['empty_paras_removed']}개")
    print(f"  저장 위치: {result['output']}")
    for w in result["warnings"]:
        print(f"  경고: {w}")


if __name__ == "__main__":
    main()
