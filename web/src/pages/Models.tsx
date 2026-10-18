import { useEffect, useState } from "react";
import { api, selectEndpoint, selectedEndpointId, streamSse, type Endpoint, type ModelRow } from "../api";

export function Models() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointId, setEndpointId] = useState<number | null>(selectedEndpointId());
  const [models, setModels] = useState<ModelRow[]>([]);
  const [pullName, setPullName] = useState("");
  const [progress, setProgress] = useState("");
  const [check, setCheck] = useState("");
  const [error, setError] = useState("");

  const endpoint = endpoints.find((item) => item.id === endpointId) ?? null;

  async function loadEndpoints() {
    const data = await api<{ endpoints: Endpoint[] }>("/api/endpoints");
    setEndpoints(data.endpoints);
    const chosen = data.endpoints.find((item) => item.id === selectedEndpointId()) ?? data.endpoints[0];
    if (chosen) setEndpointId(chosen.id);
  }

  async function loadModels(id: number) {
    const data = await api<{ models: ModelRow[] }>(`/api/models?endpoint_id=${id}`);
    setModels(data.models);
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

  async function pull() {
    if (!endpointId) return;
    setError("");
    setProgress("");
    try {
      await streamSse(
        "/api/models/pull",
        { method: "POST", body: JSON.stringify({ endpoint_id: endpointId, name: pullName }) },
        (event) => setProgress(JSON.stringify(event)),
      );
      await loadModels(endpointId);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Pull failed.");
    }
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
        <h1>Models</h1>
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
      {endpoint?.kind === "openai" ? (
        <p>Pull and delete are not available for this server. Load the model in that runtime, then refresh.</p>
      ) : null}
      {endpoint?.kind === "ollama" ? (
        <div className="card row">
          <label>Pull<input value={pullName} onChange={(event) => setPullName(event.target.value)} placeholder="llama3.2:3b" /></label>
          <button type="button" onClick={pull} disabled={!pullName.trim()}>Pull</button>
          {progress ? <span className="mono">{progress}</span> : null}
        </div>
      ) : null}
      {error ? <p className="fault">{error}</p> : null}
      {check ? <p>{check}</p> : null}
      <table>
        <thead>
          <tr><th>Model</th><th>Sees images</th><th>Source</th><th></th></tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id}>
              <td className="mono">{model.id}</td>
              <td>{model.vision ? "Yes" : "No"}</td>
              <td>{model.vision_source}</td>
              <td className="row">
                <select
                  value={model.vision_source === "override" ? (model.vision ? "on" : "off") : "auto"}
                  onChange={(event) => setOverride(model.id, event.target.value)}
                  aria-label={`Vision override for ${model.id}`}
                >
                  <option value="auto">Automatic</option>
                  <option value="on">Can see images</option>
                  <option value="off">Text only</option>
                </select>
                <button type="button" className="secondary" onClick={() => visionCheck(model.id)}>Vision check</button>
                {endpoint?.kind === "ollama" ? (
                  <button type="button" className="danger" onClick={() => remove(model.id)}>Delete</button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
