/**
 * Client-side auth utilities.
 */
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user_id: string;
  tenant_id: string;
  role: string;
  plan: string;
}

export function saveTokens(tokens: AuthTokens) {
  localStorage.setItem("cios_access_token", tokens.access_token);
  localStorage.setItem("cios_refresh_token", tokens.refresh_token);
  localStorage.setItem("cios_user_id", tokens.user_id);
  localStorage.setItem("cios_tenant_id", tokens.tenant_id);
  localStorage.setItem("cios_role", tokens.role);
  localStorage.setItem("cios_plan", tokens.plan);
}

export function clearTokens() {
  ["cios_access_token", "cios_refresh_token", "cios_user_id", "cios_tenant_id", "cios_role", "cios_plan"]
    .forEach((k) => localStorage.removeItem(k));
}

export function getAccessToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("cios_access_token") : null;
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export function getUserRole(): string {
  return typeof window !== "undefined" ? (localStorage.getItem("cios_role") || "member") : "member";
}

export function getUserPlan(): string {
  return typeof window !== "undefined" ? (localStorage.getItem("cios_plan") || "trial") : "trial";
}
