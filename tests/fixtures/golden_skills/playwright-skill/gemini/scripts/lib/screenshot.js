const fs = require("fs");
const os = require("os");
const path = require("path");
const runtime = require("./runtime");

const DEFAULT_TITLE_SELECTOR = 'h1, h2, [role="heading"]';

function parseInteger(value, name, options = {}) {
  if (value === undefined || value === null || value === "") {
    if (Object.prototype.hasOwnProperty.call(options, "defaultValue")) {
      return options.defaultValue;
    }
    throw new Error(`${name} is required`);
  }

  const number = Number(value);
  const min = options.min;

  if (!Number.isInteger(number) || (min !== undefined && number < min)) {
    const suffix = min === undefined ? "" : ` >= ${min}`;
    throw new Error(`${name} must be an integer${suffix}`);
  }

  return number;
}

function parseViewport(value) {
  if (!value) {
    return { width: 1280, height: 720 };
  }

  if (typeof value === "object") {
    const width = parseInteger(value.width, "viewport.width", { min: 1 });
    const height = parseInteger(value.height, "viewport.height", { min: 1 });
    return { ...value, width, height };
  }

  const match = String(value).match(/^(\d+)x(\d+)$/i);
  if (!match) {
    throw new Error(
      `Invalid viewport '${value}'. Use WIDTHxHEIGHT, e.g. 1280x720.`,
    );
  }

  return {
    width: parseInteger(match[1], "viewport width", { min: 1 }),
    height: parseInteger(match[2], "viewport height", { min: 1 }),
  };
}

function sanitizeFilename(value) {
  return String(value)
    .replace(/^https?:\/\//, "")
    .replace(/[^a-z0-9._-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

function defaultScreenshotPath(url) {
  const filename = sanitizeFilename(url) || "screenshot";
  return path.join(os.tmpdir(), `playwright-${filename}.png`);
}

function resolveOutputPath(outputPath, fallbackUrl) {
  const target = outputPath || defaultScreenshotPath(fallbackUrl);
  return path.isAbsolute(target) ? target : path.resolve(process.cwd(), target);
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function attachDiagnostics(page) {
  const consoleErrors = [];
  const networkFailures = [];
  const badResponses = [];

  page.on("console", (message) => {
    if (message.type() !== "error") {
      return;
    }

    consoleErrors.push({
      type: message.type(),
      text: message.text(),
      location: message.location(),
    });
  });

  page.on("requestfailed", (request) => {
    networkFailures.push({
      url: request.url(),
      method: request.method(),
      failure: request.failure()?.errorText || "unknown",
    });
  });

  page.on("response", (response) => {
    if (response.status() < 400) {
      return;
    }

    badResponses.push({
      url: response.url(),
      status: response.status(),
      statusText: response.statusText(),
    });
  });

  return { consoleErrors, networkFailures, badResponses };
}

async function firstVisibleText(page, selector) {
  if (!selector) {
    return "";
  }

  const locator = page.locator(selector).filter({ hasText: /\S/ }).first();

  try {
    const text = await locator.textContent({ timeout: 1500 });
    return text?.trim() || "";
  } catch (_error) {
    return "";
  }
}

async function extractTitle(page, titleSelector) {
  const selectorTitle = await firstVisibleText(
    page,
    titleSelector === undefined ? DEFAULT_TITLE_SELECTOR : titleSelector,
  );

  if (selectorTitle) {
    return selectorTitle;
  }

  return (await page.title()).trim();
}

function normalizeLaunchOptions(options) {
  const browserName = options.browser || "chromium";
  const headless = options.headed ? false : options.headless !== false;

  return {
    browserName,
    headless,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  };
}

async function captureUrl(options) {
  if (!options.url) {
    throw new Error("--url is required");
  }

  const quiet = Boolean(options.quiet);
  const playwright = runtime.loadPlaywright({ quiet });
  const helpers = require("./helpers");
  const launch = normalizeLaunchOptions(options);
  const browserType = playwright[launch.browserName];

  if (!browserType) {
    throw new Error(`Invalid browser '${launch.browserName}'`);
  }

  const timeout = parseInteger(options.timeout, "--timeout", {
    defaultValue: 30000,
    min: 0,
  });
  const animationFrames = parseInteger(
    options.animationFrames,
    "--animation-frames",
    { defaultValue: 2, min: 0 },
  );
  const viewport = parseViewport(options.viewport);
  const screenshotPath = resolveOutputPath(options.out, options.url);
  ensureParentDir(screenshotPath);

  const browser = await browserType.launch({
    headless: launch.headless,
    args: launch.args,
  });

  try {
    const context = await browser.newContext(
      helpers.getContextOptionsWithHeaders({ viewport }),
    );
    const page = await context.newPage();
    page.setDefaultTimeout(timeout);
    const diagnostics = attachDiagnostics(page);

    await page.goto(options.url, {
      waitUntil: options.gotoWaitUntil || "domcontentloaded",
      timeout,
    });

    await helpers.waitForStablePage(page, {
      selector: options.selector,
      waitUntil: options.waitUntil || "domcontentloaded",
      timeout,
      animationFrames,
      stableBoundingBox: options.stableBoundingBox || false,
    });

    const title = await extractTitle(page, options.titleSelector);

    await page.screenshot({
      path: screenshotPath,
      fullPage: options.fullPage !== false,
    });

    return {
      url: options.url,
      title,
      screenshotPath,
      selector: options.selector || null,
      viewport,
      fullPage: options.fullPage !== false,
      browser: launch.browserName,
      headless: launch.headless,
      consoleErrors: diagnostics.consoleErrors,
      networkFailures: diagnostics.networkFailures,
      badResponses: diagnostics.badResponses,
    };
  } finally {
    await browser.close();
  }
}

function urlForIndex(template, index) {
  if (!template.includes("{n}")) {
    throw new Error("--url-template must include {n}");
  }
  return template.replaceAll("{n}", String(index));
}

async function captureSequence(options) {
  if (!options.urlTemplate) {
    throw new Error("--url-template is required");
  }

  const from = parseInteger(options.from, "--from");
  const to = parseInteger(options.to, "--to");
  const step = parseInteger(options.step, "--step", {
    defaultValue: from <= to ? 1 : -1,
  });

  if (step === 0) {
    throw new Error("--step must not be 0");
  }

  if ((from < to && step < 0) || (from > to && step > 0)) {
    throw new Error("--step direction must move from --from toward --to");
  }

  const outDir = path.resolve(
    options.outDir || path.join(os.tmpdir(), "playwright-screenshots"),
  );
  fs.mkdirSync(outDir, { recursive: true });

  const padWidth = Math.max(
    String(Math.abs(from)).length,
    String(Math.abs(to)).length,
    2,
  );
  const prefix = options.prefix || "screenshot-";
  const manifestPath = options.manifest
    ? path.resolve(options.manifest)
    : path.join(outDir, "manifest.json");

  const results = [];
  const indices = [];

  if (step > 0) {
    for (let index = from; index <= to; index += step) indices.push(index);
  } else {
    for (let index = from; index >= to; index += step) indices.push(index);
  }

  if (indices.length === 0) {
    throw new Error("screenshot sequence is empty");
  }

  for (const index of indices) {
    const url = urlForIndex(options.urlTemplate, index);
    const screenshotPath = path.join(
      outDir,
      `${prefix}${String(index).padStart(padWidth, "0")}.png`,
    );

    try {
      const result = await captureUrl({
        ...options,
        url,
        out: screenshotPath,
      });
      results.push({ index, ...result });
    } catch (error) {
      const failed = {
        index,
        url,
        screenshotPath,
        error: error.message,
      };
      results.push(failed);

      if (!options.continueOnError) {
        const partialManifest = {
          urlTemplate: options.urlTemplate,
          from,
          to,
          step,
          outDir,
          results,
        };
        ensureParentDir(manifestPath);
        fs.writeFileSync(
          manifestPath,
          JSON.stringify(partialManifest, null, 2),
        );
        throw error;
      }
    }
  }

  const manifest = {
    urlTemplate: options.urlTemplate,
    from,
    to,
    step,
    outDir,
    results,
  };

  ensureParentDir(manifestPath);
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  return { manifestPath, ...manifest };
}

function writeManifest(manifestPath, data) {
  if (!manifestPath) {
    return;
  }

  const resolved = path.resolve(manifestPath);
  ensureParentDir(resolved);
  fs.writeFileSync(resolved, JSON.stringify(data, null, 2));
}

module.exports = {
  captureSequence,
  captureUrl,
  extractTitle,
  parseInteger,
  parseViewport,
  writeManifest,
};
