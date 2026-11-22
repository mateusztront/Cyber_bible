"""
Per-day history of Midjourney covers: every grid and every upscaled image made
for a date, with where each came from, so any of them can become the cover.

Layout, inside the date folder (web/<date>/):

    _cover_history/
        history.json      items + which image is the current cover
        1-grid.png        a 4-image grid (from a prompt, or a variation)
        2.png             an image upscaled from a grid
        ...

Items (history.json "items", oldest first):

    grid:  {"id", "type": "grid", "created_at", "prompt", "source": "prompt" |
            "subtle" | "strong", "parent": <image id varied> | None,
            "message_id", "buttons": {"U1": custom_id, ...}, "file",
            "picked": {"U2": <image id>, ...}}
    image: {"id", "type": "image", "created_at", "prompt", "grid": <grid id>,
            "variant": "U2", "message_id", "vary": {"subtle": custom_id,
            "strong": custom_id}, "file"}

The cover itself stays where publishing looks for it: web/<date>/mateusztront.jpg.
A day's history is deleted once a LATER day is published (prune_before).
"""

import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

HISTORY_DIRNAME = "_cover_history"
HISTORY_FILE = "history.json"
COVER_FILENAME = "mateusztront.jpg"
_DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")

Downloader = Callable[[str, Path], Path]


class HistoryError(Exception):
    """Unknown item or wrong kind of item; the message is for the user."""


def history_dir(web_dir: Path, thedate: str) -> Path:
    return Path(web_dir) / thedate / HISTORY_DIRNAME


def load(web_dir: Path, thedate: str) -> dict:
    path = history_dir(web_dir, thedate) / HISTORY_FILE
    if not path.exists():
        return {"items": [], "cover": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning(f"Unreadable {path}: {e}")
        return {"items": [], "cover": None}
    data.setdefault("items", [])
    data.setdefault("cover", None)
    return data


def _save(web_dir: Path, thedate: str, data: dict) -> None:
    folder = history_dir(web_dir, thedate)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (HISTORY_FILE + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(folder / HISTORY_FILE)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _next_id(data: dict) -> int:
    return max((item["id"] for item in data["items"]), default=0) + 1


def _extension(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in (".png", ".jpg", ".jpeg", ".webp") else ".png"


def _first_attachment_url(message: dict) -> str:
    url = ((message.get("attachments") or [{}])[0] or {}).get("url", "")
    if not url:
        raise HistoryError("Midjourney's reply has no image")
    return url


def get_item(data: dict, item_id: int, kind: Optional[str] = None) -> dict:
    for item in data["items"]:
        if item["id"] == int(item_id):
            if kind and item["type"] != kind:
                raise HistoryError(f"#{item_id} is a {item['type']}, not a {kind}")
            return item
    raise HistoryError(f"No #{item_id} in this day's history")


def add_grid(
    web_dir: Path,
    thedate: str,
    message: dict,
    prompt: str,
    upscale_buttons: Dict[str, str],
    download: Downloader,
    source: str = "prompt",
    parent: Optional[int] = None,
) -> dict:
    """Record a new grid (a fresh prompt, or a variation of image `parent`)."""
    url = _first_attachment_url(message)
    data = load(web_dir, thedate)
    item_id = _next_id(data)
    filename = f"{item_id}-grid{_extension(url)}"
    download(url, history_dir(web_dir, thedate) / filename)
    item = {
        "id": item_id,
        "type": "grid",
        "created_at": _now(),
        "prompt": prompt,
        "source": source,
        "parent": parent,
        "message_id": message.get("id", ""),
        "buttons": upscale_buttons,
        "file": filename,
        "picked": {},
    }
    data["items"].append(item)
    _save(web_dir, thedate, data)
    return item


def grid_for_message(data: dict, message_id: str) -> Optional[dict]:
    for item in data["items"]:
        if item["type"] == "grid" and item.get("message_id") == message_id:
            return item
    return None


def add_image(
    web_dir: Path,
    thedate: str,
    grid_id: int,
    variant: str,
    message: dict,
    vary_buttons: Dict[str, str],
    download: Downloader,
) -> dict:
    """Record an image upscaled from grid `grid_id` and make it the cover."""
    url = _first_attachment_url(message)
    data = load(web_dir, thedate)
    grid = get_item(data, grid_id, "grid")
    item_id = _next_id(data)
    filename = f"{item_id}{_extension(url)}"
    download(url, history_dir(web_dir, thedate) / filename)
    item = {
        "id": item_id,
        "type": "image",
        "created_at": _now(),
        "prompt": grid.get("prompt", ""),
        "grid": grid["id"],
        "variant": variant,
        "message_id": message.get("id", ""),
        "vary": vary_buttons,
        "file": filename,
    }
    data["items"].append(item)
    grid.setdefault("picked", {})[variant] = item_id
    _save(web_dir, thedate, data)
    set_cover(web_dir, thedate, item_id)
    return item


def set_cover(web_dir: Path, thedate: str, image_id: int) -> Path:
    """Make history image `image_id` the day's cover (web/<date>/mateusztront.jpg)."""
    data = load(web_dir, thedate)
    item = get_item(data, image_id, "image")
    src = history_dir(web_dir, thedate) / item["file"]
    if not src.exists():
        raise HistoryError(f"The file for #{image_id} is missing")
    dst = Path(web_dir) / thedate / COVER_FILENAME
    # A fresh copy is also the newest cover image in the folder, which is the
    # one publishing picks (see _prepare_post_images).
    shutil.copyfile(src, dst)
    data["cover"] = item["id"]
    _save(web_dir, thedate, data)
    return dst


def view(web_dir: Path, thedate: str) -> dict:
    """History for the page: items newest first, with image URLs."""
    data = load(web_dir, thedate)
    base = f"/{thedate}/{HISTORY_DIRNAME}"
    items = []
    for item in reversed(data["items"]):
        entry = {k: v for k, v in item.items() if k not in ("buttons", "vary")}
        entry["url"] = f"{base}/{item['file']}"
        if item["type"] == "grid":
            entry["buttons"] = item.get("buttons", {})
        else:
            entry["can_vary"] = {k: bool(item.get("vary", {}).get(k)) for k in ("subtle", "strong")}
        items.append(entry)
    return {"items": items, "cover": data.get("cover")}


def prune_before(web_dir: Path, published_date: str) -> List[str]:
    """
    Delete the cover history of every day before `published_date`: once the
    next day's post is out, an earlier day won't be reposted. The days' own
    covers (outside the history folder) are kept.
    """
    pruned = []
    web_dir = Path(web_dir)
    if not web_dir.is_dir():
        return pruned
    for day in web_dir.iterdir():
        if not (day.is_dir() and _DATE_DIR.match(day.name) and day.name < published_date):
            continue
        folder = day / HISTORY_DIRNAME
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
            pruned.append(day.name)
    if pruned:
        logger.info(f"Cover history deleted for {', '.join(sorted(pruned))} (published {published_date})")
    return sorted(pruned)
