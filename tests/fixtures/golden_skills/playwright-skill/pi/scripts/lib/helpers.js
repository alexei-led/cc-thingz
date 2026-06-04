// Reusable utility functions for Playwright automation.

const fs = require("fs");
const os = require("os");
const path = require("path");
const { loadPlaywright } = require("./runtime");

const { chromium, firefox, webkit } = loadPlaywright({ quiet: isQuiet() });

function isQuiet() {
  return process.env.PLAYWRIGHT_SKILL_QUIET === "1";
}

function log(...parts) {
  if (!isQuiet()) {
    console.error(...parts);
  }
}

function warn(...parts) {
  console.error(...parts);
}

/**
 * Parse extra HTTP headers from environment variables.
 * Supports two formats:
 * - PW_HEADER_NAME + PW_HEADER_VALUE: Single header (simple, common case)
 * - PW_EXTRA_HEADERS: JSON object for multiple headers (advanced)
 * Single header format takes precedence if both are set.
 * @returns {Object|null} Headers object or null if none configured
 */
function getExtraHeadersFromEnv() {
  const headerName = process.env.PW_HEADER_NAME;
  const headerValue = process.env.PW_HEADER_VALUE;

  if (headerName && headerValue) {
    return { [headerName]: headerValue };
  }

  const headersJson = process.env.PW_EXTRA_HEADERS;
  if (headersJson) {
    try {
      const parsed = JSON.parse(headersJson);
      if (
        typeof parsed === "object" &&
        parsed !== null &&
        !Array.isArray(parsed)
      ) {
        return parsed;
      }
      warn("PW_EXTRA_HEADERS must be a JSON object, ignoring...");
    } catch (error) {
      warn("Failed to parse PW_EXTRA_HEADERS as JSON:", error.message);
    }
  }

  return null;
}

/**
 * Merge environment-provided extra HTTP headers into browser context options.
 * @param {Object} options - Browser context options
 * @returns {Object} Options with extraHTTPHeaders merged in
 */
function getContextOptionsWithHeaders(options = {}) {
  const extraHeaders = getExtraHeadersFromEnv();

  if (!extraHeaders) {
    return options;
  }

  return {
    ...options,
    extraHTTPHeaders: {
      ...extraHeaders,
      ...(options.extraHTTPHeaders || {}),
    },
  };
}

/**
 * Launch browser with standard configuration.
 * @param {string} browserType - 'chromium', 'firefox', or 'webkit'
 * @param {Object} options - Additional launch options
 */
async function launchBrowser(browserType = "chromium", options = {}) {
  const defaultOptions = {
    headless: process.env.HEADLESS !== "false",
    slowMo: process.env.SLOW_MO ? parseInt(process.env.SLOW_MO, 10) : 0,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  };

  const browsers = { chromium, firefox, webkit };
  const browser = browsers[browserType];

  if (!browser) {
    throw new Error(`Invalid browser type: ${browserType}`);
  }

  return await browser.launch({ ...defaultOptions, ...options });
}

/**
 * Create a new page with viewport and user agent.
 * @param {Object} context - Browser context
 * @param {Object} options - Page options
 */
async function createPage(context, options = {}) {
  const page = await context.newPage();

  if (options.viewport) {
    await page.setViewportSize(options.viewport);
  }

  if (options.userAgent) {
    await page.setExtraHTTPHeaders({
      "User-Agent": options.userAgent,
    });
  }

  page.setDefaultTimeout(options.timeout || 30000);
  return page;
}

async function waitForAnimationFrames(page, frames = 2) {
  const frameCount = Math.max(0, Number(frames) || 0);
  if (frameCount === 0) {
    return;
  }

  await page.evaluate(
    (count) =>
      new Promise((resolve) => {
        let remaining = count;
        function tick() {
          remaining -= 1;
          if (remaining <= 0) {
            resolve();
            return;
          }
          window.requestAnimationFrame(tick);
        }
        window.requestAnimationFrame(tick);
      }),
    frameCount,
  );
}

async function waitForFonts(page) {
  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
  });
}

async function waitForStableBoundingBox(page, selector, options = {}) {
  const timeout = options.timeout || 10000;
  const requiredStableFrames = options.frames || 2;
  const locator = page.locator(selector).first();
  const deadline = Date.now() + timeout;
  let lastBox = null;
  let stableFrames = 0;

  while (Date.now() < deadline) {
    let box = null;
    try {
      box = await locator.boundingBox({ timeout: Math.min(1000, timeout) });
    } catch (_error) {
      // Dynamic pages can briefly detach/recreate nodes during animation.
    }

    if (!box) {
      stableFrames = 0;
      await waitForAnimationFrames(page, 1);
      continue;
    }

    const stable =
      lastBox &&
      Math.abs(lastBox.x - box.x) < 0.5 &&
      Math.abs(lastBox.y - box.y) < 0.5 &&
      Math.abs(lastBox.width - box.width) < 0.5 &&
      Math.abs(lastBox.height - box.height) < 0.5;

    stableFrames = stable ? stableFrames + 1 : 0;
    lastBox = box;

    if (stableFrames >= requiredStableFrames) {
      return;
    }

    await waitForAnimationFrames(page, 1);
  }

  throw new Error(`Element bounding box did not stabilize: ${selector}`);
}

/**
 * Wait for SPA/page readiness using load state, a rendered selector, fonts, and
 * animation frames. Prefer this before screenshots of dynamic pages.
 * @param {Object} page - Playwright page
 * @param {Object} options - Wait options
 */
async function waitForStablePage(page, options = {}) {
  const timeout = options.timeout || 30000;
  const waitUntil = options.waitUntil || "domcontentloaded";
  const selector = options.selector || options.waitForSelector;
  const selectorState = options.state || "visible";
  const animationFrames = options.animationFrames ?? 2;

  if (waitUntil) {
    try {
      await page.waitForLoadState(waitUntil, { timeout });
    } catch (_error) {
      log(
        `Page did not reach load state '${waitUntil}' before timeout; continuing...`,
      );
    }
  }

  if (selector) {
    await page.waitForSelector(selector, { state: selectorState, timeout });
  }

  if (options.fonts !== false) {
    try {
      await waitForFonts(page);
    } catch (_error) {
      log("Font readiness check failed; continuing...");
    }
  }

  await waitForAnimationFrames(page, animationFrames);

  if (selector && options.stableBoundingBox) {
    await waitForStableBoundingBox(page, selector, {
      timeout,
      frames: options.stableFrames || 2,
    });
  }
}

/**
 * Smart wait for page to be ready. Kept for compatibility; prefer
 * waitForStablePage for SPA screenshots.
 * @param {Object} page - Playwright page
 * @param {Object} options - Wait options
 */
async function waitForPageReady(page, options = {}) {
  await waitForStablePage(page, {
    waitUntil: options.waitUntil || "networkidle",
    selector: options.selector || options.waitForSelector,
    timeout: options.timeout || 30000,
    animationFrames: options.animationFrames ?? 2,
    fonts: options.fonts,
    stableBoundingBox: options.stableBoundingBox,
    stableFrames: options.stableFrames,
  });
}

/**
 * Safe click with retry logic.
 * @param {Object} page - Playwright page
 * @param {string} selector - Element selector
 * @param {Object} options - Click options
 */
async function safeClick(page, selector, options = {}) {
  const maxRetries = options.retries || 3;
  const retryDelay = options.retryDelay || 1000;

  for (let i = 0; i < maxRetries; i += 1) {
    try {
      await page.waitForSelector(selector, {
        state: "visible",
        timeout: options.timeout || 5000,
      });
      await page.click(selector, {
        force: options.force || false,
        timeout: options.timeout || 5000,
      });
      return true;
    } catch (error) {
      if (i === maxRetries - 1) {
        console.error(
          `Failed to click ${selector} after ${maxRetries} attempts`,
        );
        throw error;
      }
      log(`Retry ${i + 1}/${maxRetries} for clicking ${selector}`);
      await page.waitForTimeout(retryDelay);
    }
  }

  return false;
}

/**
 * Safe text input with clear before type.
 * @param {Object} page - Playwright page
 * @param {string} selector - Input selector
 * @param {string} text - Text to type
 * @param {Object} options - Type options
 */
async function safeType(page, selector, text, options = {}) {
  await page.waitForSelector(selector, {
    state: "visible",
    timeout: options.timeout || 10000,
  });

  if (options.clear !== false) {
    await page.fill(selector, "");
  }

  if (options.slow) {
    await page.type(selector, text, { delay: options.delay || 100 });
  } else {
    await page.fill(selector, text);
  }
}

/**
 * Extract text from multiple elements.
 * @param {Object} page - Playwright page
 * @param {string} selector - Elements selector
 */
async function extractTexts(page, selector) {
  await page.waitForSelector(selector, { timeout: 10000 });
  return await page.$$eval(selector, (elements) =>
    elements.map((el) => el.textContent?.trim()).filter(Boolean),
  );
}

function timestampedScreenshotPath(name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const parsed = path.parse(name);
  const stem = parsed.ext ? parsed.name : name;
  const filename = `${stem}-${timestamp}.png`;

  if (path.isAbsolute(name)) {
    return parsed.ext ? name : `${name}-${timestamp}.png`;
  }

  if (name.includes(path.sep) || name.includes("/")) {
    const resolved = path.resolve(process.cwd(), name);
    const resolvedParsed = path.parse(resolved);
    return resolvedParsed.ext ? resolved : `${resolved}-${timestamp}.png`;
  }

  return path.join(os.tmpdir(), `playwright-${filename}`);
}

/**
 * Take screenshot with timestamp. Simple names are saved under /tmp.
 * @param {Object} page - Playwright page
 * @param {string} name - Screenshot name or path
 * @param {Object} options - Screenshot options
 */
async function takeScreenshot(page, name, options = {}) {
  const filename = timestampedScreenshotPath(name);
  fs.mkdirSync(path.dirname(filename), { recursive: true });

  await page.screenshot({
    path: filename,
    fullPage: options.fullPage !== false,
    ...options,
  });

  log(`Screenshot saved: ${filename}`);
  return filename;
}

/**
 * Handle authentication.
 * @param {Object} page - Playwright page
 * @param {Object} credentials - Username and password
 * @param {Object} selectors - Login form selectors
 */
async function authenticate(page, credentials, selectors = {}) {
  const defaultSelectors = {
    username: 'input[name="username"], input[name="email"], #username, #email',
    password: 'input[name="password"], #password',
    submit:
      'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in")',
  };

  const finalSelectors = { ...defaultSelectors, ...selectors };

  await safeType(page, finalSelectors.username, credentials.username);
  await safeType(page, finalSelectors.password, credentials.password);
  await safeClick(page, finalSelectors.submit);

  await Promise.race([
    page.waitForNavigation({ waitUntil: "networkidle" }),
    page.waitForSelector(
      selectors.successIndicator || ".dashboard, .user-menu, .logout",
      { timeout: 10000 },
    ),
  ]).catch(() => {
    log("Login might have completed without navigation");
  });
}

/**
 * Scroll page.
 * @param {Object} page - Playwright page
 * @param {string} direction - 'down', 'up', 'top', 'bottom'
 * @param {number} distance - Pixels to scroll (for up/down)
 */
async function scrollPage(page, direction = "down", distance = 500) {
  switch (direction) {
    case "down":
      await page.evaluate((d) => window.scrollBy(0, d), distance);
      break;
    case "up":
      await page.evaluate((d) => window.scrollBy(0, -d), distance);
      break;
    case "top":
      await page.evaluate(() => window.scrollTo(0, 0));
      break;
    case "bottom":
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      break;
    default:
      throw new Error(`Invalid scroll direction: ${direction}`);
  }
  await waitForAnimationFrames(page, 2);
}

/**
 * Extract table data.
 * @param {Object} page - Playwright page
 * @param {string} tableSelector - Table selector
 */
async function extractTableData(page, tableSelector) {
  await page.waitForSelector(tableSelector);

  return await page.evaluate((selector) => {
    const table = document.querySelector(selector);
    if (!table) return null;

    const headers = Array.from(table.querySelectorAll("thead th")).map((th) =>
      th.textContent?.trim(),
    );

    const rows = Array.from(table.querySelectorAll("tbody tr")).map((tr) => {
      const cells = Array.from(tr.querySelectorAll("td"));
      if (headers.length > 0) {
        return cells.reduce((obj, cell, index) => {
          obj[headers[index] || `column_${index}`] = cell.textContent?.trim();
          return obj;
        }, {});
      }
      return cells.map((cell) => cell.textContent?.trim());
    });

    return { headers, rows };
  }, tableSelector);
}

/**
 * Wait for and dismiss cookie banners.
 * @param {Object} page - Playwright page
 * @param {number} timeout - Max time to wait
 */
async function handleCookieBanner(page, timeout = 3000) {
  const commonSelectors = [
    'button:has-text("Accept")',
    'button:has-text("Accept all")',
    'button:has-text("OK")',
    'button:has-text("Got it")',
    'button:has-text("I agree")',
    ".cookie-accept",
    "#cookie-accept",
    '[data-testid="cookie-accept"]',
  ];

  for (const selector of commonSelectors) {
    try {
      const element = await page.waitForSelector(selector, {
        timeout: timeout / commonSelectors.length,
        state: "visible",
      });
      if (element) {
        await element.click();
        log("Cookie banner dismissed");
        return true;
      }
    } catch (_error) {
      // Continue to next selector.
    }
  }

  return false;
}

/**
 * Retry a function with exponential backoff.
 * @param {Function} fn - Function to retry
 * @param {number} maxRetries - Maximum retry attempts
 * @param {number} initialDelay - Initial delay in ms
 */
async function retryWithBackoff(fn, maxRetries = 3, initialDelay = 1000) {
  let lastError;

  for (let i = 0; i < maxRetries; i += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const delay = initialDelay * 2 ** i;
      log(`Attempt ${i + 1} failed, retrying in ${delay}ms...`);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

/**
 * Create browser context with common settings.
 * @param {Object} browser - Browser instance
 * @param {Object} options - Context options
 */
async function createContext(browser, options = {}) {
  const defaultOptions = {
    viewport: { width: 1280, height: 720 },
    userAgent: options.mobile
      ? "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
      : undefined,
    permissions: options.permissions || [],
    geolocation: options.geolocation,
    locale: options.locale || "en-US",
    timezoneId: options.timezoneId || "America/New_York",
  };

  return await browser.newContext(
    getContextOptionsWithHeaders({ ...defaultOptions, ...options }),
  );
}

function requestUrl(port) {
  return `http://localhost:${port}`;
}

async function probeHttpPort(http, port) {
  return await new Promise((resolve) => {
    const req = http.request(
      {
        hostname: "localhost",
        port,
        path: "/",
        method: "HEAD",
        timeout: 500,
      },
      (res) => {
        resolve(res.statusCode < 500);
      },
    );

    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });

    req.end();
  });
}

/**
 * Detect running dev servers on common ports.
 * @param {Array<number>} customPorts - Additional ports to check
 * @returns {Promise<Array>} Array of detected server URLs
 */
async function detectDevServers(customPorts = []) {
  const http = require("http");
  const commonPorts = [
    3000, 3001, 3002, 3030, 4173, 4200, 4321, 5000, 5173, 5174, 6006, 8000,
    8080, 9000, 1234,
  ];
  const allPorts = [...new Set([...commonPorts, ...customPorts])];
  const detectedServers = [];

  log("🔍 Checking for running dev servers...");

  for (const port of allPorts) {
    try {
      if (await probeHttpPort(http, port)) {
        detectedServers.push(requestUrl(port));
        log(`  ✅ Found server on port ${port}`);
      }
    } catch (_error) {
      // Port not available, continue.
    }
  }

  if (detectedServers.length === 0) {
    log("  ❌ No dev servers detected");
  }

  return detectedServers;
}

module.exports = {
  launchBrowser,
  createPage,
  waitForPageReady,
  waitForStablePage,
  waitForAnimationFrames,
  waitForStableBoundingBox,
  safeClick,
  safeType,
  extractTexts,
  takeScreenshot,
  authenticate,
  scrollPage,
  extractTableData,
  handleCookieBanner,
  retryWithBackoff,
  createContext,
  detectDevServers,
  getExtraHeadersFromEnv,
  getContextOptionsWithHeaders,
};
