import { expect, test, type Page } from "@playwright/test";

// Unique email per run so tests are independent of existing data.
const email = () => `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
const PASSWORD = "e2e-password-123";

async function register(page: Page, address: string) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(address);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

async function startRun(page: Page, task: string) {
  const previous = page.url();
  await page.getByLabel("What should the agents work on?").fill(task);
  await page.getByRole("button", { name: "Run task" }).click();
  await page.waitForURL((url) => url.href !== previous && /\/runs\/[0-9a-f-]+$/.test(url.href));
}

test("register, run a task, and see the live trace and findings", async ({ page }) => {
  await register(page, email());
  await startRun(page, "Compare rate-monotonic and EDF scheduling and recommend one");

  // The step trace fills in as agents finish.
  await expect(page.locator("main ol li").first()).toBeVisible();
  await expect(
    page.locator("main").getByText("Passed", { exact: true }).first(),
  ).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("heading", { name: "Findings" })).toBeVisible();

  // The finished run appears in history and the Markdown export works.
  await expect(page.locator("aside").getByText("Passed", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download as Markdown" })).toBeVisible();
});

test("cancel a running task keeps the finished steps", async ({ page }) => {
  await register(page, email());
  await startRun(page, "Survey space-debris detection methods and their limitations");
  await page.locator("main ol li").first().waitFor();
  await page.getByRole("button", { name: "Cancel run" }).click();
  await expect(
    page.locator("main").getByText("Cancelled", { exact: true }).first(),
  ).toBeVisible({ timeout: 45_000 });
});

test("a second user cannot see the first user's run", async ({ browser }) => {
  const first = await browser.newContext();
  const firstPage = await first.newPage();
  await register(firstPage, email());
  await startRun(firstPage, "Explain the circuit breaker pattern with an example");
  await expect(
    firstPage.locator("main").getByText("Passed", { exact: true }).first(),
  ).toBeVisible({ timeout: 45_000 });
  const runUrl = firstPage.url();

  const second = await browser.newContext();
  const secondPage = await second.newPage();
  await register(secondPage, email());
  await secondPage.goto(runUrl);
  await expect(secondPage.getByRole("alert")).toBeVisible();

  await first.close();
  await second.close();
});

test("protected pages redirect to sign-in when signed out", async ({ page }) => {
  await page.goto("/runs/does-not-exist");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});
