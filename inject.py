#!/usr/bin/env python3
"""
inject.py  —  사업계획서 자동 주입 CLI
----------------------------------------
사용법:
    python inject.py --template template.docx --content content.json --output output.docx
    python inject.py --analyze template.docx
    python inject.py --skeleton template.docx
    python inject.py --ai --template template.docx --profile company_profile.yaml [--api-key KEY]
    python inject.py --ai-generate --template template.docx --profile company_profile.yaml [--output content.json]
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
      --ai              : AI가 content.json 생성 + 자동 주입 → 완성 DOCX
      --ai-generate     : AI가 content.json만 생성 (주입 없이)
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
  python inject.py --ai --template template.docx --profile company_profile.yaml
  python inject.py --ai-generate --profile company_profile.yaml --output content.json
        """,
    )
    parser.add_argument("--template",  "-t", help="원본 양식 DOCX 파일 경로")
    parser.add_argument("--content",   "-c", help="내용 JSON 파일 경로")
    parser.add_argument("--output",    "-o", help="출력 파일 경로 (기본: output/결과.docx)")
    parser.add_argument("--analyze",   "-a", metavar="DOCX", help="DOCX 구조 분석 (표/단락 목록 출력)")
    parser.add_argument("--skeleton",  "-s", metavar="DOCX", help="content.json 스켈레톤 자동 생성")
    parser.add_argument("--ai",        action="store_true", help="AI 모드: 기업정보 → content.json 생성 → DOCX 주입")
    parser.add_argument("--ai-generate", action="store_true", help="AI 생성 모드: content.json만 생성 (주입 없이)")
    parser.add_argument("--profile",   "-p", help="기업정보 파일 경로 (YAML/JSON)")
    parser.add_argument("--api-key",   help="Anthropic API 키 (미지정 시 ANTHROPIC_API_KEY 환경변수 사용)")
    parser.add_argument("--model",     default=None, help="Claude 모델명 (기본: claude-sonnet-4-20250514)")

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

    # ── AI 생성 모드 (content.json만) ─────────────────────────
    if args.ai_generate:
        _run_ai_generate(args)
        return

    # ── AI 모드 (생성 + 주입) ─────────────────────────────────
    if args.ai:
        _run_ai_inject(args)
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


def _run_ai_generate(args):
    """
    AI 생성 모드: 기업정보로 content.json을 생성한다 (주입 없이).
    """
    from core import load_company_profile, get_profile_summary, generate_content, save_content_json

    if not args.profile:
        print("❌ --ai-generate 모드에는 --profile 인수가 필요합니다")
        sys.exit(1)
    if not os.path.exists(args.profile):
        print(f"❌ 기업정보 파일 없음: {args.profile}")
        sys.exit(1)

    # .env 파일 로딩 (있으면)
    _load_dotenv()

    # API 키 확인
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ API 키가 필요합니다. --api-key 또는 ANTHROPIC_API_KEY 환경변수를 설정하세요")
        sys.exit(1)

    # 기업정보 로딩
    print(f"\n🤖 AI content.json 자동 생성 시작")
    profile = load_company_profile(args.profile)
    print(f"  기업정보: {get_profile_summary(profile)}")

    # AI 생성
    print(f"\n📝 Claude API로 섹션별 내용 생성 중...")
    kwargs = {"profile": profile, "api_key": api_key}
    if args.model:
        kwargs["model"] = args.model
    content = generate_content(**kwargs)

    # 저장
    output_path = args.output or "output/content_ai_generated.json"
    save_content_json(content, output_path)

    # 통계
    n_cells = len(content.get("table_cells", []))
    n_rows = len(content.get("table_rows", []))
    n_sections = len(content.get("sections", []))
    print(f"\n✅ AI 생성 완료!")
    print(f"  table_cells: {n_cells}개")
    print(f"  table_rows:  {n_rows}개")
    print(f"  sections:    {n_sections}개")
    print(f"  저장 위치:   {output_path}")


def _run_ai_inject(args):
    """
    AI 모드: 기업정보 → content.json 생성 → DOCX 주입 → 완성 파일 출력.
    """
    from core import load_company_profile, get_profile_summary, generate_content

    if not args.template:
        print("❌ --ai 모드에는 --template 인수가 필요합니다")
        sys.exit(1)
    if not args.profile:
        print("❌ --ai 모드에는 --profile 인수가 필요합니다")
        sys.exit(1)
    if not os.path.exists(args.template):
        print(f"❌ 템플릿 파일 없음: {args.template}")
        sys.exit(1)
    if not os.path.exists(args.profile):
        print(f"❌ 기업정보 파일 없음: {args.profile}")
        sys.exit(1)

    # .env 파일 로딩 (있으면)
    _load_dotenv()

    # API 키 확인
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ API 키가 필요합니다. --api-key 또는 ANTHROPIC_API_KEY 환경변수를 설정하세요")
        sys.exit(1)

    # 기업정보 로딩
    print(f"\n🤖 AI 사업계획서 자동 작성 시작")
    profile = load_company_profile(args.profile)
    print(f"  기업정보: {get_profile_summary(profile)}")
    print(f"  템플릿:   {args.template}")

    # AI 생성
    print(f"\n📝 Claude API로 섹션별 내용 생성 중...")
    kwargs = {"profile": profile, "api_key": api_key}
    if args.model:
        kwargs["model"] = args.model
    content = generate_content(**kwargs)

    # DOCX 주입
    print(f"\n🔧 생성된 내용을 DOCX에 주입 중...")
    output_path = args.output
    if not output_path:
        base = os.path.splitext(os.path.basename(args.template))[0]
        os.makedirs("output", exist_ok=True)
        output_path = f"output/{base}_AI완성.docx"

    inj = BizPlanInjector(args.template)
    inj.set_content(content)
    stats = inj.run()
    inj.save(output_path)

    size = os.path.getsize(output_path)
    print(f"\n✅ AI 사업계획서 완성!")
    print(f"  파일 크기: {size:,} bytes ({size // 1024} KB)")
    print(f"  파란 안내문구 제거: {stats['blue_removed']}개")
    print(f"  빈 단락 정리: {stats['empty_paras_removed']}개")
    print(f"  저장 위치: {output_path}")


def _load_dotenv():
    """
    .env 파일이 있으면 환경변수로 로딩한다 (python-dotenv 없이 간단 구현).
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


if __name__ == "__main__":
    main()
