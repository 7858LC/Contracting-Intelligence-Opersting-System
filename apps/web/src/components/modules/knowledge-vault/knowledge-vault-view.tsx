"use client";

import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  BookOpen,
  Search,
  Trash2,
  FileText,
  Loader2,
  CheckCircle2,
  Clock,
  AlertCircle,
  CloudUpload,
  X,
  Tag,
  Database,
  Layers,
  ScanSearch,
} from "lucide-react";

interface KnowledgeDocument {
  id: string;
  title: string;
  document_type: string;
  file_name: string;
  file_size_bytes: number;
  vectorization_status: string;
  tags: string[];
  description: string | null;
  created_at: string;
  chunk_count: number;
}

interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  text: string;
  score: number;
  metadata: Record<string, unknown>;
}

const DOC_TYPES = [
  { value: "past_performance", label: "Past Performance", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  { value: "proposal", label: "Proposal", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  { value: "capability_statement", label: "Capability Statement", color: "bg-violet-500/10 text-violet-400 border-violet-500/20" },
  { value: "pricing_data", label: "Pricing Data", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  { value: "technical_approach", label: "Technical Approach", color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20" },
  { value: "teaming_agreement", label: "Teaming Agreement", color: "bg-pink-500/10 text-pink-400 border-pink-500/20" },
  { value: "regulatory_guidance", label: "Regulatory Guidance", color: "bg-orange-500/10 text-orange-400 border-orange-500/20" },
  { value: "competitor_intel", label: "Competitor Intel", color: "bg-red-500/10 text-red-400 border-red-500/20" },
  { value: "lessons_learned", label: "Lessons Learned", color: "bg-teal-500/10 text-teal-400 border-teal-500/20" },
  { value: "general", label: "General", color: "bg-secondary text-muted-foreground border-border" },
  { value: "other", label: "Other", color: "bg-secondary text-muted-foreground border-border" },
];

const STATUS_CONFIG = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  processing: { icon: Loader2, label: "Vectorizing…", className: "text-blue-400 animate-spin" },
  completed: { icon: CheckCircle2, label: "Ready", className: "text-emerald-400" },
  failed: { icon: AlertCircle, label: "Failed", className: "text-red-400" },
} as const;

function getDocTypeConfig(value: string) {
  return DOC_TYPES.find((t) => t.value === value) ?? DOC_TYPES[DOC_TYPES.length - 1];
}

function formatBytes(bytes: number): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function KnowledgeVaultView() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [uploadForm, setUploadForm] = useState({
    title: "",
    document_type: "past_performance",
    description: "",
    tags: "",
  });
  const [uploading, setUploading] = useState(false);

  const { data: documents = [], isLoading } = useQuery<KnowledgeDocument[]>({
    queryKey: ["knowledge-documents", typeFilter],
    queryFn: () => api.getKnowledgeDocuments({ document_type: typeFilter || undefined }),
    refetchInterval: 15_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteKnowledgeDocument(id),
    onSuccess: () => {
      toast.success("Document deleted");
      queryClient.invalidateQueries({ queryKey: ["knowledge-documents"] });
    },
    onError: () => toast.error("Delete failed"),
  });

  function setFile(file: File | null) {
    setSelectedFile(file);
    if (file && !uploadForm.title) {
      setUploadForm((f) => ({ ...f, title: file.name.replace(/\.[^.]+$/, "") }));
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) setFile(file);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFile) { toast.error("Select a file first"); return; }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("title", uploadForm.title || selectedFile.name);
      formData.append("document_type", uploadForm.document_type);
      if (uploadForm.description) formData.append("description", uploadForm.description);
      if (uploadForm.tags) {
        const tagList = uploadForm.tags.split(",").map((t) => t.trim()).filter(Boolean);
        formData.append("tags", JSON.stringify(tagList));
      }
      await api.uploadKnowledgeDocument(formData);
      toast.success("Document uploaded — vectorization in progress");
      queryClient.invalidateQueries({ queryKey: ["knowledge-documents"] });
      setSelectedFile(null);
      setUploadForm({ title: "", document_type: "past_performance", description: "", tags: "" });
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Upload failed";
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const results = await api.searchKnowledge(searchQuery, 10);
      setSearchResults(results);
    } catch {
      toast.error("Search failed");
    } finally {
      setSearching(false);
    }
  }

  const docs = documents as KnowledgeDocument[];
  const vectorized = docs.filter((d) => d.vectorization_status === "completed");
  const totalBytes = docs.reduce((s, d) => s + (d.file_size_bytes ?? 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Knowledge Vault</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Private AI memory — your documents, your context, zero cross-tenant contamination.
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Database, label: "Total documents", value: docs.length.toString() },
          { icon: Layers, label: "Vectorized & searchable", value: vectorized.length.toString() },
          { icon: BookOpen, label: "Storage used", value: formatBytes(totalBytes) },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="bg-card border border-border rounded-lg px-5 py-4 flex items-center gap-4">
            <div className="w-9 h-9 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
              <Icon className="w-4 h-4 text-primary" />
            </div>
            <div>
              <div className="text-xl font-bold">{value}</div>
              <div className="text-xs text-muted-foreground">{label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left col: upload + documents */}
        <div className="col-span-2 space-y-5">
          {/* Upload card */}
          <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-4 text-sm flex items-center gap-2">
              <CloudUpload className="w-4 h-4 text-primary" />
              Upload Document
            </h3>
            <form onSubmit={handleUpload} className="space-y-3">
              {/* Drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "border-2 border-dashed rounded-lg px-4 py-6 text-center cursor-pointer transition-colors",
                  dragOver
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-secondary/30"
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc,.txt,.csv,.xlsx"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                {selectedFile ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileText className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">{selectedFile.name}</span>
                    <span className="text-xs text-muted-foreground">({formatBytes(selectedFile.size)})</span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                      className="ml-1 text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <>
                    <CloudUpload className="w-7 h-7 mx-auto mb-2 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">
                      <span className="text-primary font-medium">Click to browse</span> or drag & drop
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-1">PDF · DOCX · TXT · CSV · XLSX · Max 50 MB</p>
                  </>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">Title</label>
                  <input
                    value={uploadForm.title}
                    onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="Q4 2024 Proposal — DHS"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">Document type</label>
                  <select
                    value={uploadForm.document_type}
                    onChange={(e) => setUploadForm({ ...uploadForm, document_type: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    {DOC_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1 text-muted-foreground">
                  Tags <span className="font-normal">(comma-separated)</span>
                </label>
                <input
                  value={uploadForm.tags}
                  onChange={(e) => setUploadForm({ ...uploadForm, tags: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="cybersecurity, federal, DHS, FY24"
                />
              </div>

              <button
                type="submit"
                disabled={uploading || !selectedFile}
                className="w-full py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</>
                ) : (
                  <><CloudUpload className="w-4 h-4" /> Upload & Vectorize</>
                )}
              </button>
            </form>
          </div>

          {/* Document list */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-sm flex-1">Documents</h3>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-1.5 bg-card border border-border rounded-md text-xs focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option value="">All types</option>
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-16 bg-card border border-border rounded-lg animate-pulse" />
                ))}
              </div>
            ) : docs.length === 0 ? (
              <div className="text-center py-16 border border-border rounded-xl bg-card">
                <BookOpen className="w-10 h-10 mx-auto mb-3 text-muted-foreground/20" />
                <p className="text-sm font-medium text-muted-foreground">No documents yet</p>
                <p className="text-xs text-muted-foreground/60 mt-1">Upload your first document to start building your Knowledge Vault.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {docs.map((doc) => {
                  const status = STATUS_CONFIG[doc.vectorization_status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending;
                  const StatusIcon = status.icon;
                  const typeConfig = getDocTypeConfig(doc.document_type);
                  return (
                    <div
                      key={doc.id}
                      className="bg-card border border-border rounded-lg px-4 py-3.5 flex items-start gap-3 hover:border-border/80 transition-colors"
                    >
                      <div className="w-8 h-8 rounded-md bg-secondary flex items-center justify-center shrink-0 mt-0.5">
                        <FileText className="w-4 h-4 text-muted-foreground" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{doc.title}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-1.5">
                          <span className={cn(
                            "inline-flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded border",
                            typeConfig.color
                          )}>
                            {typeConfig.label}
                          </span>
                          <span className="text-xs text-muted-foreground">{formatBytes(doc.file_size_bytes)}</span>
                          {doc.chunk_count > 0 && (
                            <span className="text-xs text-muted-foreground">{doc.chunk_count} chunks</span>
                          )}
                          <span className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</span>
                          {doc.tags?.slice(0, 3).map((tag) => (
                            <span key={tag} className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                              <Tag className="w-2.5 h-2.5" />{tag}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className={cn("flex items-center gap-1.5 text-xs shrink-0", status.className)}>
                        <StatusIcon className="w-3.5 h-3.5" />
                        <span>{status.label}</span>
                      </div>

                      <button
                        onClick={() => { if (confirm(`Delete "${doc.title}"?`)) deleteMutation.mutate(doc.id); }}
                        className="text-muted-foreground/40 hover:text-red-400 transition-colors p-1 shrink-0"
                        title="Delete document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right col: semantic search */}
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5">
            <h3 className="font-semibold mb-1 text-sm flex items-center gap-2">
              <ScanSearch className="w-4 h-4 text-primary" />
              Semantic Search
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Ask in natural language — the AI retrieves the most relevant passages from your vault.
            </p>
            <form onSubmit={handleSearch} className="space-y-2">
              <textarea
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50"
                placeholder="What past performance do we have for cybersecurity operations at the federal level?"
              />
              <button
                type="submit"
                disabled={searching || !searchQuery.trim()}
                className="w-full py-2 bg-primary text-primary-foreground rounded-md text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
              >
                {searching ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Searching…</>
                ) : (
                  <><Search className="w-4 h-4" /> Search</>
                )}
              </button>
            </form>
          </div>

          {/* Results */}
          {searchResults !== null && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground px-1">
                {searchResults.length === 0 ? "No matches found" : `${searchResults.length} relevant passage${searchResults.length !== 1 ? "s" : ""} found`}
              </p>
              {searchResults.map((r) => {
                const pct = Math.round(r.score * 100);
                return (
                  <div key={r.chunk_id} className="bg-card border border-border rounded-lg p-3.5 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-primary truncate">{r.document_title}</p>
                      <div className="flex items-center gap-1 shrink-0">
                        <div
                          className="h-1.5 w-12 bg-secondary rounded-full overflow-hidden"
                          title={`${pct}% relevance`}
                        >
                          <div
                            className="h-full bg-primary rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-muted-foreground w-7 text-right">{pct}%</span>
                      </div>
                    </div>
                    {r.metadata?.document_type && (
                      <span className={cn(
                        "inline-flex text-[10px] font-medium px-1.5 py-0.5 rounded border",
                        getDocTypeConfig(r.metadata.document_type as string).color
                      )}>
                        {getDocTypeConfig(r.metadata.document_type as string).label}
                      </span>
                    )}
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-5">{r.text}</p>
                  </div>
                );
              })}
            </div>
          )}

          {/* Placeholder when no search yet */}
          {searchResults === null && vectorized.length > 0 && (
            <div className="bg-card border border-border/50 rounded-xl p-5 text-center">
              <Search className="w-8 h-8 mx-auto mb-2 text-muted-foreground/20" />
              <p className="text-xs text-muted-foreground">
                {vectorized.length} document{vectorized.length !== 1 ? "s" : ""} ready to search
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
