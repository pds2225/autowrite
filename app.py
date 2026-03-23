from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from dedupe import remove_duplicates
from downloader import DownloadedImage, ImageDownloader
from image_search import ImageSearchClient
from manifest_writer import write_manifest_csv, write_manifest_json

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
GENERATED_DIR = BASE_DIR / "separate_generated_images"
LOGS_DIR = BASE_DIR / "logs"
QUERY_CSV = BASE_DIR / "queries.csv"
MANIFEST_JSON = BASE_DIR / "images_manifest.json"
MANIFEST_CSV = BASE_DIR / "images_manifest.csv"

for d in [IMAGES_DIR, GENERATED_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "error.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
LOGGER = logging.getLogger("auto_collector")

DEFAULT_SECTIONS = pd.DataFrame(
    [
        {"section": "problem", "summary": "시장 문제와 현재 페인포인트"},
        {"section": "solution", "summary": "제안 솔루션과 제품/공정 특징"},
        {"section": "scaleup", "summary": "확장 전략, 생산, 유통, 통계"},
        {"section": "team", "summary": "팀 역량과 현장 협업 증빙"},
    ]
)


def save_queries(rows: List[dict]) -> None:
    pd.DataFrame(rows).to_csv(QUERY_CSV, index=False, encoding="utf-8-sig")


def collect_images(
    business_name: str,
    sections: List[Dict[str, str]],
    per_section: int,
    min_width: int,
    min_height: int,
) -> List[DownloadedImage]:
    client = ImageSearchClient(
        serpapi_key=os.getenv("SERPAPI_API_KEY"),
        bing_key=os.getenv("BING_SEARCH_API_KEY"),
        bing_endpoint=os.getenv("BING_IMAGE_SEARCH_ENDPOINT"),
    )
    downloader = ImageDownloader(str(IMAGES_DIR), min_width=min_width, min_height=min_height)

    all_downloaded: List[DownloadedImage] = []
    query_rows: List[dict] = []

    for item in sections:
        section = item["section"].strip()
        summary = item["summary"].strip()
        candidates = client.search_section(business_name, section, summary, per_section * 4)

        section_downloaded: List[DownloadedImage] = []
        idx = 1
        for c in candidates:
            query_rows.append({"section": section, "query": c.query, "image_url": c.image_url, "source_url": c.source_url})
            result = downloader.download(c, summary, idx)
            if result is None:
                continue
            section_downloaded.append(result)
            idx += 1
            if len(section_downloaded) >= per_section:
                break

        deduped_section = remove_duplicates(section_downloaded)
        all_downloaded.extend(deduped_section[:per_section])

    all_downloaded = remove_duplicates(all_downloaded)
    bucket = defaultdict(list)
    for img in all_downloaded:
        bucket[img.section].append(img)

    trimmed: List[DownloadedImage] = []
    for sec, imgs in bucket.items():
        trimmed.extend(imgs[:per_section])

    save_queries(query_rows)
    return trimmed


st.set_page_config(page_title="사업계획서 이미지 자동수집기", layout="wide")
st.title("사업계획서용 이미지 자동수집기")
st.caption("통계/현장/제품/공정 우선 검색 + 다운로드 + manifest 생성")

with st.sidebar:
    st.subheader("환경 설정")
    st.write("- `SERPAPI_API_KEY` 또는 Bing 키/엔드포인트 필요")
    per_section = st.number_input("섹션별 다운로드 개수", min_value=1, max_value=10, value=3)
    min_width = st.number_input("최소 너비(px)", min_value=320, max_value=4000, value=800)
    min_height = st.number_input("최소 높이(px)", min_value=240, max_value=4000, value=600)

business_name = st.text_input("사업명", value="RUSALKA")
st.subheader("섹션 입력")
section_df = st.data_editor(DEFAULT_SECTIONS, num_rows="dynamic", use_container_width=True)

if st.button("이미지 수집 시작", type="primary"):
    try:
        section_rows = json.loads(section_df.to_json(orient="records"))
        section_rows = [r for r in section_rows if str(r.get("section", "")).strip() and str(r.get("summary", "")).strip()]
        if not section_rows:
            st.error("섹션과 요약 텍스트를 최소 1개 이상 입력하세요.")
        else:
            results = collect_images(
                business_name=business_name,
                sections=section_rows,
                per_section=int(per_section),
                min_width=int(min_width),
                min_height=int(min_height),
            )
            write_manifest_json(results, str(MANIFEST_JSON))
            write_manifest_csv(results, str(MANIFEST_CSV))

            st.success(f"완료: {len(results)}개 이미지 저장")
            st.write(f"JSON: `{MANIFEST_JSON}`")
            st.write(f"CSV: `{MANIFEST_CSV}`")
            st.write(f"로그: `{LOGS_DIR / 'error.log'}`")
            st.dataframe(pd.DataFrame([r.__dict__ for r in results]), use_container_width=True)
    except Exception as exc:
        LOGGER.exception("Collection failed: %s", exc)
        st.error(f"수집 중 오류 발생: {exc}")
