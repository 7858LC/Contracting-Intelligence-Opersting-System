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
import {
  createCapability,
  createCompetitor,
  createFailedSimulation,
  createOpportunity,
  expect,
  test,
} from "./fixtures";

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

test("Award Simulator deletes a failed simulation via its delete button", async ({ page, tenant }) => {
  const opp = await createOpportunity(tenant, { title: `E2E Smoke — Delete Sim ${Date.now()}` });
  const sim = await createFailedSimulation(tenant, opp.id);

  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/dashboard/award-simulator");
  await expect(page.getByText(sim.name)).toBeVisible({ timeout: 10_000 });

  await page.getByTitle("Delete simulation").click();

  await expect(page.getByText("Simulation deleted")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(sim.name)).not.toBeVisible();
});

test("Competitive Intelligence page renders a newly created competitor instead of an empty state", async ({
  page,
  tenant,
}) => {
  const competitor = await createCompetitor(tenant, {
    company_name: `E2E Smoke Competitor ${Date.now()}`,
  });
  await page.goto("/dashboard/competitors");
  await expect(page.getByText(competitor.company_name)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("No competitors tracked yet")).not.toBeVisible();
});

test("Capabilities page renders a newly created capability instead of an empty state", async ({
  page,
  tenant,
}) => {
  const capability = await createCapability(tenant, {
    name: `E2E Smoke Capability ${Date.now()}`,
  });
  await page.goto("/dashboard/capabilities");
  await expect(page.getByText(capability.name)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("No capabilities registered")).not.toBeVisible();
});

test("Knowledge Vault upload stays disabled until the CUI attestation is checked, then lists the new document", async ({
  page,
  tenant,
}) => {
  const fileTitle = `e2e-smoke-kv-${Date.now()}`;
  await page.goto("/dashboard/knowledge-vault");

  await page.locator('input[type="file"]').setInputFiles({
    name: `${fileTitle}.txt`,
    mimeType: "text/plain",
    buffer: Buffer.from("Ordinary past performance narrative for E2E smoke test."),
  });

  const submitButton = page.getByRole("button", { name: "Upload & Vectorize" });
  // Backend requires the attestation field (cios/api/v1/endpoints/knowledge_vault.py
  // rejects its absence with a 422) — this proves the UI actually gates on it
  // instead of just relying on the backend to reject a bad request.
  await expect(submitButton).toBeDisabled();

  await page.getByRole("checkbox").check();
  await expect(submitButton).toBeEnabled();
  await submitButton.click();

  await expect(page.getByText("Document uploaded")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(fileTitle)).toBeVisible({ timeout: 10_000 });
});

test("Capabilities page's Opportunity Gap Analysis picker lists a newly created opportunity", async ({
  page,
  tenant,
}) => {
  const opp = await createOpportunity(tenant, { title: `E2E Smoke — Gap Analysis ${Date.now()}` });
  await page.goto("/dashboard/capabilities");
  const opportunitySelect = page.getByRole("combobox").first();
  await expect(opportunitySelect.locator("option", { hasText: opp.title })).toHaveCount(1, {
    timeout: 10_000,
  });
});
