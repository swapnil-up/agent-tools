import puppeteer from "puppeteer";

const USAGE = `headless-fetch <url> [options]

Render a JS-heavy page in a real (headless) browser and dump the result
as plain text. Useful when plain HTTP fetching fails because a site
renders its content with JavaScript.

For sites behind Cloudflare bot protection, first run:
  node scripts/get-session.mjs <url> --out session.json
and solve the challenge by hand, then pass --session here.

Options:
  --mode <text|html|links|markdown>   what to output (default: text)
  --wait-for <selector>               wait for this CSS selector before dumping
  --wait-ms <ms>                      fixed extra wait after load (default 1500)
  --timeout <ms>                      per-navigation timeout (default 30000)
  --viewport <WxH>                    browser viewport (default 1366x900)
  --user-agent <string>               override user agent
  --cookie <name=value>               inject a cookie (repeatable)
  --session <file>                    load cookies + UA saved by get-session.mjs
  --click <selector>                  click this element before dumping (repeatable)
  --scroll                             scroll to bottom to trigger lazy loading
  --out <file>                        write output to file instead of stdout
  --debug                             print browser console + keep things verbose
  --help                              show this help
`;

const args = process.argv.slice(2);
if (args.length === 0 || args.includes("--help")) {
  console.log(USAGE);
  process.exit(args.includes("--help") ? 0 : 1);
}

const url = args[0];
const opts = {
  mode: "text",
  waitFor: null,
  waitMs: 1500,
  timeout: 30000,
  viewport: "1366x900",
  userAgent: null,
  cookies: [],
  session: null,
  clicks: [],
  scroll: false,
  out: null,
  debug: false,
};

for (let i = 1; i < args.length; i++) {
  const a = args[i];
  switch (a) {
    case "--mode": opts.mode = args[++i]; break;
    case "--wait-for": opts.waitFor = args[++i]; break;
    case "--wait-ms": opts.waitMs = parseInt(args[++i], 10); break;
    case "--timeout": opts.timeout = parseInt(args[++i], 10); break;
    case "--viewport": opts.viewport = args[++i]; break;
    case "--user-agent": opts.userAgent = args[++i]; break;
    case "--cookie": opts.cookies.push(args[++i]); break;
    case "--session": opts.session = args[++i]; break;
    case "--click": opts.clicks.push(args[++i]); break;
    case "--scroll": opts.scroll = true; break;
    case "--out": opts.out = args[++i]; break;
    case "--debug": opts.debug = true; break;
    default: break;
  }
}

const [vw, vh] = opts.viewport.split("x").map(Number);

// A normal desktop Chrome UA. The default Puppeteer UA advertises
// "HeadlessChrome", which bot challenges reject on sight.
const DEFAULT_UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const browser = await puppeteer.launch({
  headless: "new",
  // Drop --enable-automation (which flips navigator.webdriver to true) and
  // blank out the obvious automation feature flag, so bot challenges are
  // less likely to reject us outright.
  ignoreDefaultArgs: ["--enable-automation"],
  args: [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
  ],
});

try {
  const page = await browser.newPage();
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
  });
  await page.setViewport({ width: vw, height: vh });

  await page.setUserAgent(opts.userAgent || DEFAULT_UA);
  if (opts.session) {
    const { readFile } = await import("node:fs/promises");
    const session = JSON.parse(await readFile(opts.session, "utf8"));
    if (!opts.userAgent && session.ua) {
      await page.setUserAgent(session.ua);
    }
    if (session.cookies?.length) {
      await page.setCookie(...session.cookies.map((c) => ({
        name: c.name,
        value: c.value,
        domain: c.domain,
        path: c.path || "/",
        secure: !!c.secure,
        httpOnly: !!c.httpOnly,
        sameSite: c.sameSite,
        expires: c.expires,
      })));
    }
  }
  if (opts.cookies.length) {
    const parsed = opts.cookies.map((c) => {
      const [name, ...rest] = c.split("=");
      return { name, value: rest.join("="), url };
    });
    await page.setCookie(...parsed);
  }

  if (opts.debug) {
    page.on("console", (m) => console.error(`[console] ${m.text()}`));
    page.on("requestfailed", (r) =>
      console.error(`[reqfail] ${r.url()} ${r.failure()?.errorText ?? ""}`)
    );
  }

  // Some apps (Upwork, chat UIs) never reach "networkidle0" because they
  // hold long-lived connections open. If idle never settles, fall back to
  // whatever has loaded and carry on.
  try {
    await page.goto(url, { waitUntil: "networkidle0", timeout: opts.timeout });
  } catch (e) {
    // The navigation itself already happened; only the idle wait gave up.
    // Continue with the DOM as-is.
    if (opts.debug) console.error(`[nav] ${e.message} -- continuing with loaded DOM`);
  }

  if (opts.waitFor) {
    await page.waitForSelector(opts.waitFor, { timeout: opts.timeout });
  }

  for (const sel of opts.clicks) {
    await page.click(sel, { timeout: opts.timeout });
    await new Promise((r) => setTimeout(r, 800));
  }

  if (opts.scroll) {
    await page.evaluate(async () => {
      const step = 800;
      for (let y = 0; y < document.body.scrollHeight; y += step) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 150));
      }
      window.scrollTo(0, 0);
    });
  }

  await new Promise((r) => setTimeout(r, opts.waitMs));

  let output = "";
  switch (opts.mode) {
    case "html":
      output = await page.content();
      break;
    case "links":
      output = await page.evaluate(() =>
        Array.from(document.querySelectorAll("a"))
          .map((a) => `${a.textContent.trim()} -> ${a.href}`)
          .join("\n")
      );
      break;
    case "markdown":
      output = await page.evaluate(() => {
        const md = (el) => {
          if (el.nodeType === Node.TEXT_NODE) return el.textContent.trim() + " ";
          if (el.nodeType !== Node.ELEMENT_NODE) return "";
          const tag = el.tagName.toLowerCase();
          let text = "";
          if (["script", "style", "noscript", "svg", "iframe"].includes(tag)) return "";
          for (const child of el.childNodes) text += md(child);
          text = text.replace(/\s+/g, " ").trim();
          if (tag === "h1") return `# ${text}\n\n`;
          if (tag === "h2") return `## ${text}\n\n`;
          if (tag === "h3") return `### ${text}\n\n`;
          if (tag === "li") return `- ${text}\n`;
          if (tag === "p") return `${text}\n\n`;
          if (tag === "a") return `[${text}](${el.href})`;
          if (tag === "strong" || tag === "b") return `**${text}**`;
          if (tag === "em" || tag === "i") return `*${text}*`;
          if (tag === "code") return `\`${text}\``;
          if (tag === "br") return "\n";
          if (tag === "table") return `\n| ROW |\n` + text + `\n`;
          return text;
        };
        return md(document.body);
      });
      break;
    case "text":
    default:
      output = await page.evaluate(() => document.body.innerText);
      break;
  }

  if (opts.out) {
    const { writeFile } = await import("node:fs/promises");
    await writeFile(opts.out, output);
    console.error(`wrote ${output.length} bytes to ${opts.out}`);
  } else {
    process.stdout.write(output);
    if (!output.endsWith("\n")) process.stdout.write("\n");
  }
} finally {
  await browser.close();
}
