# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cyber Bible is a desktop application that automates creating and publishing liturgical reading graphics to Instagram. It scrapes daily Bible readings from Polish liturgy sources, renders them as images with justified text on parchment backgrounds, and publishes to Instagram as carousel posts.

## Commands

```bash
# Install dependencies (uses uv package manager)
uv sync

# Install with dev dependencies (pytest, etc.)
uv sync --extra dev

# Run the application
uv run python main.py

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=. --cov-report=term-missing

# Run a single test file
uv run pytest tests/test_create_graphic.py -v
```

## Architecture

### Core Pipeline
1. **Scraping** (`create_graphic.py`): Fetches readings from `liturgia.wiara.pl`, cross-checked with `brewiarz.pl`
2. **Processing** (`create_graphic.py`): Parses HTML, normalizes content, handles reading variants (shorter/longer versions)
3. **Rendering** (`draw_posts.py`): PIL-based text rendering with justified alignment, automatic pagination for long readings
4. **Publishing** (`login.py`, `create_graphic.py`, `social.py`): Instagram upload via instagrapi with session management; Facebook Page (Graph API) and X (API v2, OAuth 1.0a, threads of 4 images) via `social.py`. `publish(..., platforms)` runs each selected platform independently

### Key Modules
- **`main.py`**: Eel-based desktop app entry point (Chrome/browser GUI on port 8000)
- **`config.py`**: Centralized settings, paths, credentials from `.env`
- **`create_graphic.py`**: Main orchestrator with `@eel.expose` functions callable from JS frontend
- **`draw_posts.py`**: Image text rendering engine with `PageType` enum for pagination states
- **`login.py`**: Instagram auth with session persistence and 2FA support
- **`social.py`**: Facebook Page and X publishing (setup steps in README.md)
- **`cover_history.py`**: per-day Midjourney history in `web/{date}/_cover_history/` (grids + upscaled images with lineage, `history.json`). Upscaling makes an image the cover (`web/{date}/mateusztront.jpg`); any history image can be made the cover again; Vary (Subtle/Strong) on an image clicks the button saved from its upscale message (`MidjourneyApi.vary`, fails with a timeout if Remix mode is on). A successful publish of date D deletes the histories of all days before D.

### Frontend
- **`web/`**: Eel frontend (index.html, script.js) communicates with Python via `eel.draw_post()`, `eel.publish()`, etc.
- **`web/connection.js`**: Patches eel.js so calls survive phones dropping the websocket (reconnect, fail pending calls on close, timeouts). `publish()` writes `web/{date}/_published.json` (one entry per platform under `platforms`; top-level `published_at`/`media_code` are Instagram's, as in older markers) and refuses to post a date twice on a platform unless `force` is passed.
- **Logs**: stdout plus `logs/app.log` (rotating). The browser reports reconnects there via `client_log()`.

### Data Flow
```
liturgia.wiara.pl → scrape → parse readings dict → render images → web/{date}/*.jpg → Instagram / Facebook / X
```

### Reading Types
The app handles multiple Polish liturgy readings:
- PIERWSZE CZYTANIE (First Reading)
- PSALM RESPONSORYJNY (Responsorial Psalm)
- DRUGIE CZYTANIE (Second Reading, when present)
- EWANGELIA (Gospel)

Weekday feasts with two first readings to choose from (e.g. 9 Nov: Ez 47 *albo* 1 Kor 3): liturgia.wiara.pl prints the alternative as DRUGIE CZYTANIE. `_apply_first_reading_choice()` cross-checks the day on **brewiarz.pl** (the reference; no DRUGIE CZYTANIE there = no second reading), keeps one first reading (`first_reading_choice` 0/1, picked in the UI selector that appears on such days) and moves the Gospel acclamation onto the psalm. If brewiarz.pl is unreachable it falls back to `FEASTS_WITH_ALTERNATIVE_FIRST_READING` on non-Sundays.

### Pagination Logic
Long readings automatically paginate using font size reduction first (down to `FONT_SIZE_MIN`), then split into 2 or 4 pages via `draw_text_pagination_*` functions.

## Workflow Rules

- Git commit and push after completing major changes or features
- Pushing to `master` deploys: the production server picks up every new `master` commit within ~2 minutes and rebuilds the app. So work on `master` (not the stale `main`), push only finished, tested changes, and push to `master` itself rather than a side branch when the user wants a change live. A push to any other branch goes nowhere until it is merged into `master`.

## Environment Variables

Copy `.env.example` to `.env` and set:
- `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` - Required for publishing
- `FACEBOOK_PAGE_ID` / `FACEBOOK_PAGE_TOKEN` - Optional, Facebook Page publishing
- `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` - Optional, X publishing (pay-per-use)
- `ELEVENLABS_API_KEY` - Optional, for TTS features
