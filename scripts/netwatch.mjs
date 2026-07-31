import puppeteer from "puppeteer";
const url = process.argv[2] || "https://example.com";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox"] });
const page = await browser.newPage();
page.on("response", async (r) => {
  if (r.url().includes("/api/")) {
    console.log(`[API] ${r.status()} ${r.request().method()} ${r.url()}`);
    try { const j = await r.json(); console.log("  keys:", Object.keys(j).slice(0,12).join(", ")); }
    catch { console.log("  (not json)"); }
  }
});
page.on("request", (r) => {
  if (r.url().includes("/api/") && r.method() === "POST")
    console.log(`[POST] ${r.url()}\n  ${r.postData()?.slice(0,400)}`);
});
await page.goto(url, { waitUntil: "networkidle0", timeout: 45000 });
await new Promise((r) => setTimeout(r, 6000));
await browser.close();
