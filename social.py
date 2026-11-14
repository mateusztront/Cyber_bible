"""
Publishing the day's graphics to a Facebook Page and to X, next to Instagram.

Facebook: Meta Graph API. Each image is uploaded unpublished to
/{page-id}/photos, then one /{page-id}/feed post attaches them all.

X: official API v2 with OAuth 1.0a user context (four keys that don't expire).
X allows 4 images per post, so the day goes out as a thread: cover + first
readings in the first post, the rest in replies.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Sequence

import requests
from requests_oauthlib import OAuth1

import config

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com"
X_API_URL = "https://api.x.com/2"
X_MAX_WEIGHTED_LENGTH = 280
REQUEST_TIMEOUT = 120


class PublishError(Exception):
    """A platform refused the post; the message is meant for the user."""


# =============================================================================
# FACEBOOK
# =============================================================================


def facebook_configured() -> bool:
    return bool(config.FACEBOOK_PAGE_ID and config.FACEBOOK_PAGE_TOKEN)


def _graph_error(response: requests.Response) -> str:
    try:
        error = response.json().get("error", {})
        return error.get("error_user_msg") or error.get("message") or response.text[:300]
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:300]}"


def publish_facebook(paths: Sequence[Path], message: str) -> str:
    """Post the images as one multi-photo Page post. Returns the post id."""
    if not facebook_configured():
        raise PublishError("not set up — add FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN to .env")

    base = f"{GRAPH_URL}/{config.FACEBOOK_GRAPH_VERSION}/{config.FACEBOOK_PAGE_ID}"
    token = config.FACEBOOK_PAGE_TOKEN

    photo_ids = []
    for path in paths:
        with open(path, "rb") as f:
            response = requests.post(
                f"{base}/photos",
                data={"published": "false", "access_token": token},
                files={"source": (Path(path).name, f, "image/jpeg")},
                timeout=REQUEST_TIMEOUT,
            )
        if response.status_code != 200 or "id" not in response.json():
            raise PublishError(f"uploading {Path(path).name} failed: {_graph_error(response)}")
        photo_ids.append(response.json()["id"])
        logger.info(f"Facebook: uploaded {Path(path).name} ({len(photo_ids)}/{len(paths)})")

    data = {"message": message, "access_token": token}
    for i, photo_id in enumerate(photo_ids):
        data[f"attached_media[{i}]"] = f'{{"media_fbid":"{photo_id}"}}'
    response = requests.post(f"{base}/feed", data=data, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200 or "id" not in response.json():
        raise PublishError(f"creating the post failed: {_graph_error(response)}")
    post_id = response.json()["id"]
    logger.info(f"Facebook: published post {post_id}")
    return post_id


# =============================================================================
# X
# =============================================================================


def x_configured() -> bool:
    return all(
        (config.X_API_KEY, config.X_API_SECRET, config.X_ACCESS_TOKEN, config.X_ACCESS_TOKEN_SECRET)
    )


def _x_auth() -> OAuth1:
    return OAuth1(
        config.X_API_KEY,
        config.X_API_SECRET,
        config.X_ACCESS_TOKEN,
        config.X_ACCESS_TOKEN_SECRET,
    )


def _x_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}: {response.text[:300]}"
    if body.get("errors"):
        first = body["errors"][0]
        return first.get("detail") or first.get("message") or str(first)
    detail = body.get("detail") or body.get("title")
    if response.status_code == 402:
        return f"{detail or 'payment required'} — top up X API credits in the developer console"
    return detail or f"HTTP {response.status_code}: {response.text[:300]}"


def x_weighted_length(text: str) -> int:
    """Length as X counts it: most scripts (incl. Polish) weigh 1, emoji/CJK weigh 2."""
    def weight(ch: str) -> int:
        cp = ord(ch)
        if cp <= 4351 or 8192 <= cp <= 8205 or 8208 <= cp <= 8223 or 8242 <= cp <= 8247:
            return 1
        return 2

    return sum(weight(ch) for ch in text)


def _truncate_weighted(text: str, limit: int) -> str:
    """Cut text to the weighted limit at a word boundary, ending with an ellipsis."""
    if x_weighted_length(text) <= limit:
        return text
    cut = ""
    for word in text.split(" "):
        candidate = f"{cut} {word}" if cut else word
        if x_weighted_length(candidate) + 1 > limit:
            break
        cut = candidate
    if not cut:  # a single huge word
        cut = text
        while cut and x_weighted_length(cut) + 1 > limit:
            cut = cut[:-1]
    return cut.rstrip(" ,;:.-–—") + "…"


def build_x_texts(caption: str, thedate: str, posts: int) -> List[str]:
    """Texts for the thread: the caption cut to fit, then "2/3", "3/3"…"""
    clean = caption.split("\n***\n")[0].strip()
    clean = " ".join(clean.split())  # one paragraph reads better in 280 chars
    try:
        date_label = datetime.strptime(thedate, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        date_label = thedate
    tail = f"\n\n{date_label} " + " ".join(config.X_HASHTAGS)
    if posts > 1:
        tail += f"\n🧵 1/{posts}"
    # A few characters of slack for anything X counts differently (e.g. links = 23)
    budget = X_MAX_WEIGHTED_LENGTH - x_weighted_length(tail) - 5
    first = (_truncate_weighted(clean, budget) if clean else "") + tail
    return [first.strip()] + [f"{i}/{posts}" for i in range(2, posts + 1)]


def _x_upload(path: Path, auth: OAuth1) -> str:
    with open(path, "rb") as f:
        response = requests.post(
            f"{X_API_URL}/media/upload",
            auth=auth,
            data={"media_category": "tweet_image"},
            files={"media": (Path(path).name, f, "image/jpeg")},
            timeout=REQUEST_TIMEOUT,
        )
    if response.status_code not in (200, 201):
        raise PublishError(f"uploading {Path(path).name} failed: {_x_error(response)}")
    body = response.json()
    media_id = (body.get("data") or {}).get("id") or body.get("media_id_string")
    if not media_id:
        raise PublishError(f"uploading {Path(path).name} failed: no media id in {body}")
    return media_id


def _x_post(text: str, media_ids: List[str], reply_to: Optional[str], auth: OAuth1) -> str:
    payload = {"text": text, "media": {"media_ids": media_ids}}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    response = requests.post(f"{X_API_URL}/tweets", auth=auth, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code not in (200, 201):
        raise PublishError(_x_error(response))
    return response.json()["data"]["id"]


def publish_x(
    paths: Sequence[Path],
    caption: str,
    thedate: str,
    on_first_post: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Post the images as a thread, 4 per post. Returns the first post's id.

    on_first_post is called as soon as the first post is live, so the caller
    can record it before the replies go out: if a reply then fails, the day is
    still marked as published and isn't posted twice.
    """
    if not x_configured():
        raise PublishError(
            "not set up — add X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET to .env"
        )
    auth = _x_auth()
    per_post = config.X_MAX_IMAGES_PER_POST
    chunks = [list(paths[i:i + per_post]) for i in range(0, len(paths), per_post)]
    texts = build_x_texts(caption, thedate, len(chunks))

    first_id: Optional[str] = None
    previous: Optional[str] = None
    for n, (chunk, text) in enumerate(zip(chunks, texts), start=1):
        try:
            media_ids = [_x_upload(p, auth) for p in chunk]
            previous = _x_post(text, media_ids, previous, auth)
        except PublishError as e:
            if first_id:
                raise PublishError(
                    f"post {first_id} is live, but reply {n}/{len(chunks)} failed: {e}"
                ) from e
            raise
        logger.info(f"X: published post {n}/{len(chunks)} ({previous})")
        if first_id is None:
            first_id = previous
            if on_first_post:
                on_first_post(first_id)
    return first_id or ""
