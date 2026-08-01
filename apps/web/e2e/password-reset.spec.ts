/**
 * There was no password-reset flow anywhere in the product before this — no
 * endpoint, no frontend page. A user who forgot/mistyped their password had
 * no self-serve way back into their account. This drives the real flow
 * through a real browser against a real API + Postgres: request a reset,
 * pull the issued token straight from the database (the API deliberately
 * never returns it — see fixtures.ts's latestPasswordResetToken), submit a
 * new password, then actually log in with it through the real login form.
 */
import { expect, latestPasswordResetToken, registerRawTenant, test } from "./fixtures";

test("forgot-password to reset-password round trip lets the user log in with a new password", async ({
  page,
}) => {
  const { email, password: oldPassword } = await registerRawTenant();
  const newPassword = "BrandNewE2ePassword!45";

  await page.goto("/auth/forgot-password");
  await page.getByPlaceholder("you@company.com").fill(email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText("Check your email")).toBeVisible({ timeout: 10_000 });

  const token = latestPasswordResetToken(email);
  expect(token).toBeTruthy();

  await page.goto(`/auth/reset-password?token=${token}`);
  await page.getByPlaceholder("Min 12 characters").fill(newPassword);
  await page.getByRole("button", { name: "Update password" }).click();

  // Redirects to /auth/login on success.
  await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });

  // Old password no longer works.
  await page.getByPlaceholder("you@company.com").fill(email);
  await page.getByPlaceholder("••••••••").fill(oldPassword);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid credentials")).toBeVisible({ timeout: 10_000 });

  // New password does, and actually lands on the dashboard.
  await page.getByPlaceholder("••••••••").fill(newPassword);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
});
