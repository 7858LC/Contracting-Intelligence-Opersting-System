/**
 * Landlord/platform-admin client-side auth utilities.
 *
 * Deliberately separate storage keys from lib/auth.ts (tenant session) — a
 * landlord token and a tenant token must never collide or overwrite each
 * other in the same browser.
 */
export interface AdminAuthTokens {
  access_token: string;
  refresh_token: string;
  admin_id: string;
  email: string;
  full_name: string;
  role: string;
}

export function saveAdminTokens(tokens: AdminAuthTokens) {
  localStorage.setItem("cios_admin_access_token", tokens.access_token);
  localStorage.setItem("cios_admin_refresh_token", tokens.refresh_token);
  localStorage.setItem("cios_admin_id", tokens.admin_id);
  localStorage.setItem("cios_admin_email", tokens.email);
  localStorage.setItem("cios_admin_full_name", tokens.full_name);
  localStorage.setItem("cios_admin_role", tokens.role);
}

export function clearAdminTokens() {
  [
    "cios_admin_access_token",
    "cios_admin_refresh_token",
    "cios_admin_id",
    "cios_admin_email",
    "cios_admin_full_name",
    "cios_admin_role",
  ].forEach((k) => localStorage.removeItem(k));
}

export function getAdminAccessToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("cios_admin_access_token") : null;
}

export function isAdminAuthenticated(): boolean {
  return !!getAdminAccessToken();
}

export function getAdminRole(): string {
  return typeof window !== "undefined" ? localStorage.getItem("cios_admin_role") || "support" : "support";
}

export function getAdminFullName(): string {
  return typeof window !== "undefined" ? localStorage.getItem("cios_admin_full_name") || "" : "";
}

export function canOperate(): boolean {
  return getAdminRole() === "admin";
}
