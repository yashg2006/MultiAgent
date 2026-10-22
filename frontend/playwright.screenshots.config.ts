import { defineConfig, devices } from "@playwright/test";

// Captures real UI screenshots into docs/assets/screenshots/ for the report.
// Run against a live stack via the Evidence workflow, not in the E2E gate.
const baseURL = process.env.BASE_URL ?? "http://localhost:8080";

export default defineConfig({
  testDir: "./screenshots",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  use: {
    baseURL,
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 2,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
