# headless-fetch

Render JavaScript-heavy web pages to plain text, HTML, links, or markdown for CLI/agent consumption. When a site renders its content with JS (SPAs like `app.unv.org`, Catchafire, Idealist), a plain HTTP fetch returns an empty shell. This tool drives a real headless Chromium instead.

## Install

```
npm install   # pulls puppeteer + chromium
```

## Usage

```
node index.js <url> [options]
```

### Options

| Flag | Default | Purpose |
|---|---|---|
| `--mode text\|html\|links\|markdown` | `text` | Output format |
| `--wait-for <selector>` | — | Wait for a CSS selector before dumping |
| `--wait-ms <ms>` | `1500` | Fixed extra wait after load |
| `--timeout <ms>` | `30000` | Per-navigation timeout |
| `--viewport <WxH>` | `1366x900` | Browser viewport |
| `--user-agent <string>` | — | Override UA |
| `--cookie <name=value>` | — | Inject a cookie (repeatable) |
| `--click <selector>` | — | Click element before dumping (repeatable) |
| `--scroll` | — | Scroll to bottom to trigger lazy loading |
| `--out <file>` | — | Write to file instead of stdout |
| `--debug` | — | Print browser console + failed requests |
| `--help` | — | Show help |

## Examples

```
# Dump a SPA's visible text
node index.js "https://app.unv.org/opportunities/1784888021271034" --wait-for ".card"

# Save rendered HTML for parsing
node index.js "https://idealist.org/en/volunteer?keyword=web" --mode html --out page.html

# Scrape links
node index.js "https://example.com" --mode links

# Lazy-loaded feed
node index.js "https://example.com/feed" --scroll --wait-ms 3000
```

## Cloudflare / bot-protected sites

Two situations, two tools:

**A. Managed challenge (JS/checkbox) — usually just needs a real browser window.**
Headless Chromium is blocked, but a *visible* browser passes the managed
challenge automatically after a few seconds (no clicking needed). Try this first:

```
npm run headed-fetch -- "https://www.catchafire.org/volunteer/" --out projects.txt
```

It polls until the "Verifying you are human" page clears, then dumps content.
Caveat: a browser window flashes on screen; low-volume, personal use only.

**B. Interactive challenge (manual checkbox / Turnstile) — solve once, replay session.**
Open a visible browser, solve by hand, save cookies + matching user-agent:

```
npm run get-session -- "https://example.com/" --out session.json
node index.js "https://example.com/" --session session.json
```

Notes on `--session`:
- The `cf_clearance` cookie is bound to the **user-agent + IP + browser fingerprint** that earned it. Replay works only from the same IP; the fingerprint gap between the solving session and a fresh headless instance may still cause re-challenges on strict sites.
- Clearance cookies expire (Cloudflare TTLs them, often 15–60 min for managed challenges). Re-run step 1 when fetches get challenged again.
- This will NOT beat interactive Turnstile/captcha that demand a fresh solve every request.
- Use these for personal, low-volume reading of public pages. Respect robots.txt and each site's terms.

## Network watcher

`npm run netwatch -- <url>` logs all `/api/` requests (URL + status + JSON keys for responses, body for POSTs). Useful for reverse-engineering a site's underlying JSON API to call it directly.

## Notes

- Launches headless Chromium via puppeteer with `--no-sandbox` (for Linux rootless/container environments).
- Some sites (Catchafire) sit behind Cloudflare bot protection that blocks headless browsers entirely — no JS-rendering tool bypasses that without more work.
- The user agent defaults to headless Chrome; pass `--user-agent` if a site sniffs for it.
