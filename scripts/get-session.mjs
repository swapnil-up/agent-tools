import puppeteer from "puppeteer";
import { writeFileSync } from "node:fs";

const USAGE = `get-session <url> [--out session.json] [--ua <user-agent>] [--timeout <ms>]

Open a VISIBLE browser so you can manually solve a Cloudflare (or similar)
challenge. When a cf_clearance / cf_* cookie appears, saves:
  - the cookies (JSON)
  - the user agent that earned them

The saved file is meant to be passed to index.js via --session. Cookies are
bound to the UA + IP that created them, so both must match on replay.

Steps:
  1. A visible browser window opens at the URL.
  2. Solve any Cloudflare challenge / checkbox by hand.
  3. The script auto-detects the clearance cookie and saves the session.
  4. Ctrl-C anytime to abort (nothing is saved).

Options:
  --out <file>     session file path (default: session.json)
  --ua <string>    override user agent (default: a common Chrome UA)
  --timeout <ms>   max wait for clearance cookie (default: 120000)
`;

const args = process.argv.slice(2);
if (args.length === 0 || args.includes("--help")) {
  console.log(USAGE);
  process.exit(args.includes("--help") ? 0 : 1);
}

const url = args[0];
let out = "session.json";
let ua = null;
let timeout = 120000;

for (let i = 1; i < args.length; i++) {
  if (args[i] === "--out") out = args[++i];
  else if (args[i] === "--ua") ua = args[++i];
  else if (args[i] === "--timeout") timeout = parseInt(args[++i], 10);
}

const browser = await puppeteer.launch({
  headless: false,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});

try {
  const page = await browser.newPage();
  const finalUA = ua ?? (await browser.userAgent());
  await page.setUserAgent(finalUA);
  console.log(`\n>>> Solving session for: ${url}`);
  console.log(`>>> UA: ${finalUA}`);
  console.log(`>>> A visible browser opened. Solve the challenge by hand.\n`);

  await page.goto(url, { waitUntil: "domcontentloaded", timeout });
  console.log("Page loaded. Watching for a Cloudflare clearance cookie...\n");

  const start = Date.now();
  let cookies = [];
  while (Date.now() - start < timeout) {
    await new Promise((r) => setTimeout(r, 1500));
    cookies = await page.cookies();
    if (cookies.some((c) => c.name.startsWith("cf_clearance"))) break;
  }

  const clearance = cookies.filter((c) => c.name.startsWith("cf_clearance"));
  if (!clearance.length) {
    console.error("No cf_clearance cookie detected within the timeout. Nothing saved.");
    process.exit(1);
  }

  const session = {
    url,
    ua: finalUA,
    savedAt: new Date().toISOString(),
    cookies,
  };
  writeFileSync(out, JSON.stringify(session, null, 2));
  console.log(`\nSaved ${cookies.length} cookies (incl. cf_clearance) -> ${out}`);
} finally {
  await browser.close();
}
