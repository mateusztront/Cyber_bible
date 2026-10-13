# A Dockerfile is a recipe. Each line is a step, read top to bottom.

# 1. Start FROM a base image: a minimal Linux that already has Python 3.12.
FROM python:3.12-slim

# 2. Set the working directory INSIDE the container. Like `cd /app`.
WORKDIR /app

# 3. Copy the requirements file in, then install the libraries.
#    We copy this FIRST (before the code) so Docker can cache this slow step
#    and skip it when only your code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your code into the container.
COPY . .

# 5. Tell Docker this app listens on port 8000 (documentation + tooling hint).
EXPOSE 8000

# 6. The command that runs when the container starts.
#    0.0.0.0 means "listen on all network interfaces" — required so the
#    outside world (your phone, AWS) can reach it, not just localhost.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
