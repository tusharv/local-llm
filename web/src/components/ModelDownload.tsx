import { useEffect, useRef, useState } from "react";
import { IconDownload } from "@tabler/icons-react";
import { api } from "../api";
import { progressLabel } from "../progress";
import { ModelPicker } from "./ModelPicker";

type Job = { id: string; name: string; state: "running" | "done" | "error"; status: string; error: string | null; completed: number | null; total: number | null };
export function ModelDownload({ endpointId, onComplete }: { endpointId: number; onComplete: () => void }) {
  const [name, setName] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const callback = useRef(onComplete);
  callback.current = onComplete;
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    let previous: Job | null = null;
    async function poll() {
      try {
        const data = await api<{ job: Job | null }>(`/api/model-pulls?endpoint_id=${endpointId}`);
        if (!alive) return;
        setJob(data.job); setError(""); setLoaded(true);
        if (data.job && !previous) setName(data.job.name);
        if (data.job?.state === "done" && previous?.state === "running") callback.current();
        previous = data.job;
      } catch (reason) { if (alive) setError(reason instanceof Error ? reason.message : "Cannot check download status."); }
      if (alive) timer = setTimeout(poll, 1500);
    }
    setLoaded(false); setJob(null); setName(""); poll();
    return () => { alive = false; clearTimeout(timer); };
  }, [endpointId]);
  async function pull() {
    setStarting(true); setError("");
    try {
      const data = await api<{ job: Job }>("/api/model-pulls", { method:"POST", body:JSON.stringify({ endpoint_id:endpointId, name:name.trim() }) });
      setJob(data.job);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not start download."); }
    finally { setStarting(false); }
  }
  const running = job?.state === "running";
  return <div className="model-download">
    <ModelPicker value={name} onChange={setName} action={<button type="button" onClick={pull} disabled={!loaded || starting || running || !name.trim()}><IconDownload size={17} />{starting ? "Starting…" : running ? "Pulling…" : "Pull"}</button>} />
    {job ? <div className={`download-status${job.state === "error" ? " fault" : ""}`} role="status"><strong>{job.name}</strong><span>{job.state === "done" ? "Downloaded. Ready to use." : job.error || progressLabel(job)}</span>{running ? <small>You can leave this page or refresh. The download continues while Studio is running.</small> : null}</div> : null}
    {!loaded && !error ? <p className="quiet" role="status">Checking downloads…</p> : null}
    {error ? <p className="fault" role="alert">{error}</p> : null}
  </div>;
}
