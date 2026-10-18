import { ServerRecovery } from "../components/ServerRecovery";
import { ModelDownload } from "../components/ModelDownload";
import { IconServer, IconPlus, IconTrash, IconRefresh, IconArrowRight, IconShieldLock } from "@tabler/icons-react";
import { useEffect, useState, type FormEvent } from "react";
import { api, selectEndpoint, selectedEndpointId, type Endpoint } from "../api";

type Health = { ok: boolean; model_count?: number; error?: string };

export function Setup() {
  const [selectedId, setSelectedId] = useState(selectedEndpointId());
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [health, setHealth] = useState<Record<number, Health>>({});
  const [name, setName] = useState("Ollama");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:11434/v1");
  const [kind, setKind] = useState<"openai" | "ollama">("ollama");
  const [confirmed, setConfirmed] = useState(false);
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
      setSelectedId(saved.id);
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


  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Setup</h1>
          <p className="page-description">A local server is all you need. Connect once, then make yourself at home.</p>
        </div>
      </div>
      <div className="setup-intro"><div><IconShieldLock size={26} /><h2>A workspace that stays yours.</h2><p>Chat, try image-capable models, and compare speed. Your history stays on this computer.</p></div><a className="button secondary" href="#/chat">Open chat <IconArrowRight size={17} /></a></div>
      <div className="setup-columns"><form className="card stack" onSubmit={save}>
        <div className="section-title"><IconServer size={21} /><h2>Connect a server</h2></div><p className="quiet">Start your model server first, then enter its address here.</p><div className="presets">{[{ name: "Ollama", port: 11434, kind: "ollama" as const }, { name: "LM Studio", port: 1234, kind: "openai" as const }, { name: "llama.cpp", port: 8080, kind: "openai" as const }].map((preset) => <button type="button" className="secondary" key={preset.name} onClick={() => { setName(preset.name); setBaseUrl(`http://127.0.0.1:${preset.port}/v1`); setKind(preset.kind); }}>{preset.name}</button>)}</div>
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
        <button type="submit"><IconPlus size={18} /> Save server</button>
        {error ? <p className="fault">{error}</p> : null}
      </form>
      <section className="stack server-list"><div className="section-title"><h2>Your servers</h2><button type="button" className="secondary" onClick={() => refresh().catch((reason: Error) => setError(reason.message))}><IconRefresh size={16} /> Refresh</button></div>{endpoints.length === 0 ? <div className="empty-state"><IconServer size={32} /><h2>Your first connection starts here</h2><p>Choose a preset and save your running server. Then head to Chat to try a model.</p></div> : null}
      {endpoints.map((endpoint) => {
        const status = health[endpoint.id];
        const selected = selectedId === endpoint.id;
        return (
          <article className="card stack" key={endpoint.id}>
            <div className="server-heading">
              <IconServer size={20} /><strong>{endpoint.name}</strong>
              <span className="mono">{endpoint.base_url}</span>
              <span>{endpoint.kind}</span>
              {selected ? <span className="ok">Selected</span> : null}
            </div>
            {endpoint.private_network_confirmed ? <p>Prompts will be sent to this private-network host.</p> : null}
            {status?.ok ? (
              <p className="ok">Reachable. {status.model_count} model{status.model_count === 1 ? "" : "s"} installed.</p>
            ) : status ? (
              <ServerRecovery endpoint={endpoint} error={status.error} onRetry={refresh} />
            ) : <p role="status" className="quiet">Checking connection…</p>}

            <div className="row">
              <button type="button" className="secondary" onClick={() => { selectEndpoint(endpoint.id); setSelectedId(endpoint.id); }}>Use this server</button>
              <button type="button" className="danger" onClick={() => remove(endpoint.id)}><IconTrash size={16} /> Delete server</button>
            </div>
            {endpoint.kind === "ollama" && status?.ok ? (
              <ModelDownload key={endpoint.id} endpointId={endpoint.id} onComplete={() => { refresh().catch((reason: Error) => setError(reason.message)); }} />
            ) : null}
          </article>
        );
      })}</section></div><p className="quiet">Connection tip: use 127.0.0.1 instead of localhost. Studio connects to a running server; start the runtime in its own app or terminal.</p>
    </div>
  );
}
