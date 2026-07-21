/**
 * CIOS API client — typed, tenant-aware, with auto-refresh on 401.
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

    this.client.interceptors.request.use((config) => {
      if (typeof window !== "undefined") {
        const token = localStorage.getItem("cios_access_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

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

  // ── Auth ────────────────────────────────────────────────────────────────────

  async login(email: string, password: string) {
    const { data } = await this.client.post("/auth/login", { email, password });
    return data;
  }

  async register(payload: {
    email: string;
    password: string;
    full_name: string;
    company_name: string;
    naics_codes?: string[];
  }) {
    const { data } = await this.client.post("/auth/register", payload);
    return data;
  }

  async getMe() {
    const { data } = await this.client.get("/auth/me");
    return data;
  }

  // ── Opportunities (Module 1) ─────────────────────────────────────────────

  async getOpportunities(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/opportunities", { params });
    return data.opportunities ?? data;
  }

  async createOpportunity(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/opportunities", payload);
    return data;
  }

  async getOpportunity(id: string) {
    const { data } = await this.client.get(`/opportunities/${id}`);
    return data;
  }

  async updateOpportunity(id: string, payload: Record<string, unknown>) {
    const { data } = await this.client.patch(`/opportunities/${id}`, payload);
    return data;
  }

  async analyzeOpportunity(id: string) {
    const { data } = await this.client.post(`/opportunities/${id}/analyze`);
    return data;
  }

  async watchOpportunity(id: string) {
    const { data } = await this.client.post(`/opportunities/${id}/watch`);
    return data;
  }

  // ── Bid Decisions (Module 2) ─────────────────────────────────────────────

  async getBidDecisions(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/bid-decisions", { params });
    return data.bid_decisions ?? data.decisions ?? data;
  }

  async createBidDecision(payload: { opportunity_id: string; go_no_go_threshold?: number; scoring_weights?: Record<string, number> }) {
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

  // ── Award Simulations (Module 13 — flagship) ────────────────────────────

  async getSimulations(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/award-simulations", { params });
    return data.simulations ?? data;
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

  // ── Knowledge Vault ──────────────────────────────────────────────────────

  async getKnowledgeDocuments(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/knowledge-vault", { params });
    return data.items ?? data.documents ?? data;
  }

  async uploadKnowledgeDocument(formData: FormData) {
    const { data } = await this.client.post("/knowledge-vault/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  }

  async searchKnowledge(query: string, topK = 10) {
    const { data } = await this.client.post("/knowledge-vault/search", { query, top_k: topK });
    return data.results ?? data;
  }

  async deleteKnowledgeDocument(id: string) {
    await this.client.delete(`/knowledge-vault/${id}`);
    return { deleted: true };
  }

  // ── Capabilities (Module 5 & 15) ─────────────────────────────────────────

  async getCapabilities(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/capabilities", { params });
    return data.capabilities ?? data;
  }

  async createCapability(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/capabilities", payload);
    return data;
  }

  async deleteCapability(id: string) {
    const { data } = await this.client.delete(`/capabilities/${id}`);
    return data;
  }

  async getCapabilityGaps() {
    const { data } = await this.client.get("/capabilities/gaps");
    return data.gaps ?? data;
  }

  // ── Past Performance (Module 6) ──────────────────────────────────────────

  async getPastPerformances(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/past-performance", { params });
    return data.past_performances ?? data;
  }

  async createPastPerformance(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/past-performance", payload);
    return data;
  }

  // ── Teaming (Module 7) ───────────────────────────────────────────────────

  async getTeamingRecommendations(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/teaming/recommendations", { params });
    return data.recommendations ?? data;
  }

  async getTeamingPartners(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/teaming/partners", { params });
    return data.partners ?? data;
  }

  async createTeamingPartner(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/teaming/partners", payload);
    return data;
  }

  async generateTeamingRecommendation(opportunityId: string) {
    const { data } = await this.client.post("/teaming/recommend", { opportunity_id: opportunityId });
    return data;
  }

  // ── Competitors (Module 8) ───────────────────────────────────────────────

  async getCompetitors(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/competitors", { params });
    return data.competitors ?? data;
  }

  async createCompetitor(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/competitors", payload);
    return data;
  }

  async addCompetitorIntel(competitorId: string, payload: Record<string, unknown>) {
    const { data } = await this.client.post(`/competitors/${competitorId}/intel`, payload);
    return data;
  }

  // ── Tenant ───────────────────────────────────────────────────────────────

  async getTenantProfile() {
    const { data } = await this.client.get("/tenants/profile");
    return data;
  }

  async updateTenantProfile(payload: Record<string, unknown>) {
    const { data } = await this.client.patch("/tenants/profile", payload);
    return data;
  }

  // ── API Keys ─────────────────────────────────────────────────────────────

  async createApiKey(name: string) {
    const { data } = await this.client.post("/tenants/api-keys", { name });
    return data;
  }

  async deleteApiKey(id: string) {
    const { data } = await this.client.delete(`/tenants/api-keys/${id}`);
    return data;
  }

  // ── Subscriptions ────────────────────────────────────────────────────────

  async getSubscription() {
    const { data } = await this.client.get("/subscriptions/current");
    return data;
  }

  async createCheckout(plan: string) {
    const { data } = await this.client.post("/subscriptions/checkout", { plan });
    return data;
  }

  async getCustomerPortal() {
    const { data } = await this.client.post("/subscriptions/portal");
    return data;
  }

  async getInvoices() {
    const { data } = await this.client.get("/subscriptions/invoices");
    return data;
  }

  // ── Dashboard ────────────────────────────────────────────────────────────

  async getDashboardStats() {
    const { data } = await this.client.get("/dashboard/stats");
    return data;
  }

  // ── Procurement Intelligence Radar™ (PIR) ───────────────────────────────

  async getRadarDashboard() {
    const { data } = await this.client.get("/radar/dashboard");
    return data;
  }

  async listCompanies(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/radar/companies", { params });
    return data;
  }

  async createCompany(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/radar/companies", payload);
    return data;
  }

  async getCompany(id: string) {
    const { data } = await this.client.get(`/radar/companies/${id}`);
    return data;
  }

  async updateCompany(id: string, payload: Record<string, unknown>) {
    const { data } = await this.client.patch(`/radar/companies/${id}`, payload);
    return data;
  }

  async deleteCompany(id: string) {
    await this.client.delete(`/radar/companies/${id}`);
  }

  async triggerCompanyScan(id: string, daysBack = 60) {
    const { data } = await this.client.post(`/radar/companies/${id}/scan`, null, {
      params: { days_back: daysBack },
    });
    return data;
  }

  async listCompanySignals(companyId: string, params?: Record<string, unknown>) {
    const { data } = await this.client.get(`/radar/companies/${companyId}/signals`, { params });
    return data;
  }

  async triggerAIAnalysis(companyId: string) {
    const { data } = await this.client.post(`/radar/companies/${companyId}/analyze`);
    return data;
  }

  async listAIAnalyses(companyId: string) {
    const { data } = await this.client.get(`/radar/companies/${companyId}/analyses`);
    return data;
  }

  async getAIAnalysis(companyId: string, analysisId: string) {
    const { data } = await this.client.get(`/radar/companies/${companyId}/analyses/${analysisId}`);
    return data;
  }

  async listWatchlists() {
    const { data } = await this.client.get("/radar/watchlists");
    return data;
  }

  async createWatchlist(payload: { name: string; description?: string; is_default?: boolean }) {
    const { data } = await this.client.post("/radar/watchlists", payload);
    return data;
  }

  async deleteWatchlist(id: string) {
    await this.client.delete(`/radar/watchlists/${id}`);
  }

  async addToWatchlist(watchlistId: string, companyId: string) {
    const { data } = await this.client.post(`/radar/watchlists/${watchlistId}/companies/${companyId}`);
    return data;
  }

  async removeFromWatchlist(watchlistId: string, companyId: string) {
    const { data } = await this.client.delete(`/radar/watchlists/${watchlistId}/companies/${companyId}`);
    return data;
  }

  async listSavedSearches() {
    const { data } = await this.client.get("/radar/saved-searches");
    return data;
  }

  async createSavedSearch(payload: { name: string; filters: Record<string, unknown>; notify_on_new?: boolean }) {
    const { data } = await this.client.post("/radar/saved-searches", payload);
    return data;
  }

  async triggerBulkScan(daysBack = 60, watchedOnly = false) {
    const { data } = await this.client.post("/radar/scans", null, {
      params: { days_back: daysBack, watched_only: watchedOnly },
    });
    return data;
  }

  async listScanJobs(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/radar/scans", { params });
    return data;
  }

  // ── Winning Profile Hypothesis™ (pre-award intelligence) ─────────────────

  async listSolicitations(params?: Record<string, unknown>) {
    const { data } = await this.client.get("/winning-profile/solicitations", { params });
    return data;
  }

  async createSolicitation(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/winning-profile/solicitations", payload);
    return data;
  }

  async getSolicitation(id: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}`);
    return data;
  }

  async deleteSolicitation(id: string) {
    await this.client.delete(`/winning-profile/solicitations/${id}`);
  }

  async addSolicitationDocument(id: string, payload: Record<string, unknown>) {
    const { data } = await this.client.post(`/winning-profile/solicitations/${id}/documents`, payload);
    return data;
  }

  async listSolicitationDocuments(id: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}/documents`);
    return data;
  }

  async getSolicitationSignals(id: string, category?: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}/signals`, {
      params: category ? { category } : undefined,
    });
    return data;
  }

  async generateWinningProfile(id: string, enrich = false) {
    const { data } = await this.client.post(
      `/winning-profile/solicitations/${id}/generate-profile`, null, { params: { enrich } });
    return data;
  }

  async getWinningProfile(id: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}/profile`);
    return data;
  }

  async listWphContractors() {
    const { data } = await this.client.get("/winning-profile/contractors");
    return data;
  }

  async createWphContractor(payload: Record<string, unknown>) {
    const { data } = await this.client.post("/winning-profile/contractors", payload);
    return data;
  }

  async deleteWphContractor(id: string) {
    await this.client.delete(`/winning-profile/contractors/${id}`);
  }

  async alignContractors(id: string, contractorIds?: string[]) {
    const { data } = await this.client.post(
      `/winning-profile/solicitations/${id}/align`, { contractor_ids: contractorIds ?? null });
    return data;
  }

  async getAlignments(id: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}/alignments`);
    return data;
  }

  async assessPursuit(id: string, targetContractorId?: string) {
    const { data } = await this.client.post(
      `/winning-profile/solicitations/${id}/assess`,
      { target_contractor_id: targetContractorId ?? null });
    return data;
  }

  async getPursuitAssessment(id: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}/assessment`);
    return data;
  }

  async runWphPipeline(id: string, enrich = false) {
    const { data } = await this.client.post(
      `/winning-profile/solicitations/${id}/run`, null, { params: { enrich } });
    return data;
  }

  async getSolicitationIntelligence(id: string) {
    const { data } = await this.client.get(`/winning-profile/solicitations/${id}/intelligence`);
    return data;
  }

  async seedWphSample(run = true) {
    const { data } = await this.client.post("/winning-profile/sample", null, { params: { run } });
    return data;
  }
}

export const api = new CIOSApiClient();
export default api;
