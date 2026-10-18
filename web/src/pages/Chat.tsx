import { ChatPicker } from "../components/ChatPicker";
import { IconDownload, IconUpload, IconMessages, IconPlus, IconTrash, IconArrowUp, IconPaperclip, IconAdjustments, IconCpu, IconChartBar, IconCode, IconBulb, IconWriting, IconShieldLock } from "@tabler/icons-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ReadableOutput as Markdown } from "../components/ReadableOutput";
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
  return <img className="mark-svg" src="/brand/studio-logo-professional.webp" alt="" aria-hidden="true" />;
}

function initials(name: string): string {
  const parts = name.split(/[.\s_-]+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "L";
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
  const [navOpen, setNavOpen] = useState(() => window.innerWidth > 1000);
  const [historySearch, setHistorySearch] = useState("");
  const [session, setSession] = useState<LocalSession>({ name: "Local", host: "this computer" });
  const [name, setName] = useState("Local");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:11434/v1");
  const [kind, setKind] = useState<"openai" | "ollama">("ollama");
  const [confirmed, setConfirmed] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [transferBusy, setTransferBusy] = useState(false);
  const [transferMessage, setTransferMessage] = useState("");
  const routeVersion = useRef(0);
  const [routeLoading, setRouteLoading] = useState(false);
  const threadLocked = conversationId !== null;

  const vision = models.find((item) => item.id === model)?.vision ?? false;
  const endpoint = endpoints.find((item) => item.id === endpointId);

  async function loadEndpoints() {
    const data = await api<{ endpoints: Endpoint[] }>("/api/endpoints");
    setEndpoints(data.endpoints);
    const chosen = data.endpoints.find((item) => item.id === selectedEndpointId()) ?? data.endpoints[0];
    if (chosen && !window.location.hash.startsWith("#/chat/")) {
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

  useEffect(() => {
    async function loadRoute() {
      const version = ++routeVersion.current;
      const match = /^#\/chat\/([a-f0-9]+)$/.exec(window.location.hash);
      setBusy(false); setDraft(""); setImage(null); setError(""); setMessages([]); setConversationId(null);
      if (!match) { setRouteLoading(false); return; }
      setRouteLoading(true);
      try {
        const data = await api<Conversation & { messages: ChatMessage[] }>(`/api/conversations/${match[1]}`);
        if (version !== routeVersion.current) return;
        window.history.replaceState(null, "", `#/chat/${data.public_id}`);
        setConversationId(data.id); setMessages(data.messages);
        setEndpointId(data.endpoint_id); selectEndpoint(data.endpoint_id); setModel(data.model);
      } catch (reason) {
        if (version === routeVersion.current) setError(reason instanceof Error ? reason.message : "Could not open this conversation.");
      } finally { if (version === routeVersion.current) setRouteLoading(false); }
    }
    loadRoute();
    window.addEventListener("hashchange", loadRoute);
    return () => { ++routeVersion.current; window.removeEventListener("hashchange", loadRoute); };
  }, []);

  function openConversation(conversation: Conversation) {
    window.location.hash = `/chat/${conversation.public_id}`;
    if (window.innerWidth <= 1000) setNavOpen(false);
  }

  function startThread() {
    window.location.hash = "/chat";
    setConversationId(null); setMessages([]); setDraft(""); setImage(null); setError("");
    if (window.innerWidth <= 1000) setNavOpen(false);
  }

  async function importChat(file: File | undefined) {
    if (!file || !endpointId) return;
    setTransferBusy(true); setTransferMessage("");
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error("Choose a backup smaller than 20 MB.");
      const data = await api<{ conversations: Conversation[] }>(`/api/conversation-archive?endpoint_id=${endpointId}`, { method:"POST", body:await file.text() });
      await loadConversations();
      openConversation(data.conversations[0]);
      setTransferMessage(`Imported ${data.conversations.length} conversation(s).`);
    } catch (reason) { setTransferMessage(reason instanceof Error ? reason.message : "Import failed."); }
    finally { setTransferBusy(false); }
  }

  async function exportChat() {
    if (!conversationId) return;
    setTransferBusy(true); setTransferMessage("");
    try {
      const chat = await api<Conversation>(`/api/conversations/${conversationId}`);
      const data = await api<unknown>(`/api/conversation-archive/${chat.public_id}`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type:"application/json" }));
      const link = document.createElement("a"); link.href=url; link.download=`chat-${chat.public_id}.json`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) { setTransferMessage(reason instanceof Error ? reason.message : "Export failed."); }
    finally { setTransferBusy(false); }
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
    const version = routeVersion.current;
    const created = await api<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ endpoint_id: endpointId, model: model.trim() }),
    });
    if (version !== routeVersion.current) throw new Error("Conversation changed.");
    setConversationId(created.id);
    window.history.replaceState(null, "", `#/chat/${created.public_id}`);
    return created.id;
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (busy || routeLoading) return;
    const version = routeVersion.current;
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
      if (version !== routeVersion.current) return;
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
        if (version !== routeVersion.current) return;
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
      if (version !== routeVersion.current) return;
      setMessages(data.messages);
      await loadConversations();
    } catch (reason) {
      if (version === routeVersion.current) setError(reason instanceof Error ? reason.message : "The reply failed.");
    } finally {
      if (version === routeVersion.current) setBusy(false);
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
    if (conversationId === id) startThread();
    await loadConversations();
  }

  const ready = endpoints.length > 0;

  return (
    <div className={`chat-app${navOpen ? " nav-open" : ""}`}>
      <section className="chat-main">
        <header className="chat-top">
          <div className="chat-top-start">
            <button type="button" className="new-conversation" onClick={startThread} disabled={!ready || busy}><IconPlus size={17} /> New chat</button>
            <button type="button" className="threads-toggle" aria-label="Conversations" title="Conversations" aria-expanded={navOpen} aria-controls="conversation-panel" onClick={() => setNavOpen((open) => !open)}>
              <IconMessages size={20} aria-hidden="true" />
            </button>
          </div>
          <nav className="chat-nav" aria-label="Studio">
            <a href="#/setup"><IconAdjustments size={16} /> Setup</a>
            <a href="#/models"><IconCpu size={16} /> Models</a>
            <a href="#/benchmarks"><IconChartBar size={16} /> Benchmarks</a>
          </nav>
        </header>
        <div className="transcript-scroll">
          <div className="transcript-inner">
            {routeLoading ? <p role="status" className="quiet">Loading conversation…</p> : null}
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
                  Ask a question, untangle an idea, or build something.
                  Your chosen model runs on {endpoint?.name || "your local server"}.
                </p>
                <div className="prompt-grid">{[
                  { icon: IconBulb, title: "Explore an idea", text: "Help me brainstorm a small project I can build this weekend." },
                  { icon: IconCode, title: "Work through code", text: "Explain a programming concept with a simple example." },
                  { icon: IconWriting, title: "Find the right words", text: "Help me write a clear, friendly message." },
                ].map(({ icon: Icon, title, text }) => <button className="prompt-card" type="button" key={title} onClick={() => setDraft(text)}><Icon size={22} /><strong>{title}</strong><span>{text}</span></button>)}</div>
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
                  aria-label="Message"
                  placeholder="Ask anything, locally…"
                  rows={1}
                  disabled={busy || routeLoading}
                />
                <div className="composer-actions">
                  <label title="Attach image" className={`attach${vision ? "" : " is-disabled"}`}>
                    <IconPaperclip size={19} /> <span>Attach image</span>
                    <input
                      key={messages.length}
                      type="file"
                      accept="image/png,image/jpeg,image/gif,image/webp"
                      disabled={!vision || busy}
                      onChange={(event) => setImage(event.target.files?.[0] ?? null)}
                    />
                  </label>
          {ready ? (
            <div className="composer-models">
              <ChatPicker label="Server" value={String(endpointId ?? "")} options={endpoints.map(item => ({ value:String(item.id), label:item.name }))} disabled={threadLocked || busy} onChange={value => { const id = Number(value); setEndpointId(id); selectEndpoint(id); setModel(""); }} />
              <ChatPicker label="Model" value={model} options={models.map(item => ({ value:item.id, label:item.id }))} disabled={threadLocked || busy} allowCustom onChange={setModel} />
            </div>
          ) : null}
                  <button type="submit" className="send" disabled={busy || routeLoading || (!draft.trim() && !image)}>
                    <IconArrowUp size={20} /> <span>Send</span>
                  </button>
                </div>
              </div>
              {image ? <p className="fine-print">Image attached: {image.name}</p> : null}
              {!vision ? <p className="fine-print">Choose a model with image support to attach a picture.</p> : null}
              {error ? <p className="fault">{error}</p> : null}
              <p className="fine-print">
                <IconShieldLock size={13} /> Saved locally · Enter to send · Shift + Enter for a new line
              </p>
            </form>
          </div>
        ) : error ? <p className="fault composer-wrap">{error}</p> : null}
      </section>
      <section className="conversation-history" id="conversation-panel" aria-label="Conversation history" hidden={!navOpen}>
        <div className="history-heading"><div><h2>Your conversations</h2><p>Pick up where you left off. Saved on this computer.</p></div>
          <label>Find a conversation<input type="search" value={historySearch} onChange={event => setHistorySearch(event.target.value)} placeholder="Search by title…" /></label>
        </div>
        <div className="conversation-transfer">
          <button type="button" className="secondary" disabled={!conversationId || busy || transferBusy} onClick={exportChat}><IconDownload size={16} /> Export chat</button>
          <label className="button secondary import-chat"><IconUpload size={16} /> {transferBusy ? "Working…" : "Import chat"}<input type="file" accept=".json,application/json" aria-label="Import conversation backup" disabled={!endpointId || busy || transferBusy} onChange={event => { importChat(event.target.files?.[0]); event.target.value=""; }} /></label>
          <small>Imports create new chats using {endpoint?.name || "the selected server"}. Includes messages and attached images. Maximum 20 MB.</small>
          {transferMessage ? <p role="status">{transferMessage}</p> : null}
        </div>
        <div className="thread-list" aria-label="Threads">
          {conversations.length === 0 ? <p className="side-quiet">Your conversations will appear here. Start with a question below.</p> : null}
          {conversations.filter(conversation => conversation.title.toLowerCase().includes(historySearch.toLowerCase())).map((conversation) => (
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
                <IconTrash size={16} />
              </button>
            </div>
          ))}
        </div>
        {conversations.length > 0 && !conversations.some(conversation => conversation.title.toLowerCase().includes(historySearch.toLowerCase())) ? <p className="quiet">No matching conversations. Try another title.</p> : null}
        <div className="session">
          <span className="avatar" aria-hidden="true">{initials(session.name)}</span>
          <span>
            <strong>{session.name}</strong>
            <em>Local session · {session.host}</em>
          </span>
        </div>
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
