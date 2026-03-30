#!/usr/bin/env python3
"""
inject.py  —  사업계획서 자동 주입 CLI
----------------------------------------
사용법:
    python inject.py --template template.docx --content content.json --output output.docx
    python inject.py --analyze template.docx
    python inject.py --skeleton template.docx
    python inject.py --generate company_info.json --base content.json --output ai_content.json
    python inject.py --validate --content content.json [--template template.docx]
    python inject.py --profile company_info.json --generate output/sections.json
"""

import argparse
import json
import sys
import os

# 패키지 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from core import BizPlanInjector, analyze_docx, generate_content_skeleton


def main():
    """
    사업계획서 자동 주입 CLI 진입점.

    실행 모드:
      --analyze  DOCX   : 표·단락 구조를 분석하여 콘솔에 출력
      --skeleton DOCX   : content.json 스켈레톤 파일 자동 생성
      --generate JSON   : AI로 사업계획서 콘텐츠 생성 (기업정보 JSON 입력)
      --validate        : content.json / profile 검증 리포트 생성
      --profile JSON    : 기업정보 정규화 후 AI 생성 (--generate와 함께 사용)
      --template + --content : JSON 내용을 양식 DOCX에 주입하여 출력

    종료 코드:
      0 — 정상 완료
      1 — 파일 없음 또는 필수 인수 누락
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
    parser.add_argument("--template",  "-t", help="원본 양식 DOCX 파일 경로")
    parser.add_argument("--content",   "-c", help="내용 JSON 파일 경로")
    parser.add_argument("--output",    "-o", help="출력 파일 경로 (기본: output/결과.docx)")
    parser.add_argument("--analyze",   "-a", metavar="DOCX", help="DOCX 구조 분석 (표/단락 목록 출력)")
    parser.add_argument("--skeleton",  "-s", metavar="DOCX", help="content.json 스켈레톤 자동 생성")
    parser.add_argument("--generate",  "-g", metavar="JSON", help="AI 콘텐츠 생성 (기업정보 JSON)")
    parser.add_argument("--validate",  "-V", action="store_true", help="content.json / profile 검증 리포트 생성")
    parser.add_argument("--profile",   "-p", help="기업정보 JSON/YAML (정규화 후 AI 생성에 사용)")
    parser.add_argument("--base",      "-b", help="기존 content.json (표 데이터 유지용, --generate와 함께 사용)")
    parser.add_argument("--api-key",   help="Anthropic API 키 (기본: ANTHROPIC_API_KEY 환경변수)")
    parser.add_argument("--model",     help="AI 모델 ID (기본: claude-sonnet-4-20250514)")
    parser.add_argument("--temperature", type=float, help="AI 생성 온도 (기본: 0.3)")

    args = parser.parse_args()

    # ── 분석 모드 ──────────────────────────────────────────────
    if args.analyze:
        if not os.path.exists(args.analyze):
            print(f"파일 없음: {args.analyze}")
            sys.exit(1)
        analyze_docx(args.analyze, verbose=True)
        return

    # ── 스켈레톤 생성 모드 ─────────────────────────────────────
    if args.skeleton:
        if not os.path.exists(args.skeleton):
            print(f"파일 없음: {args.skeleton}")
            sys.exit(1)
        out = args.output or "content_skeleton.json"
        generate_content_skeleton(args.skeleton, out)
        return

    # ── 검증 모드 ─────────────────────────────────────────────
    if args.validate:
        from core import validate_content, normalize_content, normalize_profile
        from core import generate_template_schema

        content = {}
        profile = None
        template_schema = None

        if args.content:
            if not os.path.exists(args.content):
                print(f"파일 없음: {args.content}")
                sys.exit(1)
            with open(args.content, encoding="utf-8") as f:
                raw_content = json.load(f)
            content = normalize_content(raw_content)

        if args.profile:
            if not os.path.exists(args.profile):
                print(f"파일 없음: {args.profile}")
                sys.exit(1)
            from core import load_and_normalize
            profile = load_and_normalize(args.profile)

        if args.template:
            if not os.path.exists(args.template):
                print(f"파일 없음: {args.template}")
                sys.exit(1)
            schema_path = args.output or "template_schema.json"
            template_schema = generate_template_schema(args.template, schema_path)

        report = validate_content(content, profile=profile, template_schema=template_schema)

        out_path = args.output or "validation_report.json"
        if not out_path.endswith(".json"):
            out_path = "validation_report.json"
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        s = report["summary"]
        status = "PASSED" if s["passed"] else "FAILED"
        print(f"\n검증 결과: {status}")
        print(f"  ERROR: {s['errors']}  WARNING: {s['warnings']}  INFO: {s['infos']}")
        for issue in report["issues"]:
            prefix = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(issue["level"], "")
            print(f"  {prefix} [{issue['level']}] {issue['code']}: {issue['message']}")
        print(f"\n리포트 저장: {out_path}")
        sys.exit(0 if s["passed"] else 1)

    # ── 프로필 정규화 + AI 생성 모드 ─────────────────────────
    if args.profile and args.generate:
        from core import load_and_normalize, normalize_profile
        if not os.path.exists(args.profile):
            print(f"파일 없음: {args.profile}")
            sys.exit(1)

        profile = load_and_normalize(args.profile)
        norm_path = "output/normalized_profile.json"
        os.makedirs("output", exist_ok=True)
        with open(norm_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"정규화된 프로필 저장: {norm_path}")

        try:
            from core import HAS_AI_WRITER
            if not HAS_AI_WRITER:
                raise ImportError
            from core.ai_writer import generate_from_company_info
        except ImportError:
            print("AI 생성 기능을 사용하려면 anthropic 패키지를 설치하세요:")
            print("  pip install anthropic")
            sys.exit(1)

        output_path = args.generate
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        generate_from_company_info(
            company_info_path=args.profile,
            base_content_path=args.base,
            output_path=output_path,
            api_key=args.api_key,
            verbose=True,
        )
        return

    # ── AI 콘텐츠 생성 모드 ───────────────────────────────────
    if args.generate:
        if not os.path.exists(args.generate):
            print(f"파일 없음: {args.generate}")
            sys.exit(1)

        try:
            from core import HAS_AI_WRITER
            if not HAS_AI_WRITER:
                raise ImportError
            from core.ai_writer import generate_from_company_info
        except ImportError:
            print("AI 생성 기능을 사용하려면 anthropic 패키지를 설치하세요:")
            print("  pip install anthropic")
            sys.exit(1)

        output_path = args.output or "output/ai_content.json"
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        generate_from_company_info(
            company_info_path=args.generate,
            base_content_path=args.base,
            output_path=output_path,
            api_key=args.api_key,
            verbose=True,
        )
        return

    # ── 주입 모드 ──────────────────────────────────────────────
    if not args.template or not args.content:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.template):
        print(f"템플릿 파일 없음: {args.template}")
        sys.exit(1)
    if not os.path.exists(args.content):
        print(f"내용 파일 없음: {args.content}")
        sys.exit(1)

    # 출력 경로
    output_path = args.output
    if not output_path:
        base = os.path.splitext(os.path.basename(args.template))[0]
        os.makedirs("output", exist_ok=True)
        output_path = f"output/{base}_완성.docx"

    print(f"\n사업계획서 자동 주입 시작")
    print(f"  템플릿: {args.template}")
    print(f"  내용:   {args.content}")
    print(f"  출력:   {output_path}")

    inj = BizPlanInjector(args.template)
    inj.load_content(args.content)
    stats = inj.run()
    inj.save(output_path)

    size = os.path.getsize(output_path)
    print(f"\n완성!")
    print(f"  파일 크기: {size:,} bytes ({size // 1024} KB)")
    print(f"  파란 안내문구 제거: {stats['blue_removed']}개")
    print(f"  빈 단락 정리: {stats['empty_paras_removed']}개")
    print(f"  저장 위치: {output_path}")


if __name__ == "__main__":
    main()
