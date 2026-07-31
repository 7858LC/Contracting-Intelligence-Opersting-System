/**
 * Damascus Protocol tier-2 smoke coverage for the frontend: one real record
 * created via the real API, then a real browser asserting it actually
 * renders — not an empty/zero state. This is the exact bug class found live
 * in production: a page that compiles and type-checks cleanly while quietly
 * showing nothing for data that genuinely exists, because the frontend
 * misread the backend's real response shape.
 *
 * Deliberately smoke-level: one assertion per screen, not deep interaction
 * testing. Each test seeds its own tenant/data via the `tenant` fixture, so
 * they don't depend on run order or shared state.
 */
import { createOpportunity, expect, test } from "./fixtures";

test("Executive Dashboard renders a newly created opportunity instead of an empty state", async ({
  page,
  tenant,
}) => {
  const opp = await createOpportunity(tenant, { title: `E2E Smoke — Dashboard ${Date.now()}` });
  await page.goto("/dashboard");
  await expect(page.getByText(opp.title)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("No opportunities yet.")).not.toBeVisible();
});

test("Opportunities pipeline board places a new opportunity in a visible column, not silently dropped", async ({
  page,
  tenant,
}) => {
  const opp = await createOpportunity(tenant, { title: `E2E Smoke — Pipeline ${Date.now()}` });
  await page.goto("/dashboard/opportunities");
  await expect(page.getByText(opp.title)).toBeVisible({ timeout: 10_000 });
});

test("Award Simulator's New Simulation form lists a newly created opportunity", async ({ page, tenant }) => {
  const opp = await createOpportunity(tenant, { title: `E2E Smoke — Simulator ${Date.now()}` });
  await page.goto("/dashboard/award-simulator");
  await page.getByRole("button", { name: "New Simulation" }).click();

  // The Opportunity <select> is the first of two selects on the Setup step
  // (Evaluation Methodology is the second) — coupled to NewSimulationForm's
  // current field order in award-simulator-view.tsx.
  const opportunitySelect = page.locator("select").first();
  await expect(opportunitySelect.locator("option", { hasText: opp.title })).toHaveCount(1, {
    timeout: 10_000,
  });
});
