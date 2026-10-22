import { expect, test, type Page } from "@playwright/test";

// Produces the UI screenshots embedded in docs/. Each shot is of a real,
// running build driven through its real flows — nothing is mocked or staged.
const OUT = "../docs/assets/screenshots";
const email = () => `shot-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
const PASSWORD = "shot-password-123";

async function register(page: Page, address: string) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(address);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

test("capture the main screens", async ({ page }) => {
  // 1. Sign-in page (signed out).
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.screenshot({ path: `${OUT}/01-sign-in.png`, fullPage: true });

  // 2. Task composer after signing in.
  await register(page, email());
  await expect(page.getByLabel("What should the agents work on?")).toBeVisible();
  await page.screenshot({ path: `${OUT}/02-composer.png`, fullPage: true });

  // 3. Live run trace, then the finished result with findings.
  await page.getByLabel("What should the agents work on?").fill(
    "Compare rate-monotonic and EDF scheduling and recommend one",
  );
  await page.getByRole("button", { name: "Run task" }).click();
  await page.waitForURL(/\/runs\/[0-9a-f-]+$/);
  await page.locator("main ol li").first().waitFor();
  await page.screenshot({ path: `${OUT}/03-live-trace.png`, fullPage: true });

  await expect(
    page.locator("main").getByText("Passed", { exact: true }).first(),
  ).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Findings" })).toBeVisible();
  await page.screenshot({ path: `${OUT}/04-result.png`, fullPage: true });

  // 4. Usage / metrics page.
  await page.goto("/stats");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: `${OUT}/05-metrics.png`, fullPage: true });
});
