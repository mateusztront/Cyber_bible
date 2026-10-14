# Cyber Bible in a container. Same recipe as docker-learning/, plus uv,
# headless mode, and secrets/fonts kept OUTSIDE the image (see compose.yaml).

# 1. Base image: minimal Linux with Python 3.10 (matches .python-version).
FROM python:3.10-slim

# 2. Copy the uv binary in from its official image instead of pip-installing it.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 3. Install libraries FIRST (cached until pyproject.toml or uv.lock change).
#    --frozen     = use uv.lock exactly, never re-resolve versions
#    --no-dev     = skip pytest & co.
#    --no-install-project = only the libraries; our code comes in step 5
#    UV_PYTHON_DOWNLOADS=never = use the image's Python, don't fetch another
ENV UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 4. Put the virtualenv uv created first on PATH, so `python` means that one.
ENV PATH="/app/.venv/bin:$PATH"

# 5. Run as a normal user, not root. uid 1000 = your user on the host, so files
#    the app writes into mounted folders (web/, session.json) stay yours.
RUN useradd --create-home --uid 1000 appuser
COPY --chown=appuser:appuser . .
USER appuser

# 6. No screen inside a container: serve the page on 0.0.0.0:8000 instead of
#    opening a Chrome window. This is the HEADLESS mode from config.py.
ENV HEADLESS=1
EXPOSE 8000

CMD ["python", "main.py"]
