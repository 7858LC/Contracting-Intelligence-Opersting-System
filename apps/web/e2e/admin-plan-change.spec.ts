/**
 * Landlord console smoke test for the new tenant plan-override control
 * (admin.py's update_tenant_plan + the tenant detail page's plan
 * selector). Regression coverage for the gap this closes: previously there
 * was no way — Stripe upgrade or admin action — that reliably landed a new
 * plan on Tenant.plan, the field every feature check actually reads.
 */
import { createPlatformAdmin, expect, registerRawTenant, test } from "./fixtures";

test("Landlord console changes a tenant's plan and it persists across a reload", async ({ page }) => {
  const { tenantId } = await registerRawTenant();
  const { email, password } = createPlatformAdmin("admin");

  await page.goto("/admin/login");
  await page.getByPlaceholder("ops@cios.ai").fill(email);
  await page.getByPlaceholder("••••••••").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL("/admin", { timeout: 10_000 });

  await page.goto(`/admin/tenants/${tenantId}`);
  await expect(page.getByText("· trial plan")).toBeVisible({ timeout: 10_000 });

  await page.locator("select").selectOption("growth");
  await page.getByRole("button", { name: "Change Plan" }).click();

  await expect(page.getByText("Plan changed to growth")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("· growth plan")).toBeVisible();

  await page.reload();
  await expect(page.getByText("· growth plan")).toBeVisible({ timeout: 10_000 });
});
