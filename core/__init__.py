"""
bizplan_injector/core/__init__.py
"""
from .injector import BizPlanInjector, make_para, make_run, set_cell_text, set_cell_multiline
from .analyzer import analyze_docx, generate_content_skeleton
from .company_profile import load_company_profile, get_profile_summary
from .ai_writer import generate_content, save_content_json

__all__ = [
    "BizPlanInjector",
    "analyze_docx",
    "generate_content_skeleton",
    "make_para",
    "make_run",
    "set_cell_text",
    "set_cell_multiline",
    "load_company_profile",
    "get_profile_summary",
    "generate_content",
    "save_content_json",
]
