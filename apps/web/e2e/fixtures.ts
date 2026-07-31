/**
 * Shared E2E fixture — the frontend analog of tests/integration/conftest.py's
 * `client` fixture. Auths via the real /auth/register endpoint (never a
 * mocked backend) and primes the browser's localStorage with the resulting
 * tokens before any app code runs, so tests start already logged in instead
 * of re-driving the login form on every run.
 */
import { test as base, expect } from "@playwright/test";

const API_URL = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

export interface TenantSession {
  accessToken: string;
  refreshToken: string;
  tenantId: string;
  apiUrl: string;
}

function fakeClientIp(): string {
  // Mirrors apps/api/tests/integration/test_module_smoke.py's _fake_client_ip —
  // /auth/register is Redis-rate-limited per IP, so parallel/repeated test
  // runs need a distinct X-Forwarded-For per registration.
  const octet = () => Math.floor(Math.random() * 255);
  return `10.${octet()}.${octet()}.${octet()}`;
}

async function registerTenant(): Promise<TenantSession> {
  const suffix = Math.random().toString(36).slice(2, 10);
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Forwarded-For": fakeClientIp() },
    body: JSON.stringify({
      email: `e2e-${suffix}@example.com`,
      password: "E2eSmokeTestPassword!23",
      full_name: "E2E Smoke Test",
      company_name: `E2E Smoke Co ${suffix}`,
    }),
  });
  if (!res.ok) {
    throw new Error(`Tenant registration failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    tenantId: data.tenant_id,
    apiUrl: API_URL,
  };
}

export async function createOpportunity(
  session: TenantSession,
  overrides: { title?: string } = {}
): Promise<{ id: string; title: string }> {
  const res = await fetch(`${session.apiUrl}/opportunities`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({
      title: overrides.title ?? `E2E Smoke Opportunity ${Date.now()}`,
      agency: "Department of Defense",
      naics_codes: ["541512"],
    }),
  });
  if (!res.ok) {
    throw new Error(`Opportunity creation failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

export const test = base.extend<{ tenant: TenantSession }>({
  tenant: async ({ page }, use) => {
    const session = await registerTenant();
    await page.addInitScript(
      ({ access, refresh }) => {
        localStorage.setItem("cios_access_token", access);
        localStorage.setItem("cios_refresh_token", refresh);
      },
      { access: session.accessToken, refresh: session.refreshToken }
    );
    await use(session);
  },
});

export { expect };
