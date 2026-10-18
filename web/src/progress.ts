/** Turn runtime progress events into useful status copy. */
export function progressLabel(event: Record<string, unknown>): string {
  if (typeof event.error === "string") return `Failed: ${event.error}`;
  if (event.discarded) return "Warmup complete. Starting measured prompts…";
  if (event.done || event.status === "done") return "Completed. Your results are ready.";
  if (typeof event.status === "string") {
    const completed = Number(event.completed);
    const total = Number(event.total);
    return total > 0 && Number.isFinite(completed)
      ? `${event.status} · ${Math.min(100, Math.round(completed / total * 100))}%`
      : event.status;
  }
  if (typeof event.case_id === "string") {
    const speed = typeof event.tokens_per_second === "number" ? ` · ${event.tokens_per_second.toFixed(1)} tokens/s` : "";
    return `Completed ${event.case_id.replaceAll("_", " ")}${speed}`;
  }
  return "Working…";
}
