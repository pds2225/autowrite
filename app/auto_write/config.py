from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Settings:
    app_root: Path
    workspace_root: Path
    template_root: Path
    project_root: Path
    results_root: Path
    static_root: Path
    template_view_root: Path
    host: str
    port: int
    openai_api_key: str
    openai_model: str
    openai_search_model: str
    openai_image_model: str
    anthropic_api_key: str
    anthropic_model: str
    anthropic_search_model: str
    template_ai_refine_enabled: bool = False
    reference_library_dir: Optional[Path] = None

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def ai_provider(self) -> str:
        if self.has_openai:
            return "openai"
        if self.has_anthropic:
            return "anthropic"
        return "none"


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _can_write_to_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".auto_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _resolve_workspace_root(app_root: Path) -> Path:
    configured = os.getenv("AUTO_WRITE_WORKSPACE_ROOT", "").strip()
    if configured:
        return Path(configured)

    default_root = app_root.parent / "workspace"
    if _can_write_to_dir(default_root):
        return default_root

    return app_root / "workspace"


def get_settings() -> Settings:
    app_root = Path(__file__).resolve().parent.parent
    _load_env_file(app_root / ".env")
    workspace_root = _resolve_workspace_root(app_root)
    template_root = workspace_root / "templates"
    project_root = workspace_root / "projects"
    results_root = app_root.parent / "results"
    static_root = app_root / "auto_write" / "static"
    template_view_root = app_root / "auto_write" / "templates"
    default_reference_library = Path(
        r"C:\Users\ekth3\OneDrive\바탕 화면\다솜\경영지도사 개인\02. 밸류업파트너스\2025년\20250406 희망리턴패키지 서류평가\경영개선 4조 서류평가"
    )
    reference_dir_env = os.getenv("AUTO_WRITE_REFERENCE_LIBRARY_DIR", "").strip()
    reference_library_dir: Optional[Path]
    if reference_dir_env:
        reference_library_dir = Path(reference_dir_env)
    elif default_reference_library.exists():
        reference_library_dir = default_reference_library
    else:
        reference_library_dir = None

    return Settings(
        app_root=app_root,
        workspace_root=workspace_root,
        template_root=template_root,
        project_root=project_root,
        results_root=results_root,
        static_root=static_root,
        template_view_root=template_view_root,
        host=os.getenv("AUTO_WRITE_HOST", "127.0.0.1"),
        port=int(os.getenv("AUTO_WRITE_PORT", "8765")),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("AUTO_WRITE_OPENAI_MODEL", "gpt-4.1-mini").strip(),
        openai_search_model=os.getenv("AUTO_WRITE_OPENAI_SEARCH_MODEL", "gpt-4.1-mini").strip(),
        openai_image_model=os.getenv("AUTO_WRITE_OPENAI_IMAGE_MODEL", "gpt-image-1").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("AUTO_WRITE_ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip(),
        anthropic_search_model=os.getenv("AUTO_WRITE_ANTHROPIC_SEARCH_MODEL", "claude-sonnet-4-20250514").strip(),
        template_ai_refine_enabled=os.getenv("AUTO_WRITE_TEMPLATE_AI_REFINE", "").strip().lower()
        in {"1", "true", "yes", "on"},
        reference_library_dir=reference_library_dir,
    )


def ensure_directories(settings: Settings) -> None:
    for path in (
        settings.workspace_root,
        settings.template_root,
        settings.project_root,
        settings.results_root,
        settings.static_root,
        settings.template_view_root,
    ):
        path.mkdir(parents=True, exist_ok=True)
