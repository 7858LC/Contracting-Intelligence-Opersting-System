import { defineConfig, devices } from "@playwright/test";

// This project's browser is provisioned separately by the environment
// (PLAYWRIGHT_BROWSERS_PATH), so no `npx playwright install` step is needed
// or expected in CI or locally — see e2e/README.md.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Unset by default — CI and normal dev machines resolve Chromium the
        // standard Playwright way (see the "Install Playwright browsers" CI
        // step). Some sandboxed dev environments pre-provision a browser
        // revision that doesn't match this pinned @playwright/test version;
        // set this env var there to point at the pre-installed binary
        // instead of attempting a download.
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
          ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH }
          : undefined,
      },
    },
  ],
});
