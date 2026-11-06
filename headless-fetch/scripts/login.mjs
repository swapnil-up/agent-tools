import puppeteer from "puppeteer";
import { writeFileSync } from "node:fs";
import * as readline from "node:readline";

const USAGE = `login <url> [options]

Open a VISIBLE browser, let you log in / clear any bot challenge by hand,
then save ALL cookies (plus the user agent) to a session file for replay.

Unlike get-session.mjs (which saves as soon as a cf_clearance cookie shows
up), this waits until YOU are done -- so it captures post-login auth cookies
too. Use it for sites that need an account, not just a Cloudflare pass.

Options:
  --out <file>      session file path (default: login-session.json)
  --ua <string>     override user agent (default: a common Chrome UA)
  --connect <port>  attach to an ALREADY-RUNNING Chromium on this remote
                    debugging port instead of launching a new browser. Use
                    this to reuse a browser you opened and logged into yourself.

Two ways to use it:

  A) Let this script open the browser:
       node scripts/login.mjs https://www.catchafire.org/volunteer/ --out s.json
     It launches Chromium with automation signals hidden (so Cloudflare's
     "verify you are human" clears), you sign in, then press Enter here.

  B) Reuse a browser you already have open:
       chromium --remote-debugging-port=9222 --user-data-dir=/tmp/opt-chrome
     log in there, then:
       node scripts/login.mjs https://www.catchafire.org/volunteer/ \\
            --connect 9222 --out s.json

Press Enter in this terminal when the page shows what you want saved.`;

const args = process.argv.slice(2);
if (args.length === 0 || args.includes("--help")) {
  console.log(USAGE);
  process.exit(args.includes("--help") ? 0 : 1);
}

const url = args[0];
let out = "login-session.json";
let ua = null;
let connectPort = null;
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--out") out = args[++i];
  else if (args[i] === "--ua") ua = args[++i];
  else if (args[i] === "--connect") connectPort = args[++i];
}

const CHROME_UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

// Args that hide the usual automation tells so Cloudflare's interactive
// Turnstile will clear in a headed window.
const STEALTH_ARGS = [
  "--no-sandbox",
  "--disable-dev-shm-usage",
  "--disable-blink-features=AutomationControlled",
  "--start-maximized",
];

let browser;
let attached = false;
if (connectPort) {
  browser = await puppeteer.connect({
    browserURL: `http://127.0.0.1:${connectPort}`,
    defaultViewport: null,
  });
  attached = true;
  console.log(`\n>>> Attached to Chromium on port ${connectPort}`);
} else {
  browser = await puppeteer.launch({
    headless: false,
    ignoreDefaultArgs: ["--enable-automation"],
    args: STEALTH_ARGS,
    defaultViewport: null,
  });
  console.log("\n>>> Launched a visible Chromium (automation signals hidden).");
}

try {
  const finalUA = ua ?? CHROME_UA;

  let page;
  if (attached) {
    const pages = await browser.pages();
    page = pages.find((p) => p.url().includes(new URL(url).host)) || pages[0];
    if (!page) page = await browser.newPage();
  } else {
    page = await browser.newPage();
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    });
    await page.setUserAgent(finalUA);
  }
  console.log(`>>> UA: ${finalUA}`);

  if (!attached || !page.url().startsWith("http")) {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 120000 });
  } else {
    console.log(`>>> Using already-open tab: ${page.url()}`);
  }

  console.log(">>> Log in / clear any challenge in the browser window.");
  console.log(">>> When the page shows what you want saved, come back here and press Enter.\n");

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  await new Promise((resolve) => rl.question("Press Enter to save cookies... ", resolve));
  rl.close();

  const cookies = await page.cookies();
  const session = {
    url,
    ua: finalUA,
    savedAt: new Date().toISOString(),
    cookies,
  };
  writeFileSync(out, JSON.stringify(session, null, 2));
  console.log(`\nSaved ${cookies.length} cookies -> ${out}`);
} finally {
  if (attached) {
    // Leave the user's browser running; just detach.
    browser.disconnect();
  } else {
    await browser.close();
  }
}
