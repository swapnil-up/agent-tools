# agent-tools

Tools that bridge the gap between an agent (which cannot see your screen) and
a human sitting at the machine. Each subfolder is one way of getting the human
to point at / interact with something visual and serializing the result into
machine-readable files the agent can consume.

## Subfolders

| Folder | Purpose |
|---|---|
| [`headless-fetch/`](headless-fetch/) | Drive a real Chromium to render JS-heavy pages to text/HTML/links/markdown. Includes `get-session` (open a visible browser, solve a Cloudflare challenge by hand, save cookies + UA for replay) and `netwatch` (log `/api/` calls). |
| [`mark-boxes/`](mark-boxes/) | Show an image in a window, let the user drag rectangles over it, and save original-pixel + pt coordinates to JSON for the agent. |

## Pattern

Both tools follow the same shape:

1. The agent launches a *visible* thing (a browser window, an image window).
2. The human does something only a human can do (solve a captcha, mark a
   column boundary) that the agent cannot.
3. The tool saves the result to a file (session JSON, boxes JSON).
4. The agent reads the file and proceeds.

This repo was provisionally named `agent-tools`; the parent directory and
GitHub repo name will be renamed later.
