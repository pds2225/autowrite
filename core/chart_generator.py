#!/usr/bin/env python3
"""
chart_generator.py — 사업계획서 차트 자동 생성 모듈
-----------------------------------------------------
Phase 3: 기업정보(company_profile)를 바탕으로 4가지 차트를 생성하고
content.json의 "images" 섹션에 주입할 수 있는 경로 목록을 반환한다.

생성 차트:
  1. market_size  — TAM/SAM/SOM 수평 바 차트
  2. revenue      — 연차별 매출 추정 바 차트
  3. budget       — 사업비 구성 도넛 차트
  4. roadmap      — 성장 단계 타임라인 차트

사용 예::
    from core.chart_generator import generate_all_charts

    image_specs = generate_all_charts(profile, output_dir="output/charts")
    # content["images"].extend(image_specs)
"""

import os
import re

try:
    import matplotlib
    matplotlib.use("Agg")  # 헤드리스 환경
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib import rcParams
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ── 한국어 폰트 설정 ──────────────────────────────────────────────
def _setup_korean_font():
    """
    matplotlib 한국어 폰트를 설정한다.
    NanumGothic → WenQuanYi Zen Hei → DejaVu Sans 순서로 fallback한다.
    """
    if not HAS_MPL:
        return

    candidates = [
        "NanumGothic", "NanumBarunGothic", "Malgun Gothic",
        "Apple SD Gothic Neo", "Noto Sans CJK KR", "Noto Sans KR",
        # CJK fallback — 한국어 글리프 포함
        "WenQuanYi Zen Hei", "WenQuanYi Zen Hei Sharp",
        "AR PL UMing CN", "AR PL UKai CN",
    ]
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            rcParams["font.family"] = name
            rcParams["axes.unicode_minus"] = False
            return

    rcParams["axes.unicode_minus"] = False


_setup_korean_font()


# ── 숫자 파싱 헬퍼 ────────────────────────────────────────────────
def _parse_korean_amount(s) -> float:
    """
    한국어 금액 문자열을 숫자(억원)로 변환한다.

    지원 형식:
      "38억원"  → 38.0
      "1,644억원" → 1644.0
      "5,370억원" → 5370.0
      "100,000,000" → 1.0 (원 단위 → 억원 변환)
      1234 (int/float) → 0.01234 (원 → 억)

    Args:
        s: 금액 문자열 또는 숫자

    Returns:
        억원 단위 float
    """
    if isinstance(s, (int, float)):
        return s / 1e8  # 원 → 억원

    s = str(s).replace(",", "").strip()

    # "XX억원" 패턴
    m = re.search(r"([\d.]+)억", s)
    if m:
        return float(m.group(1))

    # "XX조원" 패턴
    m = re.search(r"([\d.]+)조", s)
    if m:
        return float(m.group(1)) * 10000

    # 순수 숫자 (원 단위 추정)
    m = re.search(r"[\d.]+", s)
    if m:
        val = float(m.group(0))
        # 1억 이상이면 원 단위로 간주
        if val >= 1e8:
            return val / 1e8
        return val

    return 0.0


def _parse_revenue(s) -> float:
    """growth_strategy.stages[].revenue 값을 억원 단위로 변환한다."""
    return _parse_korean_amount(s)


def _parse_budget_amount(v) -> float:
    """budget.items[].amount 값을 억원 단위로 변환한다."""
    if isinstance(v, (int, float)):
        return v / 1e8
    return _parse_korean_amount(v)


# ── 색상 팔레트 ───────────────────────────────────────────────────
COLORS = {
    "primary":   "#2563EB",   # blue-600
    "secondary": "#7C3AED",   # violet-600
    "accent":    "#059669",   # emerald-600
    "warn":      "#D97706",   # amber-600
    "muted":     "#6B7280",   # gray-500
    "light":     "#DBEAFE",   # blue-100
    "bg":        "#F8FAFC",   # slate-50
}

CHART_PALETTE = [
    "#2563EB", "#7C3AED", "#059669", "#D97706",
    "#DC2626", "#0891B2", "#DB2777", "#65A30D",
]


# ── 1. TAM/SAM/SOM 차트 ───────────────────────────────────────────
def generate_market_chart(profile: dict, output_path: str) -> str:
    """
    TAM/SAM/SOM 수평 바 차트를 생성한다.

    Args:
        profile:     기업정보 dict
        output_path: 저장할 PNG 파일 경로

    Returns:
        output_path (저장 성공) 또는 "" (matplotlib 없음 / 데이터 없음)
    """
    if not HAS_MPL:
        return ""

    market = profile.get("market", {})
    tam = _parse_korean_amount(market.get("tam", {}).get("value", "0"))
    sam = _parse_korean_amount(market.get("sam", {}).get("value", "0"))
    som = _parse_korean_amount(market.get("som", {}).get("value", "0"))

    if tam == 0 and sam == 0 and som == 0:
        return ""

    labels = ["TAM\n(전체 시장)", "SAM\n(유효 시장)", "SOM\n(목표 시장)"]
    values = [tam, sam, som]
    bar_colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"]]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])

    bars = ax.barh(labels, values, color=bar_colors, height=0.45, edgecolor="white", linewidth=1.5)

    # 값 레이블
    for bar, val in zip(bars, values):
        label = f"{val:,.0f}억원" if val >= 1 else f"{val*100:.1f}백만원"
        ax.text(
            bar.get_width() + max(values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center", ha="left",
            fontsize=10, fontweight="bold",
            color=COLORS["muted"],
        )

    ax.set_xlabel("시장 규모 (억원)", fontsize=10, color=COLORS["muted"])
    ax.set_title("목표 시장 규모 (TAM / SAM / SOM)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlim(0, max(values) * 1.25)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="x", colors=COLORS["muted"])
    ax.tick_params(axis="y", colors="#1E293B", labelsize=10)
    ax.xaxis.set_tick_params(width=0)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return output_path


# ── 2. 연차별 매출 차트 ───────────────────────────────────────────
def generate_revenue_chart(profile: dict, output_path: str) -> str:
    """
    성장 단계별 목표 매출 바 차트를 생성한다.

    Args:
        profile:     기업정보 dict
        output_path: 저장할 PNG 파일 경로

    Returns:
        output_path 또는 ""
    """
    if not HAS_MPL:
        return ""

    stages = profile.get("growth_strategy", {}).get("stages", [])
    if not stages:
        return ""

    labels = []
    values = []
    for s in stages:
        period = s.get("period", s.get("stage", ""))
        # "2026.03~2026.08" → "26.03~\n26.08" 형태로 줄바꿈
        short = period.replace("20", "")
        labels.append(f"{s.get('stage', '')}\n({short})")
        values.append(_parse_revenue(s.get("revenue", "0")))

    if all(v == 0 for v in values):
        return ""

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])

    x = range(len(labels))
    bar_colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"]][:len(labels)]
    bars = ax.bar(x, values, color=bar_colors, width=0.5, edgecolor="white", linewidth=1.5)

    # 값 레이블
    for bar, val in zip(bars, values):
        label = f"{val:,.1f}억원" if val >= 1 else f"{val*100:.0f}백만원"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            label,
            ha="center", va="bottom",
            fontsize=10, fontweight="bold",
            color=COLORS["muted"],
        )

    # 성장 화살표 연결선
    for i in range(len(values) - 1):
        ax.annotate(
            "",
            xy=(i + 1 - 0.25, values[i + 1] * 0.5),
            xytext=(i + 0.25, values[i] * 0.5),
            arrowprops=dict(arrowstyle="->", color=COLORS["muted"], lw=1.2),
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("매출 (억원)", fontsize=10, color=COLORS["muted"])
    ax.set_title("연차별 목표 매출 추정", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, max(values) * 1.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=COLORS["muted"])

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return output_path


# ── 3. 사업비 구성 도넛 차트 ─────────────────────────────────────
def generate_budget_chart(profile: dict, output_path: str) -> str:
    """
    정부지원금 vs 자기부담금 + 항목별 사업비 구성 도넛 차트를 생성한다.

    Args:
        profile:     기업정보 dict
        output_path: 저장할 PNG 파일 경로

    Returns:
        output_path 또는 ""
    """
    if not HAS_MPL:
        return ""

    budget = profile.get("budget", {})
    items = budget.get("items", [])
    if not items:
        return ""

    # 항목 집계 (같은 category 합산)
    category_totals: dict = {}
    for item in items:
        cat = item.get("category", "기타")
        amt = _parse_budget_amount(item.get("amount", 0))
        category_totals[cat] = category_totals.get(cat, 0) + amt

    labels = list(category_totals.keys())
    values = list(category_totals.values())
    total = sum(values)

    if total == 0:
        return ""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(COLORS["bg"])

    # ── 왼쪽: 항목별 도넛 차트 ──
    ax1.set_facecolor(COLORS["bg"])
    colors = CHART_PALETTE[:len(labels)]
    wedges, texts, autotexts = ax1.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(width=0.5, edgecolor="white", linewidth=2),
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
    for t in texts:
        t.set_fontsize(9)
    ax1.set_title("사업비 항목 구성", fontsize=12, fontweight="bold", pad=10)

    # 중앙 텍스트
    ax1.text(0, 0, f"총\n{total:.0f}억원" if total >= 1 else f"총\n{total*1e8/1e6:.0f}백만원",
             ha="center", va="center", fontsize=11, fontweight="bold", color="#1E293B")

    # ── 오른쪽: 정부/자기 분담 바 차트 ──
    ax2.set_facecolor(COLORS["bg"])
    gov = _parse_budget_amount(budget.get("government", 0))
    self_ = _parse_budget_amount(budget.get("self", 0))
    total2 = gov + self_ or total

    fund_labels = ["정부지원금", "자기부담금"]
    fund_values = [gov, self_]
    fund_colors = [COLORS["primary"], COLORS["accent"]]

    bars = ax2.bar(fund_labels, fund_values, color=fund_colors,
                   width=0.4, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, fund_values):
        pct = val / total2 * 100
        unit = f"{val:.0f}억원" if val >= 1 else f"{val*1e8/1e6:.0f}백만원"
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + total2 * 0.02,
                 f"{unit}\n({pct:.1f}%)",
                 ha="center", va="bottom", fontsize=10, fontweight="bold",
                 color=COLORS["muted"])

    ax2.set_ylim(0, max(fund_values) * 1.4)
    ax2.set_title("정부지원금 vs 자기부담금", fontsize=12, fontweight="bold", pad=10)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.tick_params(colors=COLORS["muted"])

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return output_path


# ── 4. 성장 로드맵 차트 ───────────────────────────────────────────
def generate_roadmap_chart(profile: dict, output_path: str) -> str:
    """
    성장 단계별 수평 타임라인(로드맵) 차트를 생성한다.

    Args:
        profile:     기업정보 dict
        output_path: 저장할 PNG 파일 경로

    Returns:
        output_path 또는 ""
    """
    if not HAS_MPL:
        return ""

    stages = profile.get("growth_strategy", {}).get("stages", [])
    if not stages:
        return ""

    n = len(stages)
    fig, ax = plt.subplots(figsize=(12, 3.5))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(-1.2, 1.8)
    ax.axis("off")

    stage_colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"]]

    # 연결선
    ax.plot([0, n - 1], [0, 0], color="#CBD5E1", linewidth=3, zorder=1)

    for i, s in enumerate(stages):
        color = stage_colors[i % len(stage_colors)]

        # 원형 노드
        circle = mpatches.Circle((i, 0), 0.18, color=color, zorder=3)
        ax.add_patch(circle)
        ax.text(i, 0, str(i + 1), ha="center", va="center",
                fontsize=11, fontweight="bold", color="white", zorder=4)

        # 단계명 (위)
        ax.text(i, 0.38, s.get("stage", f"{i+1}단계"),
                ha="center", va="bottom", fontsize=11,
                fontweight="bold", color="#1E293B")

        # 기간 (위)
        ax.text(i, 0.68, s.get("period", ""),
                ha="center", va="bottom", fontsize=8.5, color=COLORS["muted"])

        # 목표 (아래) — 긴 텍스트는 줄바꿈
        goal = s.get("goal", "")
        if len(goal) > 14:
            mid = len(goal) // 2
            # 공백 근처에서 자르기
            for k in range(mid, len(goal)):
                if goal[k] in (" ", "+", "·", ","):
                    goal = goal[:k] + "\n" + goal[k+1:]
                    break
        ax.text(i, -0.42, goal, ha="center", va="top",
                fontsize=9, color="#1E293B", linespacing=1.4)

        # 매출 목표
        revenue = s.get("revenue", "")
        if revenue:
            ax.text(i, -0.95, f"매출 {revenue}",
                    ha="center", va="top", fontsize=9,
                    fontweight="bold", color=color)

        # 단계별 박스
        rect = mpatches.FancyBboxPatch(
            (i - 0.42, -1.15), 0.84, 2.9,
            boxstyle="round,pad=0.05",
            linewidth=1.5, edgecolor=color,
            facecolor=color + "18",  # 투명도 hex
            zorder=0,
        )
        ax.add_patch(rect)

    ax.set_title("성장 단계별 로드맵", fontsize=13, fontweight="bold", pad=8)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return output_path


# ── 통합 생성 함수 ────────────────────────────────────────────────
def generate_all_charts(
    profile: dict,
    output_dir: str = "output/charts",
) -> list:
    """
    4가지 차트를 모두 생성하고 content.json "images" 섹션 형식으로 반환한다.

    Args:
        profile:    기업정보 dict
        output_dir: 차트 PNG 파일 저장 디렉토리

    Returns:
        content.json "images" 키에 바로 삽입 가능한 dict 목록::

            [
              {
                "keyword":    "1-2",     # 삽입 위치 (섹션 헤딩 키워드)
                "image_path": "output/charts/market_size.png",
                "width_cm":   14.0,
                "height_cm":  7.0,
                "align":      "center",
                "_label":     "TAM/SAM/SOM 시장 규모 차트"
              },
              ...
            ]

        matplotlib가 없거나 데이터가 없는 차트는 결과에서 제외됩니다.
    """
    if not HAS_MPL:
        print("  ⚠️  matplotlib 미설치 — 차트 생성을 건너뜁니다.")
        print("      pip install matplotlib 로 설치하세요.")
        return []

    program_type = profile.get("program_type", "초기창업패키지")
    # 양식별 섹션 키워드 매핑 (ai_writer.py SECTION_KEYWORDS와 동일)
    keyword_map = {
        "재도전성공패키지": {"1-2": "1 -2", "3-1": "3 -1", "3-2": "3 -2", "3-3": "3-3-3"},
    }.get(program_type, {})

    def _kw(base: str) -> str:
        return keyword_map.get(base, base)

    specs = [
        {
            "chart_fn":   generate_market_chart,
            "filename":   "market_size.png",
            "keyword":    _kw("1-2"),
            "width_cm":   14.0,
            "height_cm":  6.0,
            "_label":     "TAM/SAM/SOM 시장 규모 차트",
        },
        {
            "chart_fn":   generate_revenue_chart,
            "filename":   "revenue_forecast.png",
            "keyword":    _kw("3-1"),
            "width_cm":   12.0,
            "height_cm":  6.5,
            "_label":     "연차별 매출 추정 차트",
        },
        {
            "chart_fn":   generate_budget_chart,
            "filename":   "budget_breakdown.png",
            "keyword":    _kw("3-3"),
            "width_cm":   14.0,
            "height_cm":  6.0,
            "_label":     "사업비 구성 차트",
        },
        {
            "chart_fn":   generate_roadmap_chart,
            "filename":   "roadmap.png",
            "keyword":    _kw("3-2"),
            "width_cm":   15.0,
            "height_cm":  5.0,
            "_label":     "성장 단계 로드맵 차트",
        },
    ]

    results = []
    for spec in specs:
        output_path = os.path.join(output_dir, spec["filename"])
        saved = spec["chart_fn"](profile, output_path)
        if saved:
            results.append({
                "keyword":    spec["keyword"],
                "image_path": saved,
                "width_cm":   spec["width_cm"],
                "height_cm":  spec["height_cm"],
                "align":      "center",
                "_label":     spec["_label"],
            })
            print(f"  📊 차트 생성: {spec['_label']} → {saved}")
        else:
            print(f"  ⏭️  차트 건너뜀: {spec['_label']} (데이터 없음)")

    return results
