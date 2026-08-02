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
// Simulator are all gated Growth+ via require_feature()
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
  // log in again for one that actually reflects "growth" (Competitive
  // Intel / Capabilities & Gaps / Teaming / Award Simulator all require
  // "growth" specifically, not "professional" — see core/features.py).
  upgradeTenantPlan(data.tenant_id, "growth");
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

// Same class of workaround as upgradeTenantPlan above — POST /auth/forgot-password
// deliberately never returns the reset token/link in its response (unlike the
// invite flow, which is already admin-authenticated), so the only way for a
// test to get a real token is to go straight at the same Postgres the API uses.
export function latestPasswordResetToken(email: string): string {
  const out = execFileSync(
    "psql",
    [
      DATABASE_URL,
      "-tA",
      "-c",
      `SELECT prt.token FROM password_reset_tokens prt ` +
        `JOIN tenant_members tm ON tm.id = prt.tenant_member_id ` +
        `WHERE tm.email = '${email}' ORDER BY prt.created_at DESC LIMIT 1`,
    ],
    { stdio: "pipe" }
  );
  return out.toString().trim();
}

// Platform admins have no self-service signup (CLAUDE.md), so a real one is
// provisioned straight against Postgres, same class of workaround as
// upgradeTenantPlan above — except a password hash can't be faked with a
// plain UPDATE, so this shells out to passlib directly for the same bcrypt
// hash cios.core.security.hash_password() produces. Deliberately not
// `from cios.core.security import hash_password` — that module imports
// cios.config at module load time, which validates DATABASE_URL/JWT_SECRET/
// etc. as required settings even though hash_password itself never touches
// them; this test step runs with none of those set (they're scoped to
// ci.yml's earlier "Start API server" step, not this one), so that import
// would fail here for reasons unrelated to what's actually being computed.
export function createPlatformAdmin(role: "admin" | "support" = "admin"): {
  email: string;
  password: string;
} {
  const suffix = Math.random().toString(36).slice(2, 10);
  const email = `e2e-admin-${suffix}@cios.ai`;
  const password = "E2eAdminTestPassword!23";
  const hash = execFileSync("python3", [
    "-c",
    "import sys; from passlib.context import CryptContext; " +
      "print(CryptContext(schemes=['bcrypt']).hash(sys.argv[1]))",
    password,
  ])
    .toString()
    .trim();
  execFileSync("psql", [
    DATABASE_URL,
    "-c",
    `INSERT INTO platform_admins (id, email, password_hash, full_name, role, is_active, created_at, updated_at) ` +
      `VALUES (gen_random_uuid(), '${email}', '${hash}', 'E2E Admin', '${role}', true, now(), now())`,
  ]);
  return { email, password };
}

export async function registerRawTenant(): Promise<{ email: string; password: string; tenantId: string }> {
  const suffix = Math.random().toString(36).slice(2, 10);
  const email = `e2e-reset-${suffix}@example.com`;
  const password = "E2eSmokeTestPassword!23";
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Forwarded-For": fakeClientIp() },
    body: JSON.stringify({
      email,
      password,
      full_name: "E2E Reset Test",
      company_name: `E2E Reset Co ${suffix}`,
    }),
  });
  if (!res.ok) {
    throw new Error(`Tenant registration failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  return { email, password, tenantId: data.tenant_id };
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

export async function createFailedSimulation(
  session: TenantSession,
  opportunityId: string,
  overrides: { name?: string } = {}
): Promise<{ id: string; name: string }> {
  const name = overrides.name ?? `E2E Smoke Simulation ${Date.now()}`;
  const res = await fetch(`${session.apiUrl}/award-simulations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({ opportunity_id: opportunityId, name }),
  });
  if (!res.ok) {
    throw new Error(`Simulation creation failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  // A real run means a real Claude call — flip status straight in Postgres
  // instead, same workaround as upgradeTenantPlan, so the delete button
  // (disabled while queued/running, see award-simulator-view.tsx) is
  // actually clickable without waiting on a live simulation pipeline.
  execFileSync("psql", [
    DATABASE_URL,
    "-c",
    `UPDATE award_simulations SET status = 'failed' WHERE id = '${data.simulation_id}'`,
  ]);
  return { id: data.simulation_id, name };
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
