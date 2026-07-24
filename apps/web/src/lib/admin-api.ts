/**
 * Landlord/platform-admin API client — separate axios instance and token
 * refresh cycle from lib/api.ts (tenant client). Never shares an interceptor
 * or storage key with the tenant client; see lib/admin-auth.ts.
 */
import axios, { AxiosInstance, AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class CIOSAdminApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${BASE_URL}/api/v1/admin`,
      headers: { "Content-Type": "application/json" },
      timeout: 30_000,
    });

    this.client.interceptors.request.use((config) => {
      if (typeof window !== "undefined") {
        const token = localStorage.getItem("cios_admin_access_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401 && typeof window !== "undefined") {
          localStorage.removeItem("cios_admin_access_token");
          localStorage.removeItem("cios_admin_refresh_token");
          window.location.href = "/admin/login";
        }
        return Promise.reject(error);
      }
    );
  }

  async login(email: string, password: string) {
    const { data } = await this.client.post("/auth/login", { email, password });
    return data;
  }

  async me() {
    const { data } = await this.client.get("/auth/me");
    return data;
  }

  async getStats() {
    const { data } = await this.client.get("/stats");
    return data;
  }

  async listTenants(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/tenants", { params });
    return data;
  }

  async getTenant(id: string) {
    const { data } = await this.client.get(`/tenants/${id}`);
    return data;
  }

  async suspendTenant(id: string) {
    const { data } = await this.client.post(`/tenants/${id}/suspend`);
    return data;
  }

  async activateTenant(id: string) {
    const { data } = await this.client.post(`/tenants/${id}/activate`);
    return data;
  }

  async getTenantAuditLog(id: string, params?: Record<string, unknown>) {
    const { data } = await this.client.get(`/tenants/${id}/audit-log`, { params });
    return data;
  }
}

export const adminApi = new CIOSAdminApiClient();
export default adminApi;
