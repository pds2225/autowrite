from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from ..models import EvidenceSource, GeneratedImage, ImageSlotProfile
from .openai_client import OpenAIService

FONT_REGULAR = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(path), size)


class ImageService:
    NON_BUSINESS_SLOT_RE = re.compile(
        r"(증빙서류|제출목록|동의서|서약서|확인서|신청기업|추천기관|담\s*당\s*자|서명|날인|평가대상에서 제외|별첨|붙임)",
        re.IGNORECASE,
    )

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    @staticmethod
    def _note_key(slot_id: str) -> str:
        return f"image_note_{slot_id}"

    @classmethod
    def _is_non_business_slot(cls, label: str) -> bool:
        return bool(cls.NON_BUSINESS_SLOT_RE.search(str(label or "").strip()))

    def _should_generate_slot(self, slot: ImageSlotProfile, answers: dict[str, str]) -> bool:
        label = str(slot.label or "").strip()
        note = str(answers.get(self._note_key(slot.slot_id), "") or "").strip()
        if self._is_non_business_slot(label):
            return bool(note)
        if slot.required:
            return True
        if note:
            return True
        # Template-defined slots should be filled by default to keep template fidelity.
        if slot.source == "template":
            return True
        return False

    def build_images(
        self,
        slots: Iterable[ImageSlotProfile],
        answers: dict[str, str],
        evidence: list[EvidenceSource],
        output_dir: Path,
    ) -> list[GeneratedImage]:
        images: list[GeneratedImage] = []
        output_dir.mkdir(parents=True, exist_ok=True)
        joined_context = "\n".join(str(value) for value in answers.values() if value)
        for slot in slots:
            if not self._should_generate_slot(slot, answers):
                continue
            note = str(answers.get(self._note_key(slot.slot_id), "") or "").strip()
            slot_context = "\n".join(part for part in (note, joined_context) if part)
            prompt = self.openai_service.propose_image_prompt(slot.label, slot_context)
            image_path = output_dir / f"{slot.slot_id}.png"
            created = self.openai_service.generate_image_file(prompt, image_path)
            if not created:
                if evidence and "통계" in slot.label:
                    self._make_stat_card(slot, evidence, image_path)
                else:
                    self._make_diagram_card(slot, prompt, slot_context, image_path)
            images.append(
                GeneratedImage(
                    slot_id=slot.slot_id,
                    label=slot.label,
                    path=str(image_path),
                    caption=slot.label,
                    source="generated",
                )
            )
        return images

    def _make_diagram_card(self, slot: ImageSlotProfile, prompt: str, context: str, output_path: Path) -> None:
        image = Image.new("RGB", (1536, 1024), "#F8FAFC")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1536, 190), fill="#E2E8F0")
        draw.text((64, 52), slot.label, font=_font(44, True), fill="#0F172A")
        draw.text((64, 120), "자동 생성 설명 이미지", font=_font(24), fill="#475569")

        boxes = [
            ((96, 280, 420, 620), "#DBEAFE", "#2563EB"),
            ((606, 280, 930, 620), "#DCFCE7", "#16A34A"),
            ((1116, 280, 1440, 620), "#FCE7F3", "#DB2777"),
        ]
        stage_titles = ["입력", "분석", "결과"]
        stage_texts = [
            prompt[:80] or slot.label,
            context[:120] or "참고자료와 입력값을 바탕으로 핵심 내용을 정리",
            "계획서에 바로 넣을 수 있는 도식/설명용 이미지",
        ]
        for idx, ((x1, y1, x2, y2), fill, outline) in enumerate(boxes):
            draw.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=fill, outline=outline, width=4)
            draw.text((x1 + 24, y1 + 28), stage_titles[idx], font=_font(32, True), fill="#0F172A")
            wrapped = textwrap.fill(stage_texts[idx], width=18)
            draw.multiline_text((x1 + 24, y1 + 100), wrapped, font=_font(22), fill="#1E293B", spacing=12)
            if idx < 2:
                draw.line((x2 + 18, 450, boxes[idx + 1][0][0] - 18, 450), fill="#2563EB", width=10)
                draw.polygon(
                    [
                        (boxes[idx + 1][0][0] - 18, 450),
                        (boxes[idx + 1][0][0] - 46, 432),
                        (boxes[idx + 1][0][0] - 46, 468),
                    ],
                    fill="#2563EB",
                )
        draw.multiline_text(
            (96, 760),
            textwrap.fill(context[:220] or prompt, width=60),
            font=_font(24),
            fill="#334155",
            spacing=10,
        )
        image.save(output_path)

    def _make_stat_card(self, slot: ImageSlotProfile, evidence: list[EvidenceSource], output_path: Path) -> None:
        image = Image.new("RGB", (1536, 1024), "#FFFFFF")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1536, 180), fill="#FEF3C7")
        draw.text((64, 52), slot.label, font=_font(42, True), fill="#0F172A")
        draw.text((64, 116), "검색 결과를 바탕으로 만든 통계 요약 카드", font=_font(24), fill="#92400E")
        y = 240
        for index, source in enumerate(evidence[:4], start=1):
            draw.rounded_rectangle((72, y, 1464, y + 170), radius=24, fill="#F8FAFC", outline="#CBD5E1", width=3)
            draw.text((98, y + 20), f"{index}. {source.title}", font=_font(28, True), fill="#0F172A")
            summary = source.summary or source.url
            draw.multiline_text(
                (98, y + 72),
                textwrap.fill(summary[:180], width=60),
                font=_font(22),
                fill="#334155",
                spacing=8,
            )
            draw.text((98, y + 128), source.url[:120], font=_font(18), fill="#475569")
            y += 190
        image.save(output_path)
