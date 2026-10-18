import { useEffect, useState } from "react";
import {
  api,
  selectEndpoint,
  selectedEndpointId,
  streamSse,
  type BenchmarkResult,
  type BenchmarkRun,
  type Endpoint,
  type ModelRow,
} from "../api";

export function Benchmarks() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointId, setEndpointId] = useState<number | null>(selectedEndpointId());
  const [models, setModels] = useState<ModelRow[]>([]);
  const [model, setModel] = useState("");
  const [warmup, setWarmup] = useState(true);
  const [repeatCount, setRepeatCount] = useState<1 | 3>(1);
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [progress, setProgress] = useState<string[]>([]);
  const [selectedRun, setSelectedRun] = useState<BenchmarkResult[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const suite = runs[0]?.suite_version;
  const comparable = runs.filter((run) => run.suite_version === suite && run.status === "done");

  async function loadRuns() {
    const data = await api<{ runs: BenchmarkRun[] }>("/api/benchmarks");
    setRuns(data.runs);
  }

  useEffect(() => {
    api<{ endpoints: Endpoint[] }>("/api/endpoints")
      .then((data) => {
        setEndpoints(data.endpoints);
        const chosen = data.endpoints.find((item) => item.id === selectedEndpointId()) ?? data.endpoints[0];
        if (chosen) setEndpointId(chosen.id);
      })
      .catch((reason: Error) => setError(reason.message));
    loadRuns().catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    if (!endpointId) return;
    api<{ models: ModelRow[] }>(`/api/models?endpoint_id=${endpointId}`)
      .then((data) => {
        setModels(data.models);
        setModel((current) => current || data.models[0]?.id || "");
      })
      .catch(() => setModels([]));
  }, [endpointId]);

  async function start() {
    if (!endpointId || !model) return;
    setBusy(true);
    setError("");
    setProgress([]);
    try {
      await streamSse(
        "/api/benchmarks",
        {
          method: "POST",
          body: JSON.stringify({
            endpoint_id: endpointId,
            model,
            warmup,
            repeat_count: repeatCount,
          }),
        },
        (event) => setProgress((current) => [...current, JSON.stringify(event)]),
      );
      await loadRuns();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The benchmark did not start.");
    } finally {
      setBusy(false);
    }
  }

  async function openRun(id: number) {
    const data = await api<{ results: BenchmarkResult[] }>(`/api/benchmarks/${id}`);
    setSelectedRun(data.results);
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Benchmarks</h1>
          <p>These numbers are single-user speed for this server and tokenizer, not a quality score.</p>
        </div>
      </div>
      <div className="card stack">
        <div className="row">
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
          <label>
            Model
            <input value={model} onChange={(event) => setModel(event.target.value)} list="benchmark-models" />
          </label>
          <datalist id="benchmark-models">
            {models.map((item) => <option key={item.id} value={item.id} />)}
          </datalist>
          <label className="check">
            <input type="checkbox" checked={warmup} onChange={(event) => setWarmup(event.target.checked)} />
            Discard a warmup run
          </label>
          <label>
            Repeats
            <select value={repeatCount} onChange={(event) => setRepeatCount(Number(event.target.value) as 1 | 3)}>
              <option value={1}>1</option>
              <option value={3}>3</option>
            </select>
          </label>
          <button type="button" onClick={start} disabled={busy || !model}>Start benchmark</button>
        </div>
        {error ? <p className="fault">{error}</p> : null}
        {progress.map((line, index) => <p className="mono" key={`${index}-${line}`}>{line}</p>)}
      </div>
      <h2>Same suite</h2>
      <table>
        <thead>
          <tr><th>Model</th><th>Server</th><th>Suite</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          {comparable.map((run) => (
            <tr key={run.id}>
              <td className="mono">{run.model}</td>
              <td>{run.endpoint_name}</td>
              <td>{run.suite_version}</td>
              <td>{run.status}</td>
              <td className="row">
                <button type="button" className="secondary" onClick={() => openRun(run.id)}>Results</button>
                <a className="button secondary" href={`/api/benchmarks/${run.id}/export`}>Export JSON</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {selectedRun.length > 0 ? (
        <table>
          <thead>
            <tr><th>Case</th><th>Repeat</th><th>First token ms</th><th>Tokens / second</th><th>Preview</th></tr>
          </thead>
          <tbody>
            {selectedRun.map((row) => (
              <tr key={row.id}>
                <td>{row.case_id}</td>
                <td>{row.repeat_index + 1}</td>
                <td>{row.ttft_ms ?? "—"}</td>
                <td>{row.tokens_per_second?.toFixed(2) ?? "—"}</td>
                <td>{row.error || row.output_preview}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
