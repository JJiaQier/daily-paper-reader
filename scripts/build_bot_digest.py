from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = REPO_ROOT / "archive"
REPORTS_DIR = REPO_ROOT / "reports"
PAGES_BASE_URL = "https://jjiaqier.github.io/daily-paper-reader/#/"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_latest_recommend_file() -> Path:
    candidates = sorted(ARCHIVE_DIR.glob("*/recommend/*.standard.json"))
    if not candidates:
        raise FileNotFoundError("No *.standard.json found under archive/*/recommend/")
    return candidates[-1]


def first_non_empty(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def normalize_item(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": first_non_empty(record, "id"),
        "title": first_non_empty(record, "title"),
        "summary": first_non_empty(
            record,
            "llm_evidence_cn",
            "llm_evidence",
            "canonical_evidence",
            "abstract",
        ),
        "abstract": first_non_empty(record, "abstract"),
        "source": first_non_empty(record, "source"),
        "link": first_non_empty(record, "link"),
    }


def load_recommendation_sets(path: Path) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    data = load_json(path)

    run_window = path.parent.parent.name
    deep_dive_raw = data.get("deep_dive", []) if isinstance(data, dict) else []
    quick_skim_raw = data.get("quick_skim", []) if isinstance(data, dict) else []

    deep_dive = [normalize_item(x) for x in deep_dive_raw if isinstance(x, dict)]
    quick_skim = [normalize_item(x) for x in quick_skim_raw if isinstance(x, dict)]

    return run_window, deep_dive, quick_skim


def slug_from_item(item: dict[str, Any]) -> str:
    paper_id = item.get("id", "").strip()
    title = item.get("title", "").strip().lower()

    safe = []
    for ch in title:
        if ch.isalnum():
            safe.append(ch)
        elif ch in (" ", "-", "_"):
            safe.append("-")
    title_slug = "".join(safe)

    while "--" in title_slug:
        title_slug = title_slug.replace("--", "-")

    title_slug = title_slug.strip("-")
    if paper_id and title_slug:
        return f"{paper_id}-{title_slug}"
    return paper_id or title_slug


def build_entry_url(run_window: str, featured: dict[str, Any]) -> str:
    slug = slug_from_item(featured)
    if slug:
        return f"{PAGES_BASE_URL}{run_window}/{slug}"
    return PAGES_BASE_URL


def build_markdown(
    *,
    date_str: str,
    run_window: str,
    entry_url: str,
    featured: dict[str, Any],
    quick_reads: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append("# 今日论文推荐")
    lines.append("")
    lines.append("阅读入口：")
    lines.append(entry_url)
    lines.append("")
    lines.append("时间窗口：")
    lines.append(run_window)
    lines.append("")
    lines.append("精读文章：")
    lines.append(featured.get("title", "未找到精读文章"))
    lines.append("")
    lines.append("精读文章摘要：")
    lines.append(featured.get("summary", "暂无摘要"))
    lines.append("")

    for idx, item in enumerate(quick_reads, start=1):
        lines.append(f"速读文章{idx}：")
        lines.append(item.get("title", "未命名论文"))
        lines.append(f"一句话摘要：{item.get('summary', '暂无摘要')}")
        lines.append("")

    lines.append("生成日期：")
    lines.append(date_str)
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    latest_file = find_latest_recommend_file()
    run_window, deep_dive, quick_skim = load_recommendation_sets(latest_file)

    if deep_dive:
        featured = deep_dive[0]
        quick_reads = quick_skim[:3]
    elif quick_skim:
        featured = quick_skim[0]
        quick_reads = quick_skim[1:4]
    else:
        raise ValueError(f"No recommended papers found in {latest_file}")

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    entry_url = build_entry_url(run_window, featured)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    markdown = build_markdown(
        date_str=date_str,
        run_window=run_window,
        entry_url=entry_url,
        featured=featured,
        quick_reads=quick_reads,
    )

    latest_md = REPORTS_DIR / "bot-digest-latest.md"
    dated_md = REPORTS_DIR / f"bot-digest-{date_str}.md"

    latest_md.write_text(markdown, encoding="utf-8")
    dated_md.write_text(markdown, encoding="utf-8")

    print(f"Digest written to: {latest_md}")
    print(f"Digest written to: {dated_md}")


if __name__ == "__main__":
    main()
