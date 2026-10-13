"""
The simplest possible web app with a button.
This is a tiny rehearsal for Cyber Bible: a page you open on your phone,
tap a button, and the server does something.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# A counter living in the server's memory (resets when the container restarts).
clicks = 0

PAGE = """
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Docker Hello</title>
    <style>
      body {{ font-family: sans-serif; text-align: center; padding-top: 20vh; }}
      button {{ font-size: 1.5rem; padding: 1rem 2rem; border-radius: 12px; }}
    </style>
  </head>
  <body>
    <h1>Hello from inside a Docker container 🐳</h1>
    <p>This button has been pressed <b>{clicks}</b> times.</p>
    <form action="/press" method="post">
      <button type="submit">Press me</button>
    </form>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE.format(clicks=clicks)


@app.post("/press", response_class=HTMLResponse)
def press():
    global clicks
    clicks += 1
    return PAGE.format(clicks=clicks)
