export type Endpoint = {
  id: number;
  name: string;
  base_url: string;
  kind: "openai" | "ollama";
  private_network_confirmed: boolean;
};

export type ModelRow = {
  id: string;
  vision: boolean;
  vision_source: string;
  family?: string;
  size_bytes?: number;
};

export type Conversation = {
  id: number;
  title: string;
  endpoint_id: number;
  model: string;
  updated_at: string;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  thinking?: string | null;
  error: string | null;
  created_at: string;
  image_url?: string;
};

export type BenchmarkRun = {
  id: number;
  endpoint_id: number;
  endpoint_name: string | null;
  model: string;
  suite_version: string;
  status: string;
  warmup: boolean;
  repeat_count: number;
  started_at: string;
  finished_at: string | null;
};

export type BenchmarkResult = {
  id: number;
  case_id: string;
  kind: string;
  repeat_index: number;
  ttft_ms: number | null;
  tokens_per_second: number | null;
  total_ms: number | null;
  output_preview: string | null;
  error: string | null;
};

const SELECTED = "studio.endpointId";

export function selectedEndpointId(): number | null {
  const raw = localStorage.getItem(SELECTED);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isInteger(id) ? id : null;
}

export function selectEndpoint(id: number): void {
  localStorage.setItem(SELECTED, String(id));
  window.dispatchEvent(new Event("studio-endpoint"));
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(typeof data.error === "string" ? data.error : `Request failed (${response.status})`);
  }
  return data as T;
}

export async function streamSse(
  path: string,
  init: RequestInit,
  onEvent: (data: Record<string, unknown>) => void,
): Promise<void> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  if (!response.ok || !response.body) {
    const text = await response.text();
    let message = response.statusText;
    try {
      const data = JSON.parse(text);
      if (typeof data.error === "string") message = data.error;
    } catch {
      if (text) message = text;
    }
    throw new Error(message);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      onEvent(JSON.parse(payload) as Record<string, unknown>);
    }
  }
}
