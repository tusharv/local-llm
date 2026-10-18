import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  api,
  selectEndpoint,
  selectedEndpointId,
  streamSse,
  type ChatMessage,
  type Conversation,
  type Endpoint,
  type ModelRow,
} from "../api";

type LocalSession = { name: string; host: string };

function Mark() {
  return (
    <svg className="mark-svg" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#314850" />
      <circle cx="16" cy="16" r="4" fill="#e6a317" />
      <circle cx="16" cy="16" r="8.5" fill="none" stroke="#e6a317" strokeOpacity="0.5" strokeWidth="1.5" />
    </svg>
  );
}

function initials(name: string): string {
  const parts = name.split(/[.\s_-]+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "L";
}

function Markdown({ text }: { text: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (!href || href.trim().toLowerCase().startsWith("javascript:")) return <span>{children}</span>;
            return <a href={href} rel="noreferrer noopener" target="_blank">{children}</a>;
          },
          img: ({ alt, src }) => <span className="quiet">{alt || "Image"}{src ? ` (${src})` : ""}</span>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

function patchAssistant(current: ChatMessage[], patch: (message: ChatMessage) => ChatMessage): ChatMessage[] {
  const next = current.slice();
  const last = next[next.length - 1];
  if (last && last.role === "assistant") next[next.length - 1] = patch(last);
  return next;
}

export function Chat() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [endpointId, setEndpointId] = useState<number | null>(selectedEndpointId());
  const [models, setModels] = useState<ModelRow[]>([]);
  const [model, setModel] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [session, setSession] = useState<LocalSession>({ name: "Local", host: "this computer" });
  const [name, setName] = useState("Local");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:11434/v1");
  const [kind, setKind] = useState<"openai" | "ollama">("ollama");
  const [confirmed, setConfirmed] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const threadLocked = conversationId !== null;

  const vision = models.find((item) => item.id === model)?.vision ?? false;
  const endpoint = endpoints.find((item) => item.id === endpointId);

  async function loadEndpoints() {
    const data = await api<{ endpoints: Endpoint[] }>("/api/endpoints");
    setEndpoints(data.endpoints);
    const chosen = data.endpoints.find((item) => item.id === selectedEndpointId()) ?? data.endpoints[0];
    if (chosen) {
      setEndpointId(chosen.id);
      selectEndpoint(chosen.id);
    }
  }

  async function loadConversations() {
    const data = await api<{ conversations: Conversation[] }>("/api/conversations");
    setConversations(data.conversations);
  }

  useEffect(() => {
    loadEndpoints().then(loadConversations).catch((reason: Error) => setError(reason.message));
    api<LocalSession>("/api/whoami")
      .then((data) => setSession({ name: data.name || "Local", host: data.host || "this computer" }))
      .catch(() => setSession({ name: "Local", host: "this computer" }));
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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, busy]);

  async function openConversation(conversation: Conversation) {
    const data = await api<{ messages: ChatMessage[] }>(`/api/conversations/${conversation.id}`);
    setConversationId(conversation.id);
    setMessages(data.messages);
    setEndpointId(conversation.endpoint_id);
    selectEndpoint(conversation.endpoint_id);
    setModel(conversation.model);
    setError("");
    setNavOpen(false);
  }

  function startThread() {
    setConversationId(null);
    setMessages([]);
    setDraft("");
    setImage(null);
    setError("");
    setNavOpen(false);
  }

  async function saveFirst(event: FormEvent) {
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
      setEndpointId(saved.id);
      await loadEndpoints();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save that server.");
    }
  }

  async function ensureConversation(): Promise<number> {
    if (conversationId) return conversationId;
    if (!endpointId || !model.trim()) throw new Error("Choose a server and a model before sending.");
    const created = await api<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ endpoint_id: endpointId, model: model.trim() }),
    });
    setConversationId(created.id);
    return created.id;
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const content = draft.trim();
    const file = image;
    if (!content && !file) return;
    setError("");
    setBusy(true);
    setDraft("");
    setImage(null);
    const localImage = file ? URL.createObjectURL(file) : undefined;
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", content, error: null, created_at: "", image_url: localImage },
      { id: Date.now() + 1, role: "assistant", content: "", thinking: "", error: null, created_at: "" },
    ]);
    try {
      const id = await ensureConversation();
      let body: BodyInit;
      if (file) {
        const form = new FormData();
        form.set("conversation_id", String(id));
        form.set("content", content);
        form.set("image", file);
        body = form;
      } else {
        body = JSON.stringify({ conversation_id: id, content });
      }
      await streamSse("/api/chat", { method: "POST", body }, (eventData) => {
        if (typeof eventData.thinking === "string") {
          const piece = eventData.thinking;
          setMessages((current) => patchAssistant(current, (last) => ({ ...last, thinking: (last.thinking || "") + piece })));
        }
        if (typeof eventData.delta === "string") {
          const piece = eventData.delta;
          setMessages((current) => patchAssistant(current, (last) => ({ ...last, content: last.content + piece })));
        }
        if (typeof eventData.error === "string") {
          const message = eventData.error;
          setMessages((current) => patchAssistant(current, (last) => ({ ...last, error: message })));
        }
      });
      const data = await api<{ messages: ChatMessage[] }>(`/api/conversations/${id}`);
      setMessages(data.messages);
      await loadConversations();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The reply failed.");
    } finally {
      setBusy(false);
    }
  }

  function onDraftKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  async function removeConversation(id: number) {
    await api(`/api/conversations/${id}`, { method: "DELETE" });
    if (conversationId === id) {
      setConversationId(null);
      setMessages([]);
    }
    await loadConversations();
  }

  const ready = endpoints.length > 0;

  return (
    <div className={`chat-app${navOpen ? " nav-open" : ""}`}>
      <aside className="chat-side">
        <a className="brand" href="#/chat">
          <Mark />
          <span>
            <strong>Studio</strong>
            <em>Local LLM Studio</em>
          </span>
        </a>
        <p className="disclaimer">
          Prompts stay on the server you saved. Studio does not send them to a public cloud. Replies can be wrong.
        </p>
        <button type="button" className="new-thread" onClick={startThread} disabled={!ready || busy}>
          New chat
        </button>
        <div className="thread-list" aria-label="Threads">
          {conversations.length === 0 ? <p className="side-quiet">No threads yet.</p> : null}
          {conversations.map((conversation) => (
            <div className="thread-row" key={conversation.id}>
              <button
                type="button"
                className="thread"
                aria-current={conversation.id === conversationId ? "true" : undefined}
                onClick={() => openConversation(conversation)}
              >
                {conversation.title}
              </button>
              <button
                type="button"
                className="thread-delete"
                aria-label={`Delete ${conversation.title}`}
                onClick={() => removeConversation(conversation.id)}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
        <div className="session">
          <span className="avatar" aria-hidden="true">{initials(session.name)}</span>
          <span>
            <strong>{session.name}</strong>
            <em>Local session · {session.host}</em>
          </span>
        </div>
      </aside>
      <section className="chat-main">
        <header className="chat-top">
          <div className="chat-top-start">
            <button type="button" className="threads-toggle" onClick={() => setNavOpen((open) => !open)}>
              {navOpen ? "Close" : "Threads"}
            </button>
            <span className="brand-inline">
              <Mark />
              <strong>Studio</strong>
            </span>
          </div>
          {ready ? (
            <div className="model-bar">
              <label>
                Server
                <select
                  value={endpointId ?? ""}
                  disabled={threadLocked || busy}
                  onChange={(event) => {
                    const id = Number(event.target.value);
                    setEndpointId(id);
                    selectEndpoint(id);
                    setModel("");
                  }}
                >
                  {endpoints.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Model
                <input
                  value={model}
                  disabled={threadLocked || busy}
                  onChange={(event) => setModel(event.target.value)}
                  list="model-ids"
                  placeholder="Model name"
                />
              </label>
              <datalist id="model-ids">
                {models.map((item) => <option key={item.id} value={item.id} />)}
              </datalist>
            </div>
          ) : <span className="quiet">No server saved</span>}
          <nav className="chat-nav" aria-label="Studio">
            <a href="#/setup">Setup</a>
            <a href="#/models">Models</a>
            <a href="#/benchmarks">Benchmarks</a>
          </nav>
        </header>
        <div className="transcript-scroll">
          <div className="transcript-inner">
            {!ready ? (
              <form className="card stack welcome-card" onSubmit={saveFirst}>
                <h1>Save a local server</h1>
                <p>Chat starts after a server on this machine is saved. Nothing is sent to a public cloud.</p>
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
              </form>
            ) : null}
            {ready && messages.length === 0 ? (
              <div className="welcome">
                <Mark />
                <h1>What should we work on?</h1>
                <p>
                  {endpoint ? endpoint.name : "Local server"}
                  {model ? ` · ${model}` : ""}. The reply streams in Markdown. Thinking stays folded.
                </p>
              </div>
            ) : null}
            {messages.map((message, index) => (
              <Turn
                key={message.id}
                message={message}
                live={busy && index === messages.length - 1 && message.role === "assistant"}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        </div>
        {ready ? (
          <div className="composer-wrap">
            <form className="composer-inner" onSubmit={send}>
              <div className="composer-bar">
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={onDraftKey}
                  placeholder="Message the local model"
                  rows={1}
                  disabled={busy}
                />
                <div className="composer-actions">
                  <label className={`attach${vision ? "" : " is-disabled"}`}>
                    Attach image
                    <input
                      key={messages.length}
                      type="file"
                      accept="image/png,image/jpeg,image/gif,image/webp"
                      disabled={!vision || busy}
                      onChange={(event) => setImage(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <button type="submit" className="send" disabled={busy || (!draft.trim() && !image)}>
                    Send
                  </button>
                </div>
              </div>
              {image ? <p className="fine-print">Image attached: {image.name}</p> : null}
              {!vision ? <p className="fine-print">Image attach stays off until this model can see images.</p> : null}
              {error ? <p className="fault">{error}</p> : null}
              <p className="fine-print">
                Replies stream from {model || "the selected model"} on {endpoint?.name ?? "your saved server"}. They can be wrong.
              </p>
            </form>
          </div>
        ) : error ? <p className="fault composer-wrap">{error}</p> : null}
      </section>
    </div>
  );
}

function Turn({ message, live }: { message: ChatMessage; live: boolean }) {
  const waiting = live && !message.content && !message.thinking;
  return (
    <article className={`turn ${message.role}`}>
      <span className="turn-who">{message.role === "user" ? "You" : "Studio"}</span>
      {message.role === "assistant" && message.thinking ? (
        <details className="think">
          <summary>{live && !message.content ? "Thinking…" : "Thinking"}</summary>
          <Markdown text={message.thinking} />
        </details>
      ) : null}
      <div className="turn-body">
        {message.role === "assistant" ? (
          message.content ? <Markdown text={message.content} /> : null
        ) : (
          <p>{message.content}</p>
        )}
        {message.image_url ? <img src={message.image_url} alt="" /> : null}
        {waiting ? <p className="quiet">Waiting for the model…</p> : null}
        {live && message.content ? <span className="caret" aria-hidden="true" /> : null}
        {message.error ? <p className="fault">{message.error}</p> : null}
      </div>
    </article>
  );
}
