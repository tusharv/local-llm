import { ServerRecovery } from "../components/ServerRecovery";
import { ModelDownload } from "../components/ModelDownload";
import { IconCpu, IconEye, IconTrash, IconRefresh } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { api, selectEndpoint, selectedEndpointId, type Endpoint, type ModelRow } from "../api";

export function Models() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointId, setEndpointId] = useState<number | null>(selectedEndpointId());
  const [loading, setLoading] = useState(true);
  const [models, setModels] = useState<ModelRow[]>([]);
  const [check, setCheck] = useState("");
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");

  const endpoint = endpoints.find((item) => item.id === endpointId) ?? null;

  async function loadEndpoints() {
    const data = await api<{ endpoints: Endpoint[] }>("/api/endpoints");
    setEndpoints(data.endpoints);
    const chosen = data.endpoints.find((item) => item.id === selectedEndpointId()) ?? data.endpoints[0];
    if (chosen) setEndpointId(chosen.id);
    else setLoading(false);
  }

  async function loadModels(id: number) {
    setLoading(true);
    setError("");
    setModels([]);
    setConnectionError("");
    try {
      const data = await api<{ models: ModelRow[] }>(`/api/models?endpoint_id=${id}`);
      setModels(data.models);
    } catch (reason) {
      setConnectionError(reason instanceof Error ? reason.message : "Could not load models.");
    } finally { setLoading(false); }
  }

  useEffect(() => {
    loadEndpoints().catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!endpointId) return;
    loadModels(endpointId).catch((reason: Error) => setError(reason.message));
  }, [endpointId]);

  async function setOverride(model: string, visionOverride: string) {
    if (!endpointId) return;
    await api("/api/models/flags", {
      method: "PUT",
      body: JSON.stringify({
        endpoint_id: endpointId,
        model,
        vision_override: visionOverride === "auto" ? null : visionOverride,
      }),
    });
    await loadModels(endpointId);
  }


  async function remove(model: string) {
    if (!endpointId) return;
    setError("");
    try {
      await api(`/api/models/${encodeURIComponent(model)}?endpoint_id=${endpointId}`, { method: "DELETE" });
      await loadModels(endpointId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Delete failed.");
    }
  }

  async function visionCheck(model: string) {
    if (!endpointId) return;
    setCheck("");
    setError("");
    try {
      const result = await api<{ answer: string; ttft_ms: number | null; total_ms: number | null; vision: boolean }>(
        "/api/vision-check",
        { method: "POST", body: JSON.stringify({ endpoint_id: endpointId, model }) },
      );
      setCheck(`${result.vision ? "Saw the picture" : "Did not accept the picture"}. ${result.answer} Time ${result.total_ms ?? "—"} ms, first token ${result.ttft_ms ?? "—"} ms.`);
      await loadModels(endpointId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Vision check failed.");
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div><h1>Models</h1><p className="page-description">Meet your models. See what they can do and make room for what’s next.</p></div>
        <label>
          Server
          <select
            value={endpointId ?? ""}
            onChange={(event) => {
              const id = Number(event.target.value);
              setEndpointId(id);
              selectEndpoint(id);
            }}
          >
            {endpoints.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
      </div>
      <div className="row"><span className="count-badge"><IconCpu size={17} /> {models.length} installed models</span><button type="button" className="secondary" disabled={!endpointId} onClick={() => endpointId && loadModels(endpointId).catch((reason: Error) => setError(reason.message))}><IconRefresh size={16} /> Refresh models</button></div>
      {endpoint?.kind === "openai" ? (
        <p>Pull and delete are not available for this server. Load the model in that runtime, then refresh.</p>
      ) : null}
      {endpoint?.kind === "ollama" ? (
        <div className="card"><ModelDownload key={endpoint.id} endpointId={endpoint.id} onComplete={() => loadModels(endpoint.id)} /></div>
      ) : null}
      {error ? <p className="fault">{error}</p> : null}
      {connectionError && endpoint ? <ServerRecovery endpoint={endpoint} error={connectionError} onRetry={() => loadModels(endpoint.id)} /> : null}
      {check ? <p>{check}</p> : null}
      {loading ? <p role="status" className="quiet">Loading your models…</p> : null}
      {!loading && !error && !connectionError && models.length === 0 ? <div className="empty-state"><IconCpu size={34} /><h2>No models to show yet</h2><p>{endpoint ? "Load a model in your server, then refresh this list." : "Connect a local server in Setup to see its models."}</p><a className="button secondary" href="#/setup">Open Setup</a></div> : null}
      {models.length > 0 ? <div className="table-scroll"><table>
        <thead>
          <tr><th>Model</th><th>Sees images</th><th>Source</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id}>
              <td className="mono">{model.id}</td>
              <td><span className={`capability ${model.vision ? "vision" : ""}`}>{model.vision ? <IconEye size={15} /> : <IconCpu size={15} />}{model.vision ? "Text + images" : "Text only"}</span></td>
              <td>{model.vision_source}</td>
              <td><div className="table-actions">
                <select
                  value={model.vision_source === "override" ? (model.vision ? "on" : "off") : "auto"}
                  onChange={(event) => setOverride(model.id, event.target.value)}
                  aria-label={`Vision override for ${model.id}`}
                >
                  <option value="auto">Automatic</option>
                  <option value="on">Can see images</option>
                  <option value="off">Text only</option>
                </select>
                <button type="button" className="secondary" onClick={() => visionCheck(model.id)}><IconEye size={16} /> Vision check</button>
                {endpoint?.kind === "ollama" ? (
                  <button type="button" className="danger" onClick={() => remove(model.id)}><IconTrash size={16} /> Delete</button>
                ) : null}
              </div></td>
            </tr>
          ))}
        </tbody>
      </table></div> : null}
    </div>
  );
}
