"""Midjourney variations and the per-day cover history."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import cover_history
import create_graphic as cg
from libs.midjourney.midjourney_api import MidjourneyApi
from midjourney_wrapper import extract_upscale_buttons, extract_vary_buttons

DAY = "2026-11-22"
PROMPT = "Christ the King on a throne of light --ar 1:1 --v 7"


def _grid_message(msg_id, content=PROMPT):
    return {
        "id": msg_id,
        "content": f"**{content}** - <@1> (fast)",
        "attachments": [{"url": f"https://cdn.discordapp.com/attachments/1/{msg_id}/grid_0.png?ex=1"}],
        "components": [
            {"type": 1, "components": [
                {"type": 2, "label": f"U{i}", "custom_id": f"MJ::JOB::upsample::{i}::{msg_id}"} for i in range(1, 5)
            ]},
            {"type": 1, "components": [
                {"type": 2, "label": f"V{i}", "custom_id": f"MJ::JOB::variation::{i}::{msg_id}"} for i in range(1, 5)
            ]},
        ],
    }


def _upscale_message(msg_id):
    return {
        "id": msg_id,
        "attachments": [{"url": f"https://cdn.discordapp.com/attachments/1/{msg_id}/image.png"}],
        "components": [{"type": 1, "components": [
            {"type": 2, "label": "Upscale (Subtle)", "custom_id": f"MJ::JOB::upsample_v7_2x_subtle::1::{msg_id}::SOLO"},
            {"type": 2, "label": "Vary (Subtle)", "custom_id": f"MJ::JOB::low_variation::1::{msg_id}::SOLO"},
            {"type": 2, "label": "Vary (Strong)", "custom_id": f"MJ::JOB::high_variation::1::{msg_id}::SOLO"},
            {"type": 2, "label": "Vary (Region)", "custom_id": f"MJ::Inpaint::1::{msg_id}::SOLO"},
        ]}],
    }


def _fake_download(url, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), "gold").save(path, "PNG")
    return path


# =============================================================================
# Buttons
# =============================================================================


class TestButtons:
    def test_upscale_buttons(self):
        assert extract_upscale_buttons(_grid_message("g")["components"]) == {
            f"U{i}": f"MJ::JOB::upsample::{i}::g" for i in range(1, 5)
        }

    def test_vary_buttons_skip_region_and_upscale(self):
        assert extract_vary_buttons(_upscale_message("u")["components"]) == {
            "subtle": "MJ::JOB::low_variation::1::u::SOLO",
            "strong": "MJ::JOB::high_variation::1::u::SOLO",
        }

    def test_vary_buttons_found_by_custom_id_if_labels_change(self):
        comps = [{"components": [{"label": "🪄 Subtle", "custom_id": "MJ::JOB::low_variation::1::x::SOLO"},
                                 {"label": "", "custom_id": "MJ::JOB::high_variation::1::x::SOLO"}]}]
        assert set(extract_vary_buttons(comps)) == {"subtle", "strong"}

    def test_no_buttons(self):
        assert extract_vary_buttons([]) == {}
        assert extract_upscale_buttons(None) == {}


# =============================================================================
# Discord client: vary
# =============================================================================


class TestVaryClient:
    @pytest.fixture
    def api(self):
        api = MidjourneyApi("tok", "app", "guild", "chan", "v", "id")
        api._click_button = MagicMock()
        return api

    def _messages(self, *msgs, ts="2999-01-01T00:00:00+00:00"):
        resp = MagicMock()
        resp.json.return_value = [
            dict(m, author={"bot": True, "username": "Midjourney Bot"}, timestamp=ts) for m in msgs
        ]
        return resp

    def test_waits_for_finished_variation_grid(self, api):
        in_progress = {"id": "new", "content": f"**{PROMPT}** - Variations (Strong) (32%)", "components": []}
        done = _grid_message("new", content=f"{PROMPT}** - Variations (Strong) by <@1>")
        with patch("libs.midjourney.midjourney_api.time.sleep"), \
             patch("libs.midjourney.midjourney_api.requests.get",
                   side_effect=[self._messages(in_progress), self._messages(done)]):
            result = api.vary("upscaled-msg", "MJ::JOB::high_variation::1::x::SOLO", PROMPT)
        assert result["id"] == "new"
        api._click_button.assert_called_once_with("upscaled-msg", "MJ::JOB::high_variation::1::x::SOLO")

    def test_ignores_the_image_it_was_clicked_on(self, api):
        same = _grid_message("upscaled-msg")
        new = _grid_message("new")
        with patch("libs.midjourney.midjourney_api.time.sleep"), \
             patch("libs.midjourney.midjourney_api.requests.get", return_value=self._messages(same, new)):
            assert api.vary("upscaled-msg", "cid", PROMPT)["id"] == "new"

    def test_timeout_mentions_remix(self, api):
        clock = iter([0, 0, 1000])
        with patch("libs.midjourney.midjourney_api.time.sleep"), \
             patch("libs.midjourney.midjourney_api.time.time", side_effect=lambda: next(clock)), \
             patch("libs.midjourney.midjourney_api.requests.get", return_value=self._messages()):
            with pytest.raises(TimeoutError, match="Remix mode"):
                api.vary("m", "cid", PROMPT, timeout=60)


# =============================================================================
# History store
# =============================================================================


class TestHistoryStore:
    def test_chain_and_cover(self, tmp_path):
        g1 = cover_history.add_grid(tmp_path, DAY, _grid_message("g1"), PROMPT,
                                    extract_upscale_buttons(_grid_message("g1")["components"]), _fake_download)
        img = cover_history.add_image(tmp_path, DAY, g1["id"], "U2", _upscale_message("u1"),
                                      extract_vary_buttons(_upscale_message("u1")["components"]), _fake_download)
        g2 = cover_history.add_grid(tmp_path, DAY, _grid_message("g2"), PROMPT, {}, _fake_download,
                                    source="subtle", parent=img["id"])

        assert (g1["id"], img["id"], g2["id"]) == (1, 2, 3)
        assert g1["file"] == "1-grid.png" and img["file"] == "2.png"
        assert (tmp_path / DAY / "mateusztront.jpg").exists()  # upscaled image became the cover

        view = cover_history.view(tmp_path, DAY)
        assert [i["id"] for i in view["items"]] == [3, 2, 1]  # newest first
        assert view["cover"] == 2
        assert view["items"][0]["parent"] == 2 and view["items"][0]["source"] == "subtle"
        assert view["items"][1]["can_vary"] == {"subtle": True, "strong": True}
        assert view["items"][2]["picked"] == {"U2": 2}
        assert view["items"][1]["url"] == f"/{DAY}/_cover_history/2.png"
        assert "vary" not in view["items"][1]  # button ids stay server-side

    def test_any_image_can_become_cover_again(self, tmp_path):
        g = cover_history.add_grid(tmp_path, DAY, _grid_message("g"), PROMPT, {}, _fake_download)
        first = cover_history.add_image(tmp_path, DAY, g["id"], "U1", _upscale_message("a"), {}, _fake_download)
        cover_history.add_image(tmp_path, DAY, g["id"], "U3", _upscale_message("b"), {}, _fake_download)
        assert cover_history.load(tmp_path, DAY)["cover"] == 3

        cover_history.set_cover(tmp_path, DAY, first["id"])
        assert cover_history.load(tmp_path, DAY)["cover"] == first["id"]
        assert (tmp_path / DAY / "mateusztront.jpg").read_bytes() == \
               (tmp_path / DAY / "_cover_history" / first["file"]).read_bytes()

    def test_grid_cannot_be_cover(self, tmp_path):
        g = cover_history.add_grid(tmp_path, DAY, _grid_message("g"), PROMPT, {}, _fake_download)
        with pytest.raises(cover_history.HistoryError, match="is a grid"):
            cover_history.set_cover(tmp_path, DAY, g["id"])

    def test_empty_and_unreadable_history(self, tmp_path):
        assert cover_history.view(tmp_path, DAY) == {"items": [], "cover": None}
        folder = tmp_path / DAY / "_cover_history"
        folder.mkdir(parents=True)
        (folder / "history.json").write_text("{broken")
        assert cover_history.load(tmp_path, DAY) == {"items": [], "cover": None}

    def test_prune_before(self, tmp_path):
        for day in ("2026-11-20", "2026-11-21", "2026-11-22", "2026-11-23"):
            (tmp_path / day / "_cover_history").mkdir(parents=True)
            (tmp_path / day / "cover.jpg").write_bytes(b"x")
        (tmp_path / "_cover_history").mkdir()  # not a date folder: left alone

        assert cover_history.prune_before(tmp_path, "2026-11-22") == ["2026-11-20", "2026-11-21"]
        assert not (tmp_path / "2026-11-21" / "_cover_history").exists()
        assert (tmp_path / "2026-11-21" / "cover.jpg").exists()  # the published cover stays
        assert (tmp_path / "2026-11-22" / "_cover_history").exists()
        assert (tmp_path / "2026-11-23" / "_cover_history").exists()
        assert (tmp_path / "_cover_history").exists()


# =============================================================================
# The exposed functions the page calls
# =============================================================================


class FakeMJ:
    """Stands in for MidjourneyWrapper: each call returns the next Discord message."""

    def __init__(self):
        self.grids = 0
        self.upscales = 0
        self.vary_calls = []

    def generate_grid(self, prompt):
        self.grids += 1
        return _grid_message(f"grid{self.grids}")

    def upscale(self, message_id, custom_id):
        self.upscales += 1
        return _upscale_message(f"up{self.upscales}")

    def vary(self, message_id, custom_id, prompt):
        self.vary_calls.append((message_id, custom_id, prompt))
        self.grids += 1
        return _grid_message(f"grid{self.grids}")

    def download(self, url, path):
        return _fake_download(url, path)


class TestExposedFlow:
    @pytest.fixture
    def mj(self, tmp_path):
        fake = FakeMJ()
        with patch.object(cg, "MidjourneyWrapper", return_value=fake), patch.object(cg, "WEB_DIR", tmp_path):
            yield fake

    def test_prompt_upscale_vary_upscale_pick_older(self, mj, tmp_path):
        grid = cg.generate_cover_grid(DAY, PROMPT)
        assert grid["grid_id"] == 1 and grid["grid_url"] == f"/{DAY}/_cover_history/1-grid.png"

        assert cg.upscale_cover(DAY, grid["message_id"], grid["buttons"]["U3"]) == f"/{DAY}/mateusztront.jpg"

        varied = cg.vary_cover(DAY, 2, "strong")
        assert varied["grid_id"] == 3
        assert mj.vary_calls == [("up1", "MJ::JOB::high_variation::1::up1::SOLO", PROMPT)]

        cg.upscale_cover(DAY, varied["message_id"], varied["buttons"]["U1"])
        history = cg.get_cover_history(DAY)
        assert history["cover"] == 4
        newest = history["items"][0]
        assert (newest["id"], newest["grid"], newest["variant"]) == (4, 3, "U1")
        assert history["items"][1]["source"] == "strong" and history["items"][1]["parent"] == 2

        # Fresh prompt: a new chain in the same day
        assert cg.generate_cover_grid(DAY, "A shepherd with sheep")["grid_id"] == 5

        # Go back to the first image and publish that one
        assert cg.use_history_cover(DAY, 2) == f"/{DAY}/mateusztront.jpg"
        assert cg.get_cover_history(DAY)["cover"] == 2

    def test_old_grid_can_be_picked_again(self, mj):
        grid = cg.generate_cover_grid(DAY, PROMPT)
        cg.upscale_cover(DAY, grid["message_id"], grid["buttons"]["U1"])
        cg.upscale_cover(DAY, grid["message_id"], grid["buttons"]["U4"])
        grid_item = cg.get_cover_history(DAY)["items"][-1]
        assert grid_item["picked"] == {"U1": 2, "U4": 3}

    def test_errors_come_back_as_messages(self, mj):
        assert "No #9" in cg.vary_cover(DAY, 9, "subtle")["error"]
        assert cg.vary_cover(DAY, 1, "medium")["error"].startswith("Unknown variation strength")
        assert cg.use_history_cover(DAY, 9).startswith("Error: No #9")
        assert cg.upscale_cover(DAY, "unknown-msg", "cid").startswith("Error:")

    def test_image_without_vary_buttons(self, mj):
        grid = cg.generate_cover_grid(DAY, PROMPT)
        with patch.object(mj, "upscale", return_value={"id": "u", "attachments": [{"url": "https://x/i.png"}]}):
            cg.upscale_cover(DAY, grid["message_id"], grid["buttons"]["U1"])
        assert "no Vary (subtle) button" in cg.vary_cover(DAY, 2, "subtle")["error"]
        assert cg.get_cover_history(DAY)["items"][0]["can_vary"] == {"subtle": False, "strong": False}


class TestPruneOnPublish:
    def _setup(self, tmp_path):
        for day in ("2026-11-21", DAY):
            (tmp_path / day / "_cover_history").mkdir(parents=True)
        post = tmp_path / DAY
        Image.new("RGB", (50, 50), "white").save(post / "mateusztront.jpg")
        (post / "EWANGELIA1.jpg").write_bytes(b"fake")

    def _client(self, ok=True):
        client = MagicMock()
        if ok:
            client.album_upload.return_value = MagicMock(code="C")
        else:
            client.album_upload.side_effect = RuntimeError("Instagram down")
        return client

    def test_publishing_a_day_clears_earlier_days(self, tmp_path):
        self._setup(tmp_path)
        with patch.object(cg, "WEB_DIR", tmp_path), patch.object(cg, "login_user", return_value=self._client()):
            assert cg.publish(DAY, "caption") == ""
        assert not (tmp_path / "2026-11-21" / "_cover_history").exists()
        assert (tmp_path / DAY / "_cover_history").exists()  # kept until the next day is published

    def test_failed_publish_keeps_history(self, tmp_path):
        self._setup(tmp_path)
        with patch.object(cg, "WEB_DIR", tmp_path), patch.object(cg, "login_user", return_value=self._client(False)):
            assert cg.publish(DAY, "caption").startswith("Failed to publish")
        assert (tmp_path / "2026-11-21" / "_cover_history").exists()

    def test_history_folder_is_not_posted(self, tmp_path):
        self._setup(tmp_path)
        (tmp_path / DAY / "_cover_history" / "1-grid.png").write_bytes(b"x")
        client = self._client()
        with patch.object(cg, "WEB_DIR", tmp_path), patch.object(cg, "login_user", return_value=client):
            cg.publish(DAY, "caption")
        paths = client.album_upload.call_args.kwargs["paths"]
        assert len(paths) == 2 and not any("_cover_history" in p for p in paths)
