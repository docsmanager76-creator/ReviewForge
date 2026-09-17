import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// In sandboxed/CI environments a pre-installed Chromium headless shell may already be
// available (e.g. Playwright's cache) — reuse it instead of letting Remotion download its
// own, which can be blocked by network egress policies. Local Windows dev machines without
// this env var fall back to Remotion's normal managed-browser download.
if (process.env.REVIEWFORGE_CHROME_HEADLESS_SHELL_PATH) {
  Config.setBrowserExecutable(process.env.REVIEWFORGE_CHROME_HEADLESS_SHELL_PATH);
}
