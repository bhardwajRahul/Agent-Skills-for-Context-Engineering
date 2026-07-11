// Capture before/after screenshots of the Long-Horizon Prompt Lab UI.
// Uses puppeteer-core driving the system Chrome. Produces, per use case:
//   <id>-full.png     the whole page (hero + prompts + scorecard + deltas)
//   <id>-split.png    just the before/after prompt panels (the money shot)
//   <id>-scorecard.png the rubric scorecard
// Plus hero.png (the aggregate banner) for the release header.
//
// Usage: node scripts/capture.mjs
import { existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const HERE = dirname(fileURLToPath(import.meta.url));
const LAB = resolve(HERE, "..");
const UI = resolve(LAB, "ui", "index.html");
const OUT = resolve(LAB, "screenshots");

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "/usr/bin/google-chrome-stable",
  "/usr/local/bin/google-chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);

function findChrome() {
  for (const p of CHROME_CANDIDATES) if (existsSync(p)) return p;
  throw new Error("No Chrome/Chromium found. Set CHROME_PATH.");
}

async function clipElement(page, selector, path, pad = 0) {
  const rect = await page.$eval(selector, (node) => {
    const r = node.getBoundingClientRect();
    return { x: r.x, y: r.y, width: r.width, height: r.height };
  });
  await page.screenshot({
    path,
    clip: {
      x: Math.max(0, rect.x - pad),
      y: Math.max(0, rect.y - pad),
      width: rect.width + pad * 2,
      height: rect.height + pad * 2,
    },
  });
  console.log("  wrote", path.replace(LAB + "/", ""));
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const executablePath = findChrome();
  console.log("Chrome:", executablePath);

  const browser = await puppeteer.launch({
    executablePath,
    headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--force-color-profile=srgb", "--hide-scrollbars"],
  });
  const page = await browser.newPage();
  const WIDTH = 1320;
  const CROP_DPR = 2; // crisp for the read-the-text money shots
  const FULL_DPR = 1; // overview context, kept light

  const base = pathToFileURL(UI).href;

  async function load(id, dpr) {
    await page.setViewport({ width: WIDTH, height: 1000, deviceScaleFactor: dpr });
    await page.goto(base + (id ? "#" + id : ""), { waitUntil: "networkidle0" });
    await page.reload({ waitUntil: "networkidle0" });
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  }

  await load("", CROP_DPR);
  const ids = await page.evaluate(() => window.PROMPT_LAB_DATA.pairs.map((p) => p.id));
  console.log("Use cases:", ids.join(", "));

  // Hero banner (aggregate) for the release header.
  await clipElement(page, "#hero", resolve(OUT, "hero.png"), 0);

  for (const id of ids) {
    console.log("Capturing", id);
    await load(id, CROP_DPR);
    const expected = await page.evaluate((pid) => window.PROMPT_LAB_DATA.pairs.find((p) => p.id === pid).title, id);
    const rendered = await page.$eval(".pair-head h2", (n) => n.textContent);
    if (rendered !== expected) {
      throw new Error(`Rendered pair "${rendered}" != expected "${expected}" for id ${id}`);
    }
    await clipElement(page, "#pair-split", resolve(OUT, `${id}-split.png`), 12);
    await clipElement(page, "#scorecard", resolve(OUT, `${id}-scorecard.png`), 12);

    await load(id, FULL_DPR);
    await page.screenshot({ path: resolve(OUT, `${id}-full.png`), fullPage: true });
    console.log("  wrote", `screenshots/${id}-full.png`);
  }

  await browser.close();
  console.log("Done. Screenshots in", OUT.replace(LAB + "/", ""));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
