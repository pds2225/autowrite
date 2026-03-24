"""
bizplan_injector/core/__init__.py
"""
from .injector import BizPlanInjector, make_para, make_run, set_cell_text, set_cell_multiline
from .analyzer import analyze_docx, generate_content_skeleton
from .rich_formatter import format_rich_lines, rich_line_to_para, parse_inline_bold

# AI writer는 anthropic 패키지가 설치된 경우에만 로드
try:
    from .ai_writer import AIWriter, generate_from_company_info
    HAS_AI_WRITER = True
except ImportError:
    HAS_AI_WRITER = False

__all__ = [
    "BizPlanInjector",
    "analyze_docx",
    "generate_content_skeleton",
    "make_para",
    "make_run",
    "set_cell_text",
    "set_cell_multiline",
    "format_rich_lines",
    "rich_line_to_para",
    "parse_inline_bold",
    "AIWriter",
    "generate_from_company_info",
    "HAS_AI_WRITER",
]
