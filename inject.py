#!/usr/bin/env python3
"""
inject.py  —  사업계획서 자동 주입 CLI
----------------------------------------
사용법:
    python inject.py --template template.docx --content content.json --output output.docx
    python inject.py --analyze template.docx
    python inject.py --skeleton template.docx
"""

import argparse
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
        """,
    )
    parser.add_argument("--template",  "-t", help="원본 양식 DOCX 파일 경로")
    parser.add_argument("--content",   "-c", help="내용 JSON 파일 경로")
    parser.add_argument("--output",    "-o", help="출력 파일 경로 (기본: output/결과.docx)")
    parser.add_argument("--analyze",   "-a", metavar="DOCX", help="DOCX 구조 분석 (표/단락 목록 출력)")
    parser.add_argument("--skeleton",  "-s", metavar="DOCX", help="content.json 스켈레톤 자동 생성")

    args = parser.parse_args()

    # ── 분석 모드 ──────────────────────────────────────────────
    if args.analyze:
        if not os.path.exists(args.analyze):
            print(f"❌ 파일 없음: {args.analyze}")
            sys.exit(1)
        analyze_docx(args.analyze, verbose=True)
        return

    # ── 스켈레톤 생성 모드 ─────────────────────────────────────
    if args.skeleton:
        if not os.path.exists(args.skeleton):
            print(f"❌ 파일 없음: {args.skeleton}")
            sys.exit(1)
        out = args.output or "content_skeleton.json"
        generate_content_skeleton(args.skeleton, out)
        return

    # ── 주입 모드 ──────────────────────────────────────────────
    if not args.template or not args.content:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.template):
        print(f"❌ 템플릿 파일 없음: {args.template}")
        sys.exit(1)
    if not os.path.exists(args.content):
        print(f"❌ 내용 파일 없음: {args.content}")
        sys.exit(1)

    # 출력 경로
    output_path = args.output
    if not output_path:
        base = os.path.splitext(os.path.basename(args.template))[0]
        os.makedirs("output", exist_ok=True)
        output_path = f"output/{base}_완성.docx"

    print(f"\n🚀 사업계획서 자동 주입 시작")
    print(f"  템플릿: {args.template}")
    print(f"  내용:   {args.content}")
    print(f"  출력:   {output_path}")

    inj = BizPlanInjector(args.template)
    inj.load_content(args.content)
    stats = inj.run()
    inj.save(output_path)

    size = os.path.getsize(output_path)
    print(f"\n✅ 완성!")
    print(f"  파일 크기: {size:,} bytes ({size // 1024} KB)")
    print(f"  파란 안내문구 제거: {stats['blue_removed']}개")
    print(f"  빈 단락 정리: {stats['empty_paras_removed']}개")
    print(f"  저장 위치: {output_path}")


if __name__ == "__main__":
    main()
