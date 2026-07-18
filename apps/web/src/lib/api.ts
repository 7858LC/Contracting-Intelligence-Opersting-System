/**
 * CIOS API client — typed, tenant-aware, with retry logic.
 */
import axios, { AxiosInstance, AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class CIOSApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${BASE_URL}/api/v1`,
      headers: { "Content-Type": "application/json" },
      timeout: 30_000,
    });

    // Inject auth token
    this.client.interceptors.request.use((config) => {
      if (typeof window !== "undefined") {
        const token = localStorage.getItem("cios_access_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    });

    // Auto-refresh on 401
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401 && typeof window !== "undefined") {
          const refreshToken = localStorage.getItem("cios_refresh_token");
          if (refreshToken) {
            try {
              const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
                refresh_token: refreshToken,
              });
              localStorage.setItem("cios_access_token", data.access_token);
              localStorage.setItem("cios_refresh_token", data.refresh_token);
              if (error.config) {
                error.config.headers.Authorization = `Bearer ${data.access_token}`;
                return this.client.request(error.config);
              }
            } catch {
              localStorage.removeItem("cios_access_token");
              localStorage.removeItem("cios_refresh_token");
              window.location.href = "/auth/login";
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(email: string, password: string) {
    const { data } = await this.client.post("/auth/login", { email, password });
    return data;
  }

  async register(payload: { email: string; password: string; full_name: string; company_name: string }) {
    const { data } = await this.client.post("/auth/register", payload);
    return data;
  }

  async getMe() {
    const { data } = await this.client.get("/auth/me");
    return data;
  }

  // Opportunities (Module 1)
  async listOpportunities(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/opportunities", { params });
    return data;
  }

  async createOpportunity(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/opportunities", payload);
    return data;
  }

  async getOpportunity(id: string) {
    const { data } = await this.client.get(`/opportunities/${id}`);
    return data;
  }

  async analyzeOpportunity(id: string) {
    const { data } = await this.client.post(`/opportunities/${id}/analyze`);
    return data;
  }

  // Bid Decisions (Module 2)
  async listBidDecisions() {
    const { data } = await this.client.get("/bid-decisions");
    return data;
  }

  async createBidDecision(payload: { opportunity_id: string; scoring_weights?: Record<string, number> }) {
    const { data } = await this.client.post("/bid-decisions", payload);
    return data;
  }

  async recordHumanDecision(id: string, decision: string, rationale: string) {
    const { data } = await this.client.patch(`/bid-decisions/${id}/human-decision`, {
      human_decision: decision,
      human_rationale: rationale,
    });
    return data;
  }

  // Award Simulations (Module 13 — flagship)
  async listSimulations() {
    const { data } = await this.client.get("/award-simulations");
    return data;
  }

  async createSimulation(payload: {
    opportunity_id: string;
    name: string;
    evaluation_methodology?: string;
    evaluation_factors?: unknown[];
    proposal_content?: Record<string, string>;
  }) {
    const { data } = await this.client.post("/award-simulations", payload);
    return data;
  }

  async getSimulation(id: string) {
    const { data } = await this.client.get(`/award-simulations/${id}`);
    return data;
  }

  async getSimulationReport(id: string) {
    const { data } = await this.client.get(`/award-simulations/${id}/report`);
    return data;
  }

  // Knowledge Vault
  async listDocuments(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/knowledge-vault", { params });
    return data;
  }

  async uploadDocument(file: File, documentType: string, tags?: string) {
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", documentType);
    if (tags) form.append("tags", tags);
    const { data } = await this.client.post("/knowledge-vault/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  }

  async searchKnowledgeVault(query: string, topK = 10) {
    const { data } = await this.client.post("/knowledge-vault/search", { query, top_k: topK });
    return data;
  }

  // Capabilities (Module 5 & 15)
  async listCapabilities() {
    const { data } = await this.client.get("/capabilities");
    return data;
  }

  async listCapabilityGaps() {
    const { data } = await this.client.get("/capabilities/gaps");
    return data;
  }

  // Past Performance (Module 6)
  async listPastPerformance() {
    const { data } = await this.client.get("/past-performance");
    return data;
  }

  // Teaming (Module 7)
  async listTeamingPartners() {
    const { data } = await this.client.get("/teaming/partners");
    return data;
  }

  async getTeamingRecommendations(opportunityId: string) {
    const { data } = await this.client.post("/teaming/recommend", { opportunity_id: opportunityId });
    return data;
  }

  // Competitors (Module 8)
  async listCompetitors() {
    const { data } = await this.client.get("/competitors");
    return data;
  }

  // Tenant
  async getTenantProfile() {
    const { data } = await this.client.get("/tenants/profile");
    return data;
  }

  async updateTenantProfile(payload: Record<string, unknown>) {
    const { data } = await this.client.patch("/tenants/profile", payload);
    return data;
  }

  // Subscriptions
  async getSubscription() {
    const { data } = await this.client.get("/subscriptions/current");
    return data;
  }
}

export const api = new CIOSApiClient();
export default api;
