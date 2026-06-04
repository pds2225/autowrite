from __future__ import annotations

import shutil
from pathlib import Path

from .config import Settings
from .models import ProjectInput, TemplateProfile
from .utils import read_json, short_id, write_json


class Storage:
    def __init__(self, settings: Settings):
        self.settings = settings

    def template_dir(self, template_id: str) -> Path:
        return self.settings.template_root / template_id

    def project_dir(self, project_id: str) -> Path:
        return self.settings.project_root / project_id

    def results_dir(self, project_id: str) -> Path:
        return self.settings.results_root / project_id

    def create_template_space(self, file_name: str) -> tuple[str, Path]:
        template_id = short_id("tpl")
        folder = self.template_dir(template_id)
        folder.mkdir(parents=True, exist_ok=True)
        return template_id, folder / file_name

    def save_template_profile(self, profile: TemplateProfile) -> Path:
        path = self.template_dir(profile.template_id) / "template_profile.json"
        write_json(path, profile.model_dump())
        return path

    def load_template_profile(self, template_id: str) -> TemplateProfile:
        data = read_json(self.template_dir(template_id) / "template_profile.json")
        return TemplateProfile.model_validate(data)

    def list_template_profiles(self) -> list[TemplateProfile]:
        profiles: list[TemplateProfile] = []
        for path in sorted(self.settings.template_root.glob("*/template_profile.json")):
            profiles.append(TemplateProfile.model_validate(read_json(path)))
        return profiles

    def create_project_space(self, template_id: str, project_name: str) -> tuple[str, Path]:
        project_id = short_id("prj")
        folder = self.project_dir(project_id)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "references").mkdir(exist_ok=True)
        (folder / "generated_assets").mkdir(exist_ok=True)
        (folder / "output").mkdir(exist_ok=True)
        write_json(
            folder / "project_meta.json",
            {"project_id": project_id, "template_id": template_id, "project_name": project_name},
        )
        return project_id, folder

    def save_project_input(self, project_id: str, project_input: ProjectInput) -> Path:
        path = self.project_dir(project_id) / "project_input.json"
        write_json(path, project_input.model_dump())
        return path

    def load_project_input(self, project_id: str) -> ProjectInput:
        data = read_json(self.project_dir(project_id) / "project_input.json")
        return ProjectInput.model_validate(data)

    def list_projects(self) -> list[dict]:
        items: list[dict] = []
        for path in sorted(self.settings.project_root.glob("*/project_meta.json")):
            items.append(read_json(path))
        return items

    def copy_reference_file(self, project_id: str, source_path: Path, target_name: str) -> Path:
        target = self.project_dir(project_id) / "references" / target_name
        shutil.copy2(source_path, target)
        return target
