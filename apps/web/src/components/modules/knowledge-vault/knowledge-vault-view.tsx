"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { BookOpen, Upload, Search, Trash2, FileText, Loader2, CheckCircle2, Clock, AlertCircle } from "lucide-react";

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
  { value: "past_performance", label: "Past Performance" },
  { value: "proposal", label: "Proposal" },
  { value: "capability_statement", label: "Capability Statement" },
  { value: "pricing_data", label: "Pricing Data" },
  { value: "technical_approach", label: "Technical Approach" },
  { value: "teaming_agreement", label: "Teaming Agreement" },
  { value: "regulatory_guidance", label: "Regulatory Guidance" },
  { value: "competitor_intel", label: "Competitor Intelligence" },
  { value: "lessons_learned", label: "Lessons Learned" },
  { value: "other", label: "Other" },
];

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  pending: { icon: <Clock className="w-3.5 h-3.5" />, label: "Pending", color: "text-muted-foreground" },
  processing: { icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />, label: "Vectorizing", color: "text-blue-400" },
  completed: { icon: <CheckCircle2 className="w-3.5 h-3.5" />, label: "Ready", color: "text-emerald-400" },
  failed: { icon: <AlertCircle className="w-3.5 h-3.5" />, label: "Failed", color: "text-red-400" },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function KnowledgeVaultView() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [uploadForm, setUploadForm] = useState({ title: "", document_type: "past_performance", description: "", tags: "" });
  const [uploading, setUploading] = useState(false);

  const { data: documents = [], isLoading } = useQuery({
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

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) { toast.error("Select a file"); return; }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", uploadForm.title || file.name);
      formData.append("document_type", uploadForm.document_type);
      if (uploadForm.description) formData.append("description", uploadForm.description);
      if (uploadForm.tags) formData.append("tags", JSON.stringify(uploadForm.tags.split(",").map((t) => t.trim()).filter(Boolean)));
      await api.uploadKnowledgeDocument(formData);
      toast.success("Document uploaded — vectorization in progress");
      queryClient.invalidateQueries({ queryKey: ["knowledge-documents"] });
      setUploadForm({ title: "", document_type: "past_performance", description: "", tags: "" });
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
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

  const ready = (documents as KnowledgeDocument[]).filter((d) => d.vectorization_status === "completed").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Knowledge Vault</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {(documents as KnowledgeDocument[]).length} documents · {ready} vectorized
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Upload + Document list */}
        <div className="col-span-2 space-y-5">
          {/* Upload form */}
          <div className="bg-card border border-border rounded-lg p-5">
            <h3 className="font-semibold mb-4 flex items-center gap-2 text-sm">
              <Upload className="w-4 h-4" />
              Upload Document
            </h3>
            <form onSubmit={handleUpload} className="space-y-3">
              <div className="border-2 border-dashed border-border rounded-md p-4 text-center">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f && !uploadForm.title) setUploadForm({ ...uploadForm, title: f.name.replace(/\.[^.]+$/, "") });
                  }}
                />
                <button type="button" onClick={() => fileInputRef.current?.click()}
                  className="text-sm text-primary hover:underline">
                  Choose file
                </button>
                <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT, MD · Max 50 MB</p>
                {fileInputRef.current?.files?.[0] && (
                  <p className="text-xs text-emerald-400 mt-1">{fileInputRef.current.files[0].name}</p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">Title</label>
                  <input value={uploadForm.title} onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="Q4 2024 Proposal – DHS" />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1 text-muted-foreground">Document type</label>
                  <select value={uploadForm.document_type} onChange={(e) => setUploadForm({ ...uploadForm, document_type: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
                    {DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1 text-muted-foreground">Tags (comma separated)</label>
                <input value={uploadForm.tags} onChange={(e) => setUploadForm({ ...uploadForm, tags: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="cybersecurity, federal, DHS" />
              </div>
              <button type="submit" disabled={uploading}
                className="w-full py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50">
                {uploading ? "Uploading…" : "Upload & Vectorize"}
              </button>
            </form>
          </div>

          {/* Document list */}
          <div className="space-y-2">
            <div className="flex gap-3 items-center">
              <h3 className="font-semibold text-sm flex-1">Documents</h3>
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-1.5 bg-card border border-border rounded-md text-xs focus:outline-none">
                <option value="">All types</option>
                {DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-14 bg-card border border-border rounded-lg animate-pulse" />
                ))}
              </div>
            ) : (documents as KnowledgeDocument[]).length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <BookOpen className="w-10 h-10 mx-auto mb-2 opacity-20" />
                <p className="text-sm">No documents yet. Upload your first document above.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {(documents as KnowledgeDocument[]).map((doc) => {
                  const status = STATUS_CONFIG[doc.vectorization_status] || STATUS_CONFIG.pending;
                  return (
                    <div key={doc.id} className="bg-card border border-border rounded-lg px-4 py-3 flex items-center gap-3">
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{doc.title}</p>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-muted-foreground">
                            {DOC_TYPES.find((t) => t.value === doc.document_type)?.label || doc.document_type}
                          </span>
                          <span className="text-xs text-muted-foreground">{formatBytes(doc.file_size_bytes)}</span>
                          {doc.tags?.length > 0 && (
                            <span className="text-xs text-muted-foreground">{doc.tags.slice(0, 2).join(", ")}</span>
                          )}
                        </div>
                      </div>
                      <div className={cn("flex items-center gap-1 text-xs", status.color)}>
                        {status.icon}
                        <span>{status.label}</span>
                      </div>
                      <button
                        onClick={() => { if (confirm("Delete this document?")) deleteMutation.mutate(doc.id); }}
                        className="text-muted-foreground hover:text-red-400 transition-colors p-1"
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

        {/* Right: Semantic search */}
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-lg p-5">
            <h3 className="font-semibold mb-3 text-sm flex items-center gap-2">
              <Search className="w-4 h-4" />
              Semantic Search
            </h3>
            <form onSubmit={handleSearch} className="space-y-2">
              <textarea
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="What relevant past performance do we have for cybersecurity operations work?"
              />
              <button type="submit" disabled={searching}
                className="w-full py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {searching ? "Searching…" : "Search"}
              </button>
            </form>
          </div>

          {/* Search results */}
          {searchResults && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">{searchResults.length} results</p>
              {searchResults.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No matches found</p>
              ) : (
                searchResults.map((r) => (
                  <div key={r.chunk_id} className="bg-card border border-border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-xs font-medium text-primary truncate">{r.document_title}</p>
                      <span className="text-xs font-mono text-muted-foreground shrink-0 ml-2">
                        {(r.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-4">{r.text}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
