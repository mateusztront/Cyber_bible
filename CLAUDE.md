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
1. **Scraping** (`create_graphic.py`): Fetches readings from `liturgia.wiara.pl` and Vatican News
2. **Processing** (`create_graphic.py`): Parses HTML, normalizes content, handles reading variants (shorter/longer versions)
3. **Rendering** (`draw_posts.py`): PIL-based text rendering with justified alignment, automatic pagination for long readings
4. **Publishing** (`login.py`, `create_graphic.py`): Instagram upload via instagrapi with session management

### Key Modules
- **`main.py`**: Eel-based desktop app entry point (Chrome/browser GUI on port 8000)
- **`config.py`**: Centralized settings, paths, credentials from `.env`
- **`create_graphic.py`**: Main orchestrator with `@eel.expose` functions callable from JS frontend
- **`draw_posts.py`**: Image text rendering engine with `PageType` enum for pagination states
- **`login.py`**: Instagram auth with session persistence and 2FA support

### Frontend
- **`web/`**: Eel frontend (index.html, script.js) communicates with Python via `eel.draw_post()`, `eel.publish()`, etc.

### Data Flow
```
liturgia.wiara.pl → scrape → parse readings dict → render images → web/{date}/*.jpg → Instagram
```

### Reading Types
The app handles multiple Polish liturgy readings:
- PIERWSZE CZYTANIE (First Reading)
- PSALM RESPONSORYJNY (Responsorial Psalm)
- DRUGIE CZYTANIE (Second Reading, when present)
- EWANGELIA (Gospel)

### Pagination Logic
Long readings automatically paginate using font size reduction first (down to `FONT_SIZE_MIN`), then split into 2 or 4 pages via `draw_text_pagination_*` functions.

## Workflow Rules

- Git commit and push after completing major changes or features

## Environment Variables

Copy `.env.example` to `.env` and set:
- `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` - Required for publishing
- `ELEVENLABS_API_KEY` - Optional, for TTS features
