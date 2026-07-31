import puppeteer from "puppeteer";
import { writeFileSync } from "node:fs";

const USAGE = `headed-fetch <url> [--out file] [--wait-ms ms] [--timeout ms] [--mode text|html|links|markdown]

Like index.js, but runs a VISIBLE browser. Cloudflare's managed challenge
auto-resolves in a headed browser after a few seconds (no interaction
needed), but blocks headless Chromium outright. Polls until the challenge
clears, then dumps the rendered content.

Default --wait-ms is 15000 to give the challenge time to auto-resolve.
`;

const args = process.argv.slice(2);
if (args.length === 0 || args.includes("--help")) { console.log(USAGE); process.exit(args.includes("--help") ? 0 : 1); }
const url = args[0];
let out = null, waitMs = 15000, timeout = 60000, mode = "text";
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--out") out = args[++i];
  else if (args[i] === "--wait-ms") waitMs = parseInt(args[++i], 10);
  else if (args[i] === "--timeout") timeout = parseInt(args[++i], 10);
  else if (args[i] === "--mode") mode = args[++i];
}

const browser = await puppeteer.launch({ headless: false, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout });
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const text = await page.evaluate(() => document.body.innerText || "");
    if (!/Verifying you are human|Performing security verification/i.test(text)) break;
    await new Promise((r) => setTimeout(r, 2000));
  }
  await new Promise((r) => setTimeout(r, waitMs));

  let output = "";
  if (mode === "html") output = await page.content();
  else if (mode === "links") output = await page.evaluate(() => Array.from(document.querySelectorAll("a")).map((a) => `${a.textContent.trim()} -> ${a.href}`).join("\n"));
  else output = await page.evaluate(() => document.body.innerText);

  if (out) { writeFileSync(out, output); console.error(`wrote ${output.length} bytes to ${out}`); }
  else process.stdout.write(output + "\n");
} finally {
  await browser.close();
}
