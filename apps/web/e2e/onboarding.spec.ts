/**
 * Real registration flow driven through the browser, not seeded via the
 * `tenant` fixture (which registers via the API directly and primes
 * localStorage) — this is the one test that actually exercises the
 * register form and the onboarding page it now redirects to (previously
 * straight to an empty /dashboard). Onboarding used to accept a step
 * submission and return a fake "completed" status with nothing persisted;
 * this proves the CAGE code and NAICS code typed into the form actually
 * land on the tenant record.
 */
import { expect, test } from "@playwright/test";

// /auth/register is Redis-rate-limited per IP (5/5min, see
// core/rate_limit.py) — unlike fixtures.ts's registerTenant() (which sets
// a random X-Forwarded-For on its raw fetch calls), a browser-driven
// registration through the real form shares one source IP across every
// test in this file (and every other E2E file run in the same session)
// unless spoofed the same way here.
function fakeClientIp(): string {
  const octet = () => Math.floor(Math.random() * 255);
  return `10.${octet()}.${octet()}.${octet()}`;
}

test("register redirects to onboarding, and the company-profile form actually persists", async ({
  page,
}) => {
  await page.setExtraHTTPHeaders({ "X-Forwarded-For": fakeClientIp() });

  const suffix = Math.random().toString(36).slice(2, 10);
  const email = `e2e-onboard-${suffix}@example.com`;

  await page.goto("/auth/register");
  await page.getByPlaceholder("Jordan Rivera").fill("E2E Onboard Test");
  await page.getByPlaceholder("Acme Government Solutions").fill(`E2E Onboard Co ${suffix}`);
  await page.getByPlaceholder("you@company.com").fill(email);
  await page.getByPlaceholder("Min 12 characters").fill("E2eOnboardTest123!");
  await page.getByRole("button", { name: "Create free account" }).click();

  await page.waitForURL("**/onboarding", { timeout: 15_000 });
  await expect(page.getByText("Tell us about your company")).toBeVisible();

  await page.getByPlaceholder("1A2B3").fill("9X8Y7");
  await page.getByPlaceholder("541511, 541611").fill("541511");
  await page.getByRole("button", { name: "Continue to Dashboard" }).click();

  await page.waitForURL("**/dashboard", { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Executive Dashboard" })).toBeVisible();

  const apiUrl = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
  const profile = await page.evaluate(async (url) => {
    const token = localStorage.getItem("cios_access_token");
    const res = await fetch(`${url}/tenants/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.json();
  }, apiUrl);
  expect(profile.cage_code).toBe("9X8Y7");
  expect(profile.naics_codes).toContain("541511");
});

test("Skip for now leaves onboarding incomplete but still reaches the dashboard", async ({
  page,
}) => {
  await page.setExtraHTTPHeaders({ "X-Forwarded-For": fakeClientIp() });

  const suffix = Math.random().toString(36).slice(2, 10);
  const email = `e2e-onboard-skip-${suffix}@example.com`;

  await page.goto("/auth/register");
  await page.getByPlaceholder("Jordan Rivera").fill("E2E Skip Test");
  await page.getByPlaceholder("Acme Government Solutions").fill(`E2E Skip Co ${suffix}`);
  await page.getByPlaceholder("you@company.com").fill(email);
  await page.getByPlaceholder("Min 12 characters").fill("E2eSkipTest123!");
  await page.getByRole("button", { name: "Create free account" }).click();

  await page.waitForURL("**/onboarding", { timeout: 15_000 });
  await page.getByRole("button", { name: "Skip for now" }).click();

  await page.waitForURL("**/dashboard", { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Executive Dashboard" })).toBeVisible();
});
