import { useEffect, useRef, useState } from "react";
import { IconPlayerPlay, IconDownload, IconChartBar, IconCode, IconPhoto, IconPrinter, IconRefresh, IconClock, IconArrowRight } from "@tabler/icons-react";
import { api, selectEndpoint, selectedEndpointId, streamSse, type Endpoint, type ModelRow } from "../api";
import { PROFILES, profileName, duration, type Profile, type Report, type ReportRun } from "../benchmark";
import { BenchmarkReport } from "../components/BenchmarkReport";
import "../benchmark.css";

type Progress = { completed: number; total: number; label: string };
export function Benchmarks() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointId, setEndpointId] = useState<number | null>(selectedEndpointId());
  const [models, setModels] = useState<ModelRow[]>([]);
  const [model, setModel] = useState("");
  const [profile, setProfile] = useState<Profile>("standard");
  const [warmup, setWarmup] = useState(true);
  const [repeats, setRepeats] = useState<1 | 3>(1);
  const [runs, setRuns] = useState<ReportRun[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [comparisonId, setComparisonId] = useState<number | null>(null);
  const [comparison, setComparison] = useState<Report | null>(null);
  const [progress, setProgress] = useState<Progress>({ completed: 0, total: 0, label: "Preparing…" });
  const [elapsed, setElapsed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reportRevision, setReportRevision] = useState(0);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState("");
  const [modelError, setModelError] = useState("");
  const reportRef = useRef<HTMLDivElement>(null);
  const compatible = runs.filter(run => run.id !== report?.run.id && report?.summary.comparison_key && run.summary?.comparison_key === report.summary.comparison_key);

  async function refreshRuns() {
    const data = await api<{ runs: ReportRun[] }>("/api/benchmarks");
    setRuns(data.runs);
    setReportRevision(value => value + 1);
    setSelectedId(current => current ?? data.runs[0]?.id ?? null);
    return data.runs;
  }
  useEffect(() => {
    let cancelled = false;
    Promise.all([api<{ endpoints: Endpoint[] }>("/api/endpoints"), api<{ runs: ReportRun[] }>("/api/benchmarks")])
      .then(([servers, history]) => {
        if (cancelled) return;
        setEndpoints(servers.endpoints);
        const chosen = servers.endpoints.find(item => item.id === selectedEndpointId()) ?? servers.endpoints[0];
        setEndpointId(chosen?.id ?? null);
        setRuns(history.runs);
        setSelectedId(history.runs[0]?.id ?? null);
      }).catch(reason => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    let cancelled = false;
    setModels([]); setModel(""); setModelError("");
    if (!endpointId) return;
    api<{ models: ModelRow[] }>(`/api/models?endpoint_id=${endpointId}`).then(data => {
      if (!cancelled) { setModels(data.models); setModel(data.models[0]?.id || ""); }
    }).catch(() => { if (!cancelled) setModelError("Could not load models. Check the server in Setup, or enter an installed model name."); });
    return () => { cancelled = true; };
  }, [endpointId]);
  useEffect(() => {
    let cancelled = false;
    setComparisonId(null); setComparison(null); setReport(null);
    if (!selectedId) { setReportLoading(false); return; }
    setReportLoading(true);
    api<Report>(`/api/benchmarks/${selectedId}`).then(data => { if (!cancelled) setReport(data); })
      .catch(reason => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setReportLoading(false); });
    return () => { cancelled = true; };
  }, [selectedId, reportRevision]);
  useEffect(() => {
    let cancelled = false;
    setComparison(null);
    if (comparisonId) api<Report>(`/api/benchmarks/${comparisonId}`).then(data => {
      if (!cancelled && data.summary.comparison_key === report?.summary.comparison_key) setComparison(data);
    }).catch(reason => { if (!cancelled) setError(reason.message); });
    return () => { cancelled = true; };
  }, [comparisonId, report]);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now(); setElapsed(0);
    const timer = window.setInterval(() => setElapsed(Date.now() - started), 1000);
    return () => window.clearInterval(timer);
  }, [busy]);

  async function start() {
    if (!endpointId || !model.trim() || busy) return;
    setBusy(true); setError(""); setProgress({ completed: 0, total: 0, label: "Preparing your run…" });
    let finalId: number | null = null;
    try {
      await streamSse("/api/benchmarks", { method: "POST", body: JSON.stringify({ endpoint_id: endpointId, model: model.trim(), profile, warmup, repeat_count: repeats }) }, event => {
        if (typeof event.run_id === "number") finalId = event.run_id;
        if (event.event === "plan") setProgress({ completed: 0, total: Number(event.total), label: "Run planned" });
        if (event.event === "warmup") setProgress(current => ({ ...current, label: "Warming up the model…" }));
        if (event.event === "case_started") setProgress({ completed: Number(event.completed), total: Number(event.total), label: `${event.title} · repeat ${Number(event.repeat_index) + 1}` });
        if (event.event === "case_complete") setProgress(current => ({ ...current, completed: Number(event.completed), label: event.error ? "Sample failed; continuing…" : "Sample saved" }));
        if (event.event === "finished") setProgress(current => ({ ...current, label: event.status === "done" ? "Report ready" : "Run finished with errors" }));
        if (event.event === "error" && typeof event.error === "string") setError(event.error);
      });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The run could not finish."); }
    finally {
      try { await refreshRuns(); if (finalId) setSelectedId(finalId); }
      catch (reason) { setError(reason instanceof Error ? reason.message : "Could not refresh history."); }
      setBusy(false);
    }
  }
  const Icons = { standard: IconChartBar, code: IconCode, image: IconPhoto };
  return <div className="stack benchmark-page">
    <header className="page-head benchmark-page-head"><div><h1>Benchmarks</h1><p className="page-description">Put your models to the test. Turn each run into a report you can see, compare, and share.</p></div><span className="benchmark-suite-label">Performance lab · Suite 2</span></header>
    <section className="benchmark-builder no-print" aria-label="Configure a benchmark">
      <div className="section-title"><h2>What would you like to measure?</h2><span className="quiet">One model. Real measurements.</span></div>
      <div className="profile-options">{PROFILES.map(item => { const Icon = Icons[item.id]; return <button type="button" className={`profile-option ${profile === item.id ? "selected" : ""}`} key={item.id} aria-pressed={profile === item.id} disabled={busy} onClick={() => { setProfile(item.id); setWarmup(item.id !== "image"); }}><span className="profile-icon"><Icon size={23} /></span><strong>{item.title}</strong><span>{item.description}</span><small>{item.tasks} <IconArrowRight size={14} /></small></button>; })}</div>
      {loading ? <p role="status">Loading your servers and runs…</p> : !endpoints.length ? <div className="benchmark-notice">Connect a running server before your first test. <a href="#/setup">Open Setup</a></div> : null}
      {profile === "image" ? <div className="benchmark-notice"><IconPhoto size={20} /><span>Choose an image model on a server supporting <code>/v1/images/generations</code> with base64 output. Image understanding alone does not provide image generation. <a href="#/setup">Manage servers</a></span></div> : null}
      <fieldset className="benchmark-form" disabled={busy || loading || !endpoints.length}>
        <label>Server<select value={endpointId ?? ""} onChange={event => { const id = Number(event.target.value); setEndpointId(id); selectEndpoint(id); }}>{!endpoints.length ? <option value="">No server saved</option> : null}{endpoints.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>{profile === "image" ? "Image model" : "Model"}<input value={model} onChange={event => setModel(event.target.value)} list="benchmark-models" placeholder="Enter an installed model name" /></label>
        <datalist id="benchmark-models">{models.map(item => <option key={item.id} value={item.id} />)}</datalist>
        <label>Repeats<select value={repeats} onChange={event => setRepeats(Number(event.target.value) as 1 | 3)}><option value={1}>1 · Quick run</option><option value={3}>3 · Median result</option></select></label>
        <button type="button" className="benchmark-start" onClick={start} disabled={busy || !model.trim() || !endpointId}><IconPlayerPlay size={18} />{busy ? "Running…" : "Run benchmark"}</button>
        <label className="check benchmark-warmup"><input type="checkbox" checked={warmup} onChange={event => setWarmup(event.target.checked)} />Discard a warmup {profile === "image" ? "image (adds one generation)" : "request"}</label>
      </fieldset>
      {modelError ? <p className="quiet">{modelError}</p> : null}
      {profile === "standard" ? <p className="quiet">Image understanding is included only for a model marked as image-capable. Code tasks generate text; correctness is not scored.</p> : null}
    </section>
    {error ? <p className="fault no-print" role="alert">{error}</p> : null}
    {busy ? <section className="run-progress no-print" aria-live="polite"><div><IconClock size={20} /><strong>{progress.label}</strong><span>{duration(elapsed)} elapsed</span></div><progress value={progress.completed} max={progress.total || 1} aria-label="Benchmark progress" /><p>{progress.completed} of {progress.total || "…"} samples processed. Warmup is excluded from results.</p></section> : null}
    <section className="run-history no-print"><div className="section-title"><h2>Your runs</h2><button className="secondary" disabled={busy} onClick={() => refreshRuns().catch(reason => setError(reason.message))}><IconRefresh size={16} />Refresh</button></div>
      {!loading && !runs.length ? <div className="benchmark-empty"><IconChartBar size={36} /><h3>Every run tells a story.</h3><p>Choose a suite above. Your first report will show where the model responds quickly, how much it produces, and what it made.</p></div> : null}
      {runs.length ? <div className="history-list">{runs.map(run => <button className={`history-item ${selectedId === run.id ? "selected" : ""}`} key={run.id} disabled={busy} aria-pressed={selectedId === run.id} onClick={() => setSelectedId(run.id)}><span><strong>{run.model}</strong><small>{run.endpoint_name || "Deleted server"} · {profileName(run.profile)} · Suite {run.suite_version}</small></span><span><strong>{run.status === "running" ? "Running" : run.summary ? `${run.summary.completed}/${run.summary.total} completed` : run.status}</strong><small>{new Date(run.started_at).toLocaleString()}</small></span><IconArrowRight size={17} /></button>)}</div> : null}
    </section>
    {reportLoading ? <p role="status">Loading report…</p> : null}
    {report ? <div ref={reportRef} className="report-container"><div className="report-toolbar no-print"><label>Compare with<select value={comparisonId ?? ""} onChange={event => setComparisonId(event.target.value ? Number(event.target.value) : null)}><option value="">{compatible.length ? "Choose a compatible run" : "No compatible runs yet"}</option>{compatible.map(run => <option key={run.id} value={run.id}>#{run.id} · {run.model} · {run.endpoint_name}</option>)}</select></label><div className="row"><a className="button secondary" href={`/api/benchmarks/${report.run.id}/export`}><IconDownload size={16} />Export JSON</a><button className="secondary" onClick={() => window.print()}><IconPrinter size={16} />Print / Save PDF</button></div></div><BenchmarkReport report={report} comparison={comparison} /></div> : null}
  </div>;
}
