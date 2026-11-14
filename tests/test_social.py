"""Publishing to a Facebook Page and to X (social.py) and the multi-platform publish()."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

import pytest
import responses
from PIL import Image

import config
import social
from social import PublishError, build_x_texts, x_weighted_length

FB_BASE = "https://graph.facebook.com/v26.0/PAGE1"
X_BASE = "https://api.x.com/2"
THEDATE = "2026-11-14"


@pytest.fixture
def fb_config(monkeypatch):
    monkeypatch.setattr(config, "FACEBOOK_PAGE_ID", "PAGE1")
    monkeypatch.setattr(config, "FACEBOOK_PAGE_TOKEN", "TOKEN")
    monkeypatch.setattr(config, "FACEBOOK_GRAPH_VERSION", "v26.0")


@pytest.fixture
def x_config(monkeypatch):
    for name in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"):
        monkeypatch.setattr(config, name, name.lower())


def _images(tmp_path, n):
    paths = []
    for i in range(n):
        p = tmp_path / f"img{i}.jpg"
        Image.new("RGB", (10, 10), "white").save(p)
        paths.append(p)
    return paths


# =============================================================================
# FACEBOOK
# =============================================================================


class TestFacebook:
    def test_not_configured(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "FACEBOOK_PAGE_ID", "")
        assert not social.facebook_configured()
        with pytest.raises(PublishError, match="not set up"):
            social.publish_facebook(_images(tmp_path, 1), "x")

    @responses.activate
    def test_multi_photo_post(self, fb_config, tmp_path):
        for i in range(3):
            responses.post(f"{FB_BASE}/photos", json={"id": f"ph{i}"})
        responses.post(f"{FB_BASE}/feed", json={"id": "PAGE1_999"})

        assert social.publish_facebook(_images(tmp_path, 3), "Czytania") == "PAGE1_999"

        uploads = responses.calls[:3]
        assert all(b"published" in c.request.body and b"false" in c.request.body for c in uploads)
        feed = parse_qs(responses.calls[3].request.body)
        assert feed["message"] == ["Czytania"]
        assert feed["access_token"] == ["TOKEN"]
        assert [json.loads(feed[f"attached_media[{i}]"][0]) for i in range(3)] == [
            {"media_fbid": "ph0"}, {"media_fbid": "ph1"}, {"media_fbid": "ph2"},
        ]

    @responses.activate
    def test_upload_error_is_reported(self, fb_config, tmp_path):
        responses.post(
            f"{FB_BASE}/photos", status=400,
            json={"error": {"message": "(#200) The user hasn't authorized the application"}},
        )
        with pytest.raises(PublishError, match="img0.jpg failed: .*hasn't authorized"):
            social.publish_facebook(_images(tmp_path, 2), "x")
        assert not any("/feed" in c.request.url for c in responses.calls)

    @responses.activate
    def test_feed_error_is_reported(self, fb_config, tmp_path):
        responses.post(f"{FB_BASE}/photos", json={"id": "ph0"})
        responses.post(f"{FB_BASE}/feed", status=400, json={"error": {"message": "Invalid token"}})
        with pytest.raises(PublishError, match="creating the post failed: Invalid token"):
            social.publish_facebook(_images(tmp_path, 1), "x")


# =============================================================================
# X
# =============================================================================


class TestXTexts:
    def test_weighting(self):
        assert x_weighted_length("Zażółć gęślą jaźń") == 17
        assert x_weighted_length("📖") == 2

    def test_single_post_fits_and_has_date_and_hashtags(self):
        caption = "Słowa Ewangelii według świętego Łukasza. " * 30
        [text] = build_x_texts(caption, THEDATE, 1)
        assert x_weighted_length(text) <= 280
        assert "…" in text
        assert "14.11.2026" in text and "#czytanianadzis" in text
        assert "🧵" not in text

    def test_short_caption_is_kept_whole(self):
        [text] = build_x_texts("Krótko.", THEDATE, 1)
        assert text.startswith("Krótko.\n\n14.11.2026")
        assert "…" not in text

    def test_thread_numbering(self):
        texts = build_x_texts("Tekst", THEDATE, 3)
        assert texts[0].endswith("🧵 1/3")
        assert texts[1:] == ["2/3", "3/3"]

    def test_caption_metadata_after_separator_is_dropped(self):
        [text] = build_x_texts("Czytanie\n***\nGrafika AI", THEDATE, 1)
        assert "Grafika" not in text


class TestX:
    def test_not_configured(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "X_API_KEY", "")
        assert not social.x_configured()
        with pytest.raises(PublishError, match="not set up"):
            social.publish_x(_images(tmp_path, 1), "c", THEDATE)

    @responses.activate
    def test_thread_with_four_images_per_post(self, x_config, tmp_path):
        for i in range(6):
            responses.post(f"{X_BASE}/media/upload", json={"data": {"id": f"m{i}"}})
        responses.post(f"{X_BASE}/tweets", json={"data": {"id": "t1", "text": ""}}, status=201)
        responses.post(f"{X_BASE}/tweets", json={"data": {"id": "t2", "text": ""}}, status=201)
        first_posts = []

        assert social.publish_x(_images(tmp_path, 6), "Czytania", THEDATE, first_posts.append) == "t1"

        tweets = [json.loads(c.request.body) for c in responses.calls if c.request.url.endswith("/tweets")]
        assert tweets[0]["media"]["media_ids"] == ["m0", "m1", "m2", "m3"]
        assert "reply" not in tweets[0]
        assert tweets[1]["media"]["media_ids"] == ["m4", "m5"]
        assert tweets[1]["reply"] == {"in_reply_to_tweet_id": "t1"}
        assert tweets[1]["text"] == "2/2"
        assert first_posts == ["t1"]
        # OAuth 1.0a user context on every call
        for c in responses.calls:
            auth = c.request.headers["Authorization"]
            auth = auth.decode() if isinstance(auth, bytes) else auth
            assert auth.startswith("OAuth ") and 'oauth_consumer_key="x_api_key"' in auth

    @responses.activate
    def test_no_credits_is_explained(self, x_config, tmp_path):
        responses.post(f"{X_BASE}/media/upload", json={"data": {"id": "m0"}})
        responses.post(f"{X_BASE}/tweets", status=402, json={"title": "Payment Required", "detail": "No credits"})
        with pytest.raises(PublishError, match="No credits — top up X API credits"):
            social.publish_x(_images(tmp_path, 1), "c", THEDATE)

    @responses.activate
    def test_failed_reply_says_first_post_is_live(self, x_config, tmp_path):
        for i in range(5):
            responses.post(f"{X_BASE}/media/upload", json={"data": {"id": f"m{i}"}})
        responses.post(f"{X_BASE}/tweets", json={"data": {"id": "t1", "text": ""}}, status=201)
        responses.post(f"{X_BASE}/tweets", status=403, json={"detail": "duplicate content"})
        first_posts = []
        with pytest.raises(PublishError, match="post t1 is live, but reply 2/2 failed: duplicate content"):
            social.publish_x(_images(tmp_path, 5), "c", THEDATE, first_posts.append)
        assert first_posts == ["t1"]


# =============================================================================
# publish() across platforms
# =============================================================================


class TestMultiPlatformPublish:
    @staticmethod
    def _post_dir(tmp_path):
        post_dir = tmp_path / THEDATE
        post_dir.mkdir()
        Image.new("RGB", (100, 100), "white").save(post_dir / "mateusztront.jpg")
        (post_dir / "EWANGELIA1.jpg").write_bytes(b"fake")
        return post_dir

    @staticmethod
    def _ig_client():
        client = MagicMock()
        client.album_upload.return_value = SimpleNamespace(code="IGCODE")
        return client

    def _publish(self, tmp_path, platforms, force=False, fb=None, x=None, client=None):
        from create_graphic import publish

        fb = fb or MagicMock(return_value="FB1")
        x = x or MagicMock(return_value="X1")
        with patch("create_graphic.login_user", return_value=client or self._ig_client()), \
             patch("create_graphic.WEB_DIR", tmp_path), \
             patch.object(social, "publish_facebook", fb), \
             patch.object(social, "publish_x", x):
            return publish(THEDATE, "caption", force, "", platforms)

    def test_all_platforms_succeed(self, tmp_path):
        from create_graphic import PUBLISHED_MARKER, get_publish_status

        post_dir = self._post_dir(tmp_path)
        x = MagicMock(side_effect=lambda paths, cap, d, on_first_post: on_first_post("X1") or "X1")
        assert self._publish(tmp_path, ["instagram", "facebook", "x"], x=x) == ""

        marker = json.loads((post_dir / PUBLISHED_MARKER).read_text())
        assert marker["media_code"] == "IGCODE"  # Instagram keeps the old top-level keys
        assert {p: e["id"] for p, e in marker["platforms"].items()} == {
            "instagram": "IGCODE", "facebook": "FB1", "x": "X1",
        }
        with patch("create_graphic.WEB_DIR", tmp_path):
            assert set(get_publish_status(THEDATE)) == {"instagram", "facebook", "x"}

    def test_same_images_in_same_order_everywhere(self, tmp_path):
        self._post_dir(tmp_path)
        client, fb = self._ig_client(), MagicMock(return_value="FB1")
        assert self._publish(tmp_path, ["instagram", "facebook"], client=client, fb=fb) == ""
        ig_paths = client.album_upload.call_args.kwargs["paths"]
        fb_paths = [str(p) for p in fb.call_args.args[0]]
        assert ig_paths == fb_paths
        assert ig_paths[0].endswith("cover.jpg")
        assert "***" in fb.call_args.args[1]  # same full caption as Instagram

    def test_one_failure_does_not_stop_the_others(self, tmp_path):
        from create_graphic import PUBLISHED_MARKER

        post_dir = self._post_dir(tmp_path)
        fb = MagicMock(side_effect=social.PublishError("Invalid token"))
        msg = self._publish(tmp_path, ["instagram", "facebook", "x"], fb=fb)
        assert msg == (
            "Instagram: published\n"
            "Facebook: Failed to publish: Invalid token\n"
            "X: published"
        )
        marker = json.loads((post_dir / PUBLISHED_MARKER).read_text())
        assert set(marker["platforms"]) == {"instagram"}  # X mock didn't call on_first_post

    def test_already_published_platform_is_skipped_without_force(self, tmp_path):
        self._post_dir(tmp_path)
        assert self._publish(tmp_path, ["instagram"]) == ""

        client = self._ig_client()
        fb = MagicMock(return_value="FB1")
        msg = self._publish(tmp_path, ["instagram", "facebook"], client=client, fb=fb)
        assert msg.startswith("Instagram: The post for 2026-11-14 was already published at")
        assert msg.endswith("Facebook: published")
        client.album_upload.assert_not_called()
        fb.assert_called_once()

    def test_legacy_instagram_marker_is_understood(self, tmp_path):
        from create_graphic import PUBLISHED_MARKER, get_publish_status, get_published_at

        post_dir = self._post_dir(tmp_path)
        (post_dir / PUBLISHED_MARKER).write_text(
            json.dumps({"published_at": "2026-11-14T08:00:00+01:00", "media_code": "OLD"})
        )
        with patch("create_graphic.WEB_DIR", tmp_path):
            assert get_publish_status(THEDATE) == {"instagram": "2026-11-14T08:00:00+01:00"}
            assert get_published_at(THEDATE) == "2026-11-14T08:00:00+01:00"
        # Adding Facebook later keeps the Instagram record
        assert self._publish(tmp_path, ["facebook"]) == ""
        marker = json.loads((post_dir / PUBLISHED_MARKER).read_text())
        assert marker["media_code"] == "OLD"
        assert set(marker["platforms"]) == {"instagram", "facebook"}

    def test_no_platform_selected(self, tmp_path):
        self._post_dir(tmp_path)
        assert self._publish(tmp_path, []) == "Choose at least one platform to publish to"

    def test_x_only_does_not_log_in_to_instagram(self, tmp_path):
        from create_graphic import publish

        self._post_dir(tmp_path)
        login = MagicMock()
        with patch("create_graphic.login_user", login), patch("create_graphic.WEB_DIR", tmp_path), \
             patch.object(social, "publish_x", MagicMock(return_value="X1")):
            assert publish(THEDATE, "caption", False, "", ["x"]) == ""
        login.assert_not_called()

    def test_platforms_endpoint(self, fb_config, monkeypatch):
        from create_graphic import get_publish_platforms

        monkeypatch.setattr(config, "X_API_KEY", "")
        assert get_publish_platforms() == {"instagram": True, "facebook": True, "x": False}
