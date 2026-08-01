/**
 * Shared E2E fixture — the frontend analog of tests/integration/conftest.py's
 * `client` fixture. Auths via the real /auth/register endpoint (never a
 * mocked backend) and primes the browser's localStorage with the resulting
 * tokens before any app code runs, so tests start already logged in instead
 * of re-driving the login form on every run.
 */
import { execFileSync } from "node:child_process";
import { test as base, expect } from "@playwright/test";

const API_URL = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
// Matches the local dev Postgres credentials used throughout this repo
// (docker-compose.yml, apps/api's own test fixtures) — CI's e2e-test job
// overrides this to point at its service-container Postgres.
const DATABASE_URL =
  process.env.E2E_DATABASE_URL || "postgresql://cios_user:cios_pass@localhost:5432/cios_test";

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

// Competitive Intelligence, Capabilities & Gaps, Teaming, and Award
// Simulator are all gated Professional+ via require_feature()
// (apps/api/cios/api/v1/router.py) — /auth/register always issues
// plan="trial" (starter-equivalent, no access), so E2E tenants need a
// real plan bump before they can exercise those modules. There's no API
// route for this yet (it's meant to flow through Stripe checkout, not a
// self-serve endpoint), so this goes straight at the same Postgres the
// API itself uses — the same class of workaround
// tests/integration/conftest.py's upgrade_tenant_plan() uses on the
// pytest side, just via psql instead of a SQLAlchemy session since this
// fixture has no ORM access into the API's database layer.
function upgradeTenantPlan(tenantId: string, plan: string): void {
  execFileSync(
    "psql",
    [DATABASE_URL, "-c", `UPDATE tenants SET plan = '${plan}' WHERE id = '${tenantId}'`],
    { stdio: "pipe" }
  );
}

async function registerTenant(): Promise<TenantSession> {
  const suffix = Math.random().toString(36).slice(2, 10);
  const email = `e2e-${suffix}@example.com`;
  const password = "E2eSmokeTestPassword!23";
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Forwarded-For": fakeClientIp() },
    body: JSON.stringify({
      email,
      password,
      full_name: "E2E Smoke Test",
      company_name: `E2E Smoke Co ${suffix}`,
    }),
  });
  if (!res.ok) {
    throw new Error(`Tenant registration failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();

  // Plan is baked into the JWT at issue time (see auth.py), so the token
  // above still carries plan="trial" even after the DB row changes below —
  // log in again for one that actually reflects "professional".
  upgradeTenantPlan(data.tenant_id, "professional");
  const loginRes = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Forwarded-For": fakeClientIp() },
    body: JSON.stringify({ email, password }),
  });
  if (!loginRes.ok) {
    throw new Error(`Post-upgrade login failed: ${loginRes.status} ${await loginRes.text()}`);
  }
  const loginData = await loginRes.json();

  return {
    accessToken: loginData.access_token,
    refreshToken: loginData.refresh_token,
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

export async function createCompetitor(
  session: TenantSession,
  overrides: { company_name?: string } = {}
): Promise<{ id: string; company_name: string }> {
  const res = await fetch(`${session.apiUrl}/competitors`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({
      company_name: overrides.company_name ?? `E2E Smoke Competitor ${Date.now()}`,
      threat_level: "high",
    }),
  });
  if (!res.ok) {
    throw new Error(`Competitor creation failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

export async function createCapability(
  session: TenantSession,
  overrides: { name?: string } = {}
): Promise<{ id: string; name: string }> {
  const res = await fetch(`${session.apiUrl}/capabilities`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({
      name: overrides.name ?? `E2E Smoke Capability ${Date.now()}`,
      category: "technical",
    }),
  });
  if (!res.ok) {
    throw new Error(`Capability creation failed: ${res.status} ${await res.text()}`);
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
