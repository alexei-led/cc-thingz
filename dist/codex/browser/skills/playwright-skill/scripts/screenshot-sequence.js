#!/usr/bin/env node

const { captureSequence } = require("./lib/screenshot");

function usage() {
  console.error(`Usage:
  node scripts/screenshot-sequence.js --url-template 'http://localhost:3030/{n}' --from 1 --to 10 --out-dir /tmp/shots

Options:
  --url-template TEMPLATE URL template containing {n}
  --from N                first index
  --to N                  last index
  --step N                step, default 1 or -1 based on range
  --out-dir DIR           output dir, default /tmp/playwright-screenshots
  --prefix TEXT           screenshot filename prefix, default screenshot-
  --manifest FILE         manifest path, default <out-dir>/manifest.json
  --selector CSS          wait for selector before screenshot
  --viewport WIDTHxHEIGHT viewport, default 1280x720
  --title-selector CSS    selector used for manifest title, default heading
  --timeout MS            timeout, default 30000
  --animation-frames N    animation frames after readiness, default 2
  --wait-until STATE      load state for readiness, default domcontentloaded
  --browser NAME          chromium, firefox, or webkit; default chromium
  --headed                use visible browser
  --headless              force headless browser
  --full-page             capture full page, default
  --viewport-only         capture viewport only
  --continue-on-error     keep going and record failed items in manifest
  --quiet, -q             suppress status logs
  --json                  print manifest JSON to stdout and imply --quiet`);
}

function parseArgs(argv) {
  const options = { fullPage: true, quiet: false, json: false };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    switch (arg) {
      case "--help":
      case "-h":
        options.help = true;
        break;
      case "--quiet":
      case "-q":
        options.quiet = true;
        break;
      case "--json":
        options.json = true;
        options.quiet = true;
        break;
      case "--headed":
        options.headed = true;
        options.headless = false;
        break;
      case "--headless":
        options.headless = true;
        options.headed = false;
        break;
      case "--full-page":
        options.fullPage = true;
        break;
      case "--viewport-only":
      case "--no-full-page":
        options.fullPage = false;
        break;
      case "--continue-on-error":
        options.continueOnError = true;
        break;
      case "--stable-bounding-box":
        options.stableBoundingBox = true;
        break;
      default: {
        if (!arg.startsWith("--")) {
          throw new Error(`Unexpected argument: ${arg}`);
        }
        const key = arg
          .slice(2)
          .replace(/-([a-z])/g, (_, char) => char.toUpperCase());
        const value = argv[i + 1];
        if (value === undefined || value.startsWith("--")) {
          throw new Error(`${arg} requires a value`);
        }
        options[key] = value;
        i += 1;
      }
    }
  }

  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));

  if (options.help) {
    usage();
    return;
  }

  if (
    !options.urlTemplate ||
    options.from === undefined ||
    options.to === undefined
  ) {
    usage();
    process.exit(1);
  }

  process.env.PLAYWRIGHT_SKILL_QUIET = options.quiet ? "1" : "0";

  const result = await captureSequence(options);

  if (options.json) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  console.log(result.manifestPath);
}

main().catch((error) => {
  console.error("❌", error.message);
  process.exit(1);
});
