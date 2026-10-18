import { useEffect, useRef } from "react";
import { IconArrowDown, IconArrowUp, IconCheck, IconClock, IconCode, IconEye, IconPhoto, IconBolt, IconMessageCircle } from "@tabler/icons-react";
import { duration, profileName, rate, throughputUnit, type Report, type CaseSummary } from "../benchmark";

const iconFor = (kind: string) => kind === "image" ? IconPhoto : kind === "code" ? IconCode : kind === "vision" ? IconEye : IconMessageCircle;

function CaseChart({ cases, metric, unit, format }: { cases: CaseSummary[]; metric: "median_ttft_ms" | "median_total_ms" | "median_tokens_per_second"; unit: string; format: (value: number | null) => string }) {
  const max = Math.max(...cases.map(item => item[metric] ?? 0), 1);
  return <div className="case-chart" role="img" aria-label={`Per-task ${unit}. Values are also listed beside each bar.`}>
    {cases.map(item => {
      const value = item[metric];
      return <div className="chart-row" key={item.id}>
        <span>{item.title}</span><div className="chart-track"><div className="chart-fill" style={{ width: `${value == null ? 0 : value / max * 100}%` }} /></div><strong>{format(value)}</strong>
      </div>;
    })}
    <div className="chart-scale"><span>0</span><span>{format(max)}</span></div>
  </div>;
}

export function BenchmarkReport({ report, comparison }: { report: Report; comparison: Report | null }) {
  const rootRef = useRef<HTMLElement>(null);
  useEffect(() => {
    let states: Array<[HTMLDetailsElement, boolean]> = [];
    const beforePrint = () => {
      states = Array.from(rootRef.current?.querySelectorAll("details") || []).map(element => [element, element.open]);
      states.forEach(([element]) => { element.open = true; });
    };
    const afterPrint = () => { states.forEach(([element, open]) => { element.open = open; }); states = []; };
    window.addEventListener("beforeprint", beforePrint);
    window.addEventListener("afterprint", afterPrint);
    return () => { window.removeEventListener("beforeprint", beforePrint); window.removeEventListener("afterprint", afterPrint); };
  }, []);
  const { run, summary, results } = report;
  const image = run.profile === "image";
  const speedUnit = throughputUnit(summary.token_basis);
  const fullyComplete = summary.total > 0 && summary.completed === summary.total && run.status === "done";
  const percentage = summary.total ? Math.round(summary.completed / summary.total * 100) : 0;
  const comparisonMetric = image ? "median_total_ms" : "median_ttft_ms";
  const current = summary[comparisonMetric];
  const previous = comparison?.summary[comparisonMetric];
  const improvement = current != null && previous != null && previous > 0 ? (previous - current) / previous * 100 : null;
  return <article ref={rootRef} className="benchmark-report" aria-label="Benchmark report">
    <header className="report-heading">
      <div><span className="report-kicker">Performance report · Run {run.id}</span><h2>{run.model}</h2><p>{run.endpoint_name || "Deleted server"} · {profileName(run.profile)} · {new Date(run.started_at).toLocaleString()}</p></div>
      <span className={`report-status ${fullyComplete ? "complete" : "incomplete"}`}><IconCheck size={16} />{fullyComplete ? "Completed" : run.status === "running" ? "In progress" : "Needs attention"}</span>
    </header>
    {run.error ? <p className="fault" role="alert">{run.error}</p> : null}
    <div className="report-metrics">
      <div className="metric-tile"><IconClock size={22} /><span>{image ? "Median image time" : "Time to first response"}</span><strong>{duration(image ? summary.median_total_ms : summary.median_ttft_ms)}</strong><small>Median of successful samples · lower is better</small></div>
      <div className="metric-tile"><IconBolt size={22} /><span>{image ? "Measured generation time" : "Effective throughput"}</span><strong>{image ? duration(summary.measured_ms) : rate(summary.median_tokens_per_second)}</strong><small>{image ? "Includes failed attempts; excludes warmup" : `${speedUnit} · includes the initial wait`}</small></div>
      <div className="metric-tile completion-tile"><div className="completion-ring" style={{ background: `conic-gradient(var(--signal) ${percentage}%, #e1e9ed 0)` }} aria-hidden="true"><span>{percentage}%</span></div><div><span>Samples completed</span><strong>{summary.completed}<em> / {summary.total}</em></strong><small>{summary.failed ? `${summary.failed} failed` : "Successful responses, not a quality score"}</small></div></div>
    </div>
    {comparison ? <section className="report-comparison">
      <div><span className="report-kicker">Compared with run {comparison.run.id}</span><h3>{comparison.run.model}</h3><p>Same suite, tasks, repeats, warmup, and measurement basis.</p></div>
      <div className="comparison-delta">{improvement != null ? <><strong>{improvement >= 0 ? <IconArrowDown size={24} /> : <IconArrowUp size={24} />}{Math.abs(improvement).toFixed(1)}%</strong><span>{image ? "image generation" : "first response"} {improvement >= 0 ? "faster" : "slower"}</span></> : <span>No comparable timing available</span>}</div>
      <div className="comparison-values"><span>This run <strong>{duration(current)}</strong></span><span>Comparison <strong>{duration(previous)}</strong></span></div>
    </section> : null}
    <div className="report-chart-grid">
      <section className="report-panel"><div className="section-title"><h3>{image ? "Time per image" : "Response time by task"}</h3><span className="quiet">Lower is better</span></div><p className="quiet">Median {image ? "total time" : "time to first visible text"}, successful samples.</p><CaseChart cases={summary.cases} metric={image ? "median_total_ms" : "median_ttft_ms"} unit="response time" format={duration} /></section>
      <section className="report-panel"><div className="section-title"><h3>{image ? "Run conditions" : "Throughput by task"}</h3>{!image ? <span className="quiet">Higher is better</span> : null}</div>
        {image ? <dl className="condition-list"><div><dt>Requested size</dt><dd>512 × 512</dd></div><div><dt>Images per request</dt><dd>1</dd></div><div><dt>Repeats</dt><dd>{run.repeat_count}</dd></div><div><dt>Discarded warmup</dt><dd>{run.warmup ? "On" : "Off"}</dd></div></dl> : <><p className="quiet">{speedUnit}. Output count divided by full request duration.</p><CaseChart cases={summary.cases} metric="median_tokens_per_second" unit={speedUnit} format={rate} /></>}
      </section>
    </div>
    <section className="report-outputs"><div className="section-title"><h3>See what the model made</h3><span className="quiet">{results.length} saved samples</span></div><p className="quiet">Inspect the output alongside the timing. Code is shown as text and is never executed.</p>
      {results.length === 0 ? <p className="quiet">No samples were saved. Check the run error and try again.</p> : null}
      {results.map((row, index) => {
        const Icon = iconFor(row.kind);
        const title = summary.cases.find(item => item.id === row.case_id)?.title || row.case_id;
        return <details className="result-sample" key={row.id} open={index === 0 || row.kind === "image" || !!row.error}>
          <summary><Icon size={19} /><strong>{title}</strong><span>Repeat {row.repeat_index + 1}</span><span className={row.error ? "result-failed" : "result-time"}>{row.error ? "Failed" : duration(row.total_ms)}</span></summary>
          <div className="sample-body">{row.error ? <p className="fault">{row.error}</p> : row.image_url ? <img className="generated-output" src={row.image_url} alt={`Generated image for ${title}, repeat ${row.repeat_index + 1}`} /> : <pre className={row.kind === "code" ? "code-output" : "text-output"}><code>{row.output_text || row.output_preview || "No text output saved."}</code></pre>}
            <div className="sample-measurements"><span>Total: <strong>{duration(row.total_ms)}</strong></span>{row.kind !== "image" ? <><span>First response: <strong>{duration(row.ttft_ms)}</strong></span><span>Throughput: <strong>{rate(row.tokens_per_second)} {throughputUnit(row.token_basis || "unknown")}</strong></span></> : null}</div>
          </div>
        </details>;
      })}
    </section>
    <footer className="report-method"><strong>How to read this report</strong><p>Suite {run.suite_version} · {run.repeat_count} repeat{run.repeat_count === 1 ? "" : "s"} per task · Warmup {run.warmup ? "discarded" : "off"}. Single-user measurements for this server and tokenizer. Medians exclude failed samples. Speed does not measure correctness or image quality. {summary.token_basis === "chunks" ? "This server omitted token usage; throughput uses streamed chunks as an estimate." : ""} {summary.token_basis === "mixed" || summary.token_basis === "unknown" ? "Token-count basis is mixed or unknown; interpret throughput cautiously." : ""} Output previews retain up to 32,000 characters.</p></footer>
  </article>;
}
