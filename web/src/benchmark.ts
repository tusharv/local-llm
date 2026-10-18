import type { BenchmarkResult, BenchmarkRun } from "./api";

export type Profile = "standard" | "code" | "image";
export type CaseSummary = {
  id: string; title: string; kind: string; completed: number; total: number;
  median_ttft_ms: number | null; median_total_ms: number | null; median_tokens_per_second: number | null;
};
export type Summary = {
  completed: number; total: number; failed: number; measured_ms: number;
  median_ttft_ms: number | null; median_total_ms: number | null; median_tokens_per_second: number | null;
  token_basis: string; cases: CaseSummary[]; comparison_key: string | null;
};
export type ReportRun = BenchmarkRun & { profile: Profile; expected_results: number; error: string | null; summary?: Summary };
export type Result = BenchmarkResult & { output_text: string | null; image_url: string | null; token_basis: string | null };
export type Report = { run: ReportRun; results: Result[]; summary: Summary };
export const PROFILES = [
  { id: "standard" as const, title: "General suite", description: "Chat, reasoning, code, and image understanding when supported.", tasks: "5–6 tasks" },
  { id: "code" as const, title: "Code generation", description: "Python and JavaScript tasks with readable code previews.", tasks: "2 tasks" },
  { id: "image" as const, title: "Image generation", description: "Create a 512 × 512 image using a compatible local image server.", tasks: "1 task" },
];
export const profileName = (id: string) => PROFILES.find(profile => profile.id === id)?.title ?? "General suite";
export function duration(ms: number | null | undefined): string {
  if (ms == null) return "Not measured";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}
export const rate = (value: number | null | undefined) => value == null ? "Not measured" : value.toFixed(1);
export function throughputUnit(basis: string) {
  return basis === "tokens" ? "tokens/s" : basis === "chunks" ? "chunks/s (estimate)" : "units/s (mixed or unknown)";
}
