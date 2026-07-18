import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | null | undefined, currency = "USD"): string {
  if (value == null) return "—";
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return "—";
  return `${Math.round(score)}`;
}

export function formatProbability(p: number | null | undefined): string {
  if (p == null) return "—";
  return `${Math.round(p * 100)}%`;
}

export function getScoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted-foreground";
  if (score >= 90) return "score-excellent";
  if (score >= 75) return "score-good";
  if (score >= 60) return "score-acceptable";
  if (score >= 45) return "score-marginal";
  return "score-unacceptable";
}

export function getScoreLabel(score: number | null | undefined): string {
  if (score == null) return "Pending";
  if (score >= 90) return "Outstanding";
  if (score >= 75) return "Good";
  if (score >= 60) return "Acceptable";
  if (score >= 45) return "Marginal";
  return "Unacceptable";
}

export function getBidColor(recommendation: string | null | undefined): string {
  if (!recommendation) return "text-muted-foreground";
  const r = recommendation.toUpperCase();
  if (r === "BID" || r === "GO") return "bid-go";
  if (r === "NO-BID" || r === "NO_BID" || r === "NO BID") return "bid-nogo";
  return "bid-conditional";
}

export function getDaysUntil(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export function truncate(str: string, maxLength: number): string {
  return str.length > maxLength ? `${str.slice(0, maxLength)}…` : str;
}
