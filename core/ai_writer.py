#!/usr/bin/env python3
"""
ai_writer.py — AI 기반 content.json 자동 생성 모듈
----------------------------------------------------
Claude API를 호출하여 기업정보(company_profile)를 바탕으로
사업계획서 content.json을 섹션별로 생성한다.
"""

import json
import os
import re
import time

import anthropic


# === 상수 ===

PROMPT_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "prompt_templates")
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초

# 섹션 키워드 매핑 (양식별 차이 대응)
SECTION_KEYWORDS = {
    "재도전성공패키지": {
        "1-1": "1 -1",
        "1-2": "1 -2",
        "3-3": "3-3-3",
        "4-1": "4-1 -1",
    },
    "초기창업패키지": {
        "1-1": "1-1",
        "1-2": "1-2",
        "3-3": "3-3",
        "4-1": "4-1",
    },
    "예비창업패키지": {
        "1-1": "1-1",
        "1-2": "1-2",
        "3-3": "3-3",
        "4-1": "4-1",
    },
}


def _load_template(name: str) -> str:
    """
    프롬프트 템플릿 파일을 로딩한다.

    Args:
        name: 템플릿 파일명 (확장자 포함)

    Returns:
        템플릿 문자열
    """
    path = os.path.join(PROMPT_TEMPLATES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _get_keyword(section: str, program_type: str) -> str:
    """
    양식 유형에 따른 섹션 키워드를 반환한다.

    Args:
        section: 섹션 코드 (예: "1-1", "3-3")
        program_type: 사업유형

    Returns:
        실제 키워드 문자열
    """
    mapping = SECTION_KEYWORDS.get(program_type, {})
    return mapping.get(section, section)


def _format_number(n) -> str:
    """숫자를 한국식 포맷으로 변환한다 (예: 100000000 → '100,000,000')."""
    if isinstance(n, (int, float)):
        return f"{int(n):,}"
    return str(n)


def _safe_get(d: dict, *keys, default=""):
    """중첩 dict에서 안전하게 값을 추출한다."""
    current = d
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    if current is None:
        return default
    return current


def _extract_json(text: str) -> dict:
    """
    LLM 응답에서 JSON을 추출한다.
    코드블록(```json ... ```) 안에 있을 수도 있고, 순수 JSON일 수도 있다.

    Args:
        text: LLM 응답 문자열

    Returns:
        파싱된 dict

    Raises:
        json.JSONDecodeError: JSON 파싱 실패
    """
    # ```json ... ``` 패턴 시도
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # { ... } 패턴 시도 (가장 바깥쪽 중괄호)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    # 전체 텍스트를 JSON으로 파싱 시도
    return json.loads(text)


def _call_llm(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Claude API를 호출하고 JSON 응답을 반환한다.
    API 실패 및 JSON 파싱 실패 시 최대 3회 재시도한다.

    Args:
        client: anthropic.Anthropic 클라이언트
        system_prompt: 시스템 프롬프트
        user_prompt: 사용자 프롬프트
        model: 모델명

    Returns:
        파싱된 JSON dict

    Raises:
        RuntimeError: 재시도 횟수 초과
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            result = _extract_json(text)
            return result

        except anthropic.APIError as e:
            last_error = e
            print(f"  ⚠️  API 오류 (시도 {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

        except json.JSONDecodeError as e:
            last_error = e
            print(f"  ⚠️  JSON 파싱 실패 (시도 {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(
        f"LLM 호출 실패 ({MAX_RETRIES}회 시도): {last_error}"
    )


# === 섹션별 프롬프트 빌더 ===

def _build_overview_prompt(profile: dict) -> str:
    """과제개요 표 프롬프트를 생성한다."""
    template = _load_template("overview_table.txt")
    return template.format(
        company_name=profile.get("company_name", ""),
        representative=profile.get("representative", ""),
        business_number=profile.get("business_number", ""),
        establishment_date=profile.get("establishment_date", ""),
        item_name=profile.get("item_name", ""),
        program_type=profile.get("program_type", ""),
        business_type=profile.get("business_type", ""),
        solution_description=_safe_get(profile, "solution", "description"),
    )


def _build_closure_prompt(profile: dict) -> str:
    """폐업이력 표 프롬프트를 생성한다."""
    template = _load_template("closure_history.txt")
    ch = profile.get("closure_history", [])
    ch_text = ""
    first = ch[0] if ch else {}
    for i, entry in enumerate(ch):
        ch_text += f"\n### 폐업이력 {i+1}\n"
        ch_text += f"- 기업명: {entry.get('company_name', '')}\n"
        ch_text += f"- 유형: {entry.get('type', '')}\n"
        ch_text += f"- 기간: {entry.get('period', '')}\n"
        ch_text += f"- 아이템: {entry.get('item', '')}\n"
        ch_text += f"- 폐업사유: {entry.get('reason', '')}\n"
        ch_text += f"- 원인분석: {entry.get('analysis', '')}\n"
        ch_text += f"- 개선방안: {entry.get('improvement', '')}\n"

    return template.format(
        closure_history_text=ch_text,
        first_company_name=first.get("company_name", ""),
        first_type=first.get("type", ""),
        first_period=first.get("period", ""),
        first_item=first.get("item", ""),
        first_reason=first.get("reason", ""),
    )


def _build_section_prompt(
    section_id: str, profile: dict
) -> str:
    """
    섹션별 프롬프트를 생성한다.

    Args:
        section_id: 섹션 코드 (예: "1_1", "3_1")
        profile: 기업정보 dict

    Returns:
        포맷된 프롬프트 문자열
    """
    template = _load_template(f"section_{section_id}.txt")
    p = profile  # 축약

    # 공통 변수
    common = {
        "company_name": p.get("company_name", ""),
        "representative": p.get("representative", ""),
        "item_name": p.get("item_name", ""),
        "program_type": p.get("program_type", ""),
        "business_type": p.get("business_type", ""),
        "target_customer": _safe_get(p, "problem", "target_customer"),
    }

    # 섹션별 추가 변수
    if section_id == "1_1":
        problem = p.get("problem", {})
        closure = p.get("closure_history", [])
        closure_text = ""
        if closure:
            for entry in closure:
                closure_text += f"- 기업: {entry.get('company_name', '')}\n"
                closure_text += f"  원인분석: {entry.get('analysis', '')}\n"
                closure_text += f"  개선방안: {entry.get('improvement', '')}\n"
        else:
            closure_text = "해당 없음"

        common.update({
            "problem_text": f"배경: {problem.get('background', '')}\n필요성: {problem.get('market_need', '')}",
            "closure_text": closure_text,
            "solution_text": _safe_get(p, "solution", "description"),
        })

    elif section_id == "1_2":
        market = p.get("market", {})
        competitors = market.get("competitors", [])
        comp_text = ""
        for c in competitors:
            comp_text += f"- {c.get('name', '')}: {c.get('features', '')} (약점: {c.get('weakness', '')})\n"
        tam = market.get("tam", {})
        sam = market.get("sam", {})
        som = market.get("som", {})
        common.update({
            "tam_value": tam.get("value", ""),
            "tam_basis": tam.get("basis", ""),
            "sam_value": sam.get("value", ""),
            "sam_basis": sam.get("basis", ""),
            "som_value": som.get("value", ""),
            "som_basis": som.get("basis", ""),
            "competitors_text": comp_text,
        })

    elif section_id == "2_1":
        sol = p.get("solution", {})
        team = p.get("team", {})
        current = team.get("current", [])
        team_text = ""
        for m in current:
            team_text += f"- {m.get('name', '')}: {m.get('role', '')} — {m.get('background', '')}\n"
        assets = p.get("assets", {})
        assets_text = ""
        for key in ["patents", "certifications", "achievements"]:
            items = assets.get(key, [])
            if items:
                assets_text += f"- {key}: {', '.join(items)}\n"

        common.update({
            "solution_text": sol.get("description", ""),
            "tech_stack": sol.get("tech_stack", ""),
            "development_status": sol.get("development_status", ""),
            "team_text": team_text,
            "assets_text": assets_text,
        })

    elif section_id == "2_2":
        sol = p.get("solution", {})
        features = sol.get("features", [])
        features_text = ""
        for f in features:
            features_text += f"- {f.get('name', '')}: {f.get('detail', '')}\n"
        diff = sol.get("differentiators", [])
        diff_text = "\n".join(f"- {d}" for d in diff) if diff else ""

        common.update({
            "solution_text": sol.get("description", ""),
            "features_text": features_text,
            "tech_stack": sol.get("tech_stack", ""),
            "differentiators_text": diff_text,
        })

    elif section_id == "3_1":
        bm = p.get("business_model", {})
        streams = bm.get("revenue_streams", [])
        bm_text = f"가격: {bm.get('pricing', '')}\n수익원:\n"
        for s in streams:
            bm_text += f"- {s.get('type', '')}: {s.get('detail', '')} (대상: {s.get('target', '')})\n"
        market = p.get("market", {})

        common.update({
            "business_model_text": bm_text,
            "tam_value": _safe_get(market, "tam", "value"),
            "sam_value": _safe_get(market, "sam", "value"),
            "som_value": _safe_get(market, "som", "value"),
        })

    elif section_id == "3_2":
        gs = p.get("growth_strategy", {})
        stages = gs.get("stages", [])
        gs_text = ""
        for s in stages:
            gs_text += f"- {s.get('stage', '')}: {s.get('period', '')} — {s.get('goal', '')} (매출 {s.get('revenue', '')})\n"

        common.update({
            "growth_strategy_text": gs_text,
            "solution_text": _safe_get(p, "solution", "description"),
            "target_customer": _safe_get(p, "problem", "target_customer"),
        })

    elif section_id == "3_3":
        budget = p.get("budget", {})
        items = budget.get("items", [])
        items_text = ""
        for item in items:
            items_text += f"- {item.get('category', '')}: {item.get('detail', '')} — {_format_number(item.get('amount', 0))}원\n"
        gs = p.get("growth_strategy", {})
        stages = gs.get("stages", [])
        gs_text = ""
        for s in stages:
            gs_text += f"- {s.get('stage', '')}: {s.get('period', '')} — {s.get('goal', '')}\n"

        common.update({
            "budget_total": _format_number(budget.get("total", 0)),
            "budget_government": _format_number(budget.get("government", 0)),
            "budget_government_formatted": _format_number(budget.get("government", 0)),
            "budget_self": _format_number(budget.get("self", 0)),
            "budget_items_text": items_text,
            "growth_stages_text": gs_text,
        })

    elif section_id == "4_1":
        team = p.get("team", {})
        current = team.get("current", [])
        current_text = ""
        for m in current:
            current_text += f"- {m.get('name', '')}: {m.get('role', '')} — {m.get('background', '')}\n"
        assets = p.get("assets", {})
        assets_text = ""
        for key in ["patents", "certifications", "achievements"]:
            items = assets.get(key, [])
            if items:
                assets_text += f"- {key}: {', '.join(items)}\n"

        common.update({
            "current_team_text": current_text,
            "assets_text": assets_text,
        })

    elif section_id == "4_2":
        team = p.get("team", {})
        planned = team.get("planned", [])
        planned_text = ""
        for m in planned:
            planned_text += f"- {m.get('role', '')} ({m.get('timing', '')}): {m.get('requirements', '')}\n"
        assets = p.get("assets", {})
        partnerships = assets.get("partnerships", [])
        part_text = "\n".join(f"- {p_}" for p_ in partnerships) if partnerships else "없음"

        common.update({
            "planned_team_text": planned_text,
            "partnerships_text": part_text,
        })

    return template.format(**common)


# === 메인 함수 ===

def generate_content(
    profile: dict,
    api_key: str = None,
    model: str = DEFAULT_MODEL,
    charts: bool = False,
    charts_dir: str = "output/charts",
) -> dict:
    """
    기업정보를 바탕으로 content.json 전체를 AI로 생성한다.
    섹션별로 개별 LLM 호출을 수행한다.

    Args:
        profile:    기업정보 dict (company_profile.yaml 로딩 결과)
        api_key:    Anthropic API 키 (None이면 환경변수 사용)
        model:      Claude 모델명
        charts:     True이면 차트 자동 생성 후 images 섹션에 추가 (Phase 3)
        charts_dir: 차트 PNG 저장 디렉토리 (charts=True일 때 사용)

    Returns:
        content.json 호환 dict

    Raises:
        RuntimeError: API 호출 실패
    """
    # API 키 설정
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용

    system_prompt = _load_template("system_prompt.txt")
    program_type = profile.get("program_type", "초기창업패키지")

    # 결과 구조 초기화
    content = {
        "_comment": f"AI 자동생성 content.json — {profile.get('company_name', '')} ({program_type})",
        "delete_tables": [0],
        "table_cells": [],
        "table_rows": [],
        "sections": [],
        "images": [],
    }

    # === 호출 1: 과제개요 표 (table_cells) ===
    print("  📝 [1/11] 과제개요 표 생성 중...")
    try:
        prompt = _build_overview_prompt(profile)
        result = _call_llm(client, system_prompt, prompt, model)
        if "table_cells" in result:
            content["table_cells"].extend(result["table_cells"])
        print("  ✅ 과제개요 표 완료")
    except RuntimeError as e:
        print(f"  ❌ 과제개요 표 실패: {e}")

    # === 호출 2: 폐업이력 표 (재도전성공패키지 전용) ===
    if program_type == "재도전성공패키지":
        print("  📝 [2/11] 폐업이력 표 생성 중...")
        try:
            prompt = _build_closure_prompt(profile)
            result = _call_llm(client, system_prompt, prompt, model)
            if "table_rows" in result:
                content["table_rows"].extend(result["table_rows"])
            print("  ✅ 폐업이력 표 완료")
        except RuntimeError as e:
            print(f"  ❌ 폐업이력 표 실패: {e}")
    else:
        print("  ⏭️  [2/11] 폐업이력 표 건너뜀 (재도전 전용)")

    # === 호출 3~11: 섹션별 생성 ===
    section_configs = [
        ("1_1", "1-1", "문제인식/배경", 3),
        ("1_2", "1-2", "목표시장분석", 4),
        ("2_1", "2-1", "준비현황/아이템", 5),
        ("2_2", "2-2", "실현/구체화방안", 6),
        ("3_1", "3-1", "비즈니스모델", 7),
        ("3_2", "3-2", "사업화전략", 8),
        ("3_3", "3-3", "추진일정/자금", 9),
        ("4_1", "4-1", "조직구성/역량", 10),
        ("4_2", "4-2", "조직구성계획", 11),
    ]

    for file_id, section_code, label, call_num in section_configs:
        print(f"  📝 [{call_num}/11] {label} 섹션 생성 중...")
        try:
            prompt = _build_section_prompt(file_id, profile)
            result = _call_llm(client, system_prompt, prompt, model)

            # 섹션 결과 처리
            if "sections" in result:
                keyword = _get_keyword(section_code, program_type)
                for sec in result["sections"]:
                    sec["keyword"] = keyword
                content["sections"].extend(result["sections"])

            # table_rows가 있으면 추가 (3-3, 4-1, 4-2에서 표 데이터 포함 가능)
            if "table_rows" in result:
                content["table_rows"].extend(result["table_rows"])

            print(f"  ✅ {label} 완료")
        except RuntimeError as e:
            print(f"  ❌ {label} 실패: {e}")

    # === Phase 3: 차트 자동 생성 ===
    if charts:
        print("\n  📊 [Phase 3] 차트 자동 생성 중...")
        try:
            from .chart_generator import generate_all_charts
            image_specs = generate_all_charts(profile, output_dir=charts_dir)
            content["images"].extend(image_specs)
            print(f"  ✅ 차트 생성 완료: {len(image_specs)}개")
        except Exception as e:
            print(f"  ❌ 차트 생성 실패: {e}")

    return content


def save_content_json(content: dict, output_path: str) -> None:
    """
    content.json을 파일로 저장한다.

    Args:
        content: content.json dict
        output_path: 저장 경로
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    print(f"  💾 저장 완료: {output_path}")
