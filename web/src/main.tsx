import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, selectedEndpointId, type Endpoint } from "./api";
import { Benchmarks } from "./pages/Benchmarks";
import { Chat } from "./pages/Chat";
import { Models } from "./pages/Models";
import { Setup } from "./pages/Setup";
import "./styles.css";

const PAGES = [
  { hash: "#/setup", label: "Setup", page: Setup },
  { hash: "#/chat", label: "Chat", page: Chat },
  { hash: "#/models", label: "Models", page: Models },
  { hash: "#/benchmarks", label: "Benchmarks", page: Benchmarks },
];

function useHash(): string {
  const [hash, setHash] = useState(window.location.hash || "#/setup");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/setup");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

function Shell() {
  const hash = useHash();
  if (hash === "#/chat") return <Chat />;
  const current = PAGES.find((item) => item.hash === hash) ?? PAGES[0];
  const Page = current.page;
  const [endpointName, setEndpointName] = useState("No server saved");

  useEffect(() => {
    let cancel = false;
    const load = () => {
      const id = selectedEndpointId();
      if (!id) {
        setEndpointName("No server saved");
        return;
      }
      api<{ endpoints: Endpoint[] }>("/api/endpoints")
        .then((data) => {
          if (cancel) return;
          const match = data.endpoints.find((item) => item.id === id);
          setEndpointName(match ? match.name : "No server saved");
        })
        .catch(() => {
          if (!cancel) setEndpointName("Server list unavailable");
        });
    };
    load();
    window.addEventListener("studio-endpoint", load);
    return () => {
      cancel = true;
      window.removeEventListener("studio-endpoint", load);
    };
  }, [hash]);

  return (
    <div className="app">
      <aside className="rail">
        <div className="mark">
          <strong>Studio</strong>
          <span>Models on this machine</span>
        </div>
        <nav>
          {PAGES.map((item) => (
            <a key={item.hash} href={item.hash} aria-current={item.hash === current.hash ? "page" : undefined}>
              {item.label}
            </a>
          ))}
        </nav>
      </aside>
      <main className="stage">
        <div className="strip">
          <span><i className="lamp" aria-hidden="true" />127.0.0.1:8000</span>
          <span>{endpointName}</span>
        </div>
        <section className="plate">
          <Page />
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Shell />
  </StrictMode>,
);
