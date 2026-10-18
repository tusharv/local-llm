import { useEffect, useState, type FormEvent } from "react";
import { api, selectEndpoint, selectedEndpointId, streamSse, type Endpoint } from "../api";

type Health = { ok: boolean; model_count?: number; error?: string };

export function Setup() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [health, setHealth] = useState<Record<number, Health>>({});
  const [name, setName] = useState("Ollama");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:11434/v1");
  const [kind, setKind] = useState<"openai" | "ollama">("ollama");
  const [confirmed, setConfirmed] = useState(false);
  const [pullName, setPullName] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const data = await api<{ endpoints: Endpoint[] }>("/api/endpoints");
    setEndpoints(data.endpoints);
    const next: Record<number, Health> = {};
    await Promise.all(
      data.endpoints.map(async (endpoint) => {
        next[endpoint.id] = await api<Health>(`/api/health?endpoint_id=${endpoint.id}`);
      }),
    );
    setHealth(next);
  }

  useEffect(() => {
    refresh().catch((reason: Error) => setError(reason.message));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const saved = await api<Endpoint>("/api/endpoints", {
        method: "POST",
        body: JSON.stringify({
          name,
          base_url: baseUrl,
          kind,
          private_network_confirmed: confirmed,
        }),
      });
      selectEndpoint(saved.id);
      setConfirmed(false);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save that server.");
    }
  }

  async function remove(id: number) {
    setError("");
    await api(`/api/endpoints/${id}`, { method: "DELETE" });
    await refresh();
  }

  async function pull(endpointId: number) {
    setMessage("");
    setError("");
    try {
      await streamSse(
        "/api/models/pull",
        {
          method: "POST",
          body: JSON.stringify({ endpoint_id: endpointId, name: pullName }),
        },
        (event) => setMessage(JSON.stringify(event)),
      );
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Pull failed.");
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Setup</h1>
          <p className="quiet">Open Studio at 127.0.0.1:8000. On Windows, localhost often points at IPv6 while Studio listens on IPv4.</p>
        </div>
      </div>
      <form className="card stack" onSubmit={save}>
        <h2>Save a local server</h2>
        <label>Name<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
        <label>Base URL<input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} required /></label>
        <label>
          Kind
          <select value={kind} onChange={(event) => setKind(event.target.value as "openai" | "ollama")}>
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI-compatible</option>
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
          This server is on my private network. Send prompts there.
        </label>
        <button type="submit">Save server</button>
        {error ? <p className="fault">{error}</p> : null}
      </form>
      {endpoints.map((endpoint) => {
        const status = health[endpoint.id];
        const selected = selectedEndpointId() === endpoint.id;
        return (
          <article className="card stack" key={endpoint.id}>
            <div className="row">
              <strong>{endpoint.name}</strong>
              <span className="mono">{endpoint.base_url}</span>
              <span>{endpoint.kind}</span>
              {selected ? <span className="ok">Selected</span> : null}
            </div>
            {endpoint.private_network_confirmed ? <p>Prompts will be sent to this private-network host.</p> : null}
            {status?.ok ? (
              <p className="ok">Reachable. {status.model_count} model{status.model_count === 1 ? "" : "s"} installed.</p>
            ) : (
              <p className="fault">
                Endpoint is down. Start it yourself, then refresh. Use 127.0.0.1 in the address, not localhost.
                {status?.error ? ` ${status.error}` : ""}
              </p>
            )}
            <div className="row">
              <button type="button" className="secondary" onClick={() => selectEndpoint(endpoint.id)}>Use this server</button>
              <button type="button" className="danger" onClick={() => remove(endpoint.id)}>Delete server</button>
            </div>
            {endpoint.kind === "ollama" && status?.ok ? (
              <div className="row">
                <label>Pull a model<input value={pullName} onChange={(event) => setPullName(event.target.value)} placeholder="llama3.2:3b" /></label>
                <button type="button" onClick={() => pull(endpoint.id)} disabled={!pullName.trim()}>Pull</button>
              </div>
            ) : null}
            {message && endpoint.kind === "ollama" ? <p className="mono">{message}</p> : null}
          </article>
        );
      })}
    </div>
  );
}
