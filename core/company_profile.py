#!/usr/bin/env python3
"""
company_profile.py — 기업정보 YAML/JSON 로더 및 검증 모듈
----------------------------------------------------------
company_profile.yaml 또는 .json 파일을 로딩하고,
필수/선택 필드를 검증하여 dict로 반환한다.
"""

import json
import os

import yaml


# === 스키마 정의 ===

REQUIRED_FIELDS = [
    "company_name",
    "representative",
    "item_name",
    "program_type",
]

OPTIONAL_FIELDS = [
    "business_number",
    "establishment_date",
    "business_type",
    "problem",
    "closure_history",
    "solution",
    "market",
    "business_model",
    "growth_strategy",
    "budget",
    "team",
    "assets",
]

VALID_PROGRAM_TYPES = [
    "재도전성공패키지",
    "초기창업패키지",
    "예비창업패키지",
    "기타",
]


def load_company_profile(path: str) -> dict:
    """
    기업정보 파일(YAML/JSON)을 로딩하고 검증한다.

    Args:
        path: 기업정보 파일 경로 (.yaml, .yml, .json)

    Returns:
        검증된 기업정보 dict

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: 필수 필드 누락 또는 잘못된 값
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"기업정보 파일 없음: {path}")

    ext = os.path.splitext(path)[1].lower()

    with open(path, "r", encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            profile = yaml.safe_load(f)
        elif ext == ".json":
            profile = json.load(f)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {ext} (.yaml, .yml, .json만 지원)")

    if not isinstance(profile, dict):
        raise ValueError("기업정보 파일이 올바른 dict 형식이 아닙니다")

    _validate_profile(profile)
    return profile


def _validate_profile(profile: dict) -> None:
    """
    기업정보 필수 필드를 검증한다.

    Args:
        profile: 기업정보 dict

    Raises:
        ValueError: 필수 필드 누락 또는 잘못된 값
    """
    # 필수 필드 검증
    missing = [f for f in REQUIRED_FIELDS if not profile.get(f)]
    if missing:
        raise ValueError(f"필수 필드 누락: {', '.join(missing)}")

    # program_type 검증
    pt = profile.get("program_type", "")
    if pt not in VALID_PROGRAM_TYPES:
        raise ValueError(
            f"잘못된 program_type: '{pt}' "
            f"(허용값: {', '.join(VALID_PROGRAM_TYPES)})"
        )

    # 재도전성공패키지는 closure_history 필수
    if pt == "재도전성공패키지":
        ch = profile.get("closure_history")
        if not ch or not isinstance(ch, list) or len(ch) == 0:
            raise ValueError(
                "재도전성공패키지는 closure_history (폐업이력) 필수입니다"
            )


def get_profile_summary(profile: dict) -> str:
    """
    기업정보 요약 문자열을 반환한다 (로그 출력용).

    Args:
        profile: 기업정보 dict

    Returns:
        한 줄 요약 문자열
    """
    name = profile.get("company_name", "?")
    item = profile.get("item_name", "?")
    ptype = profile.get("program_type", "?")
    return f"{name} | {item} | {ptype}"
