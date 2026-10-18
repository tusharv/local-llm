import { useState } from "react";
import { IconRefresh, IconExternalLink } from "@tabler/icons-react";
import type { Endpoint } from "../api";

export function ServerRecovery({ endpoint, error, onRetry }: { endpoint: Endpoint; error?: string; onRetry: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [retryError, setRetryError] = useState("");
  const remote = !["127.0.0.1", "localhost", "[::1]"].includes(new URL(endpoint.base_url).hostname);
  const ollama = endpoint.kind === "ollama";
  async function retry() {
    setBusy(true); setRetryError("");
    try { await onRetry(); } catch (reason) { setRetryError(reason instanceof Error ? reason.message : "Could not check the connection."); }
    finally { setBusy(false); }
  }
  return <section className="server-recovery" aria-label="Server connection help">
    <h3>Let’s reconnect {endpoint.name}</h3>
    <p>We couldn’t reach this server. It may be stopped, or its address may have changed.</p>
    {remote ? <p>Follow these steps on the computer hosting <strong>{new URL(endpoint.base_url).hostname}</strong>. Check that it is reachable on your network.</p> : null}
    {ollama ? <ol>
      <li><strong>Install Ollama if needed.</strong> <a href="https://ollama.com/download" target="_blank" rel="noreferrer">Get Ollama <IconExternalLink size={14} /></a> Choose the installer for the server’s operating system.</li>
      <li><strong>Start the server.</strong> On macOS or Windows, open the Ollama app. For a command-line installation, run <code>ollama serve</code> in a terminal and leave it open.</li>
      <li><strong>Check the address.</strong> Ollama normally uses port 11434. For this computer, save <code>http://127.0.0.1:11434/v1</code> in Setup. If you configured another port, use that port instead.</li>
    </ol> : <ol>
      <li><strong>Open your model runtime.</strong> In LM Studio, load a model and start the server in the Developer tab. For another runtime, start its OpenAI-compatible API server.</li>
      <li><strong>Match the server address.</strong> Copy the runtime’s listening address into Setup, including its port and <code>/v1</code> suffix. Check any authentication settings too.</li>
    </ol>}
    <button type="button" className="secondary" disabled={busy} onClick={retry}><IconRefresh size={16} />{busy ? "Checking connection…" : "Check connection again"}</button>
    {(retryError || error) ? <details><summary>Connection details</summary><p className="mono">{retryError || error}</p></details> : null}
  </section>;
}
