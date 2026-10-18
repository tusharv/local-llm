import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, selectedEndpointId, type Endpoint } from "./api";
import { Benchmarks } from "./pages/Benchmarks";
import { Chat } from "./pages/Chat";
import { Models } from "./pages/Models";
import { Setup } from "./pages/Setup";
import { IconAdjustments, IconMessageCircle, IconCpu, IconChartBar, IconShieldLock, IconServer } from "@tabler/icons-react";
import "./styles.css";

const PAGES = [
  { hash: "#/setup", label: "Setup", icon: IconAdjustments, page: Setup },
  { hash: "#/chat", label: "Chat", icon: IconMessageCircle, page: Chat },
  { hash: "#/models", label: "Models", icon: IconCpu, page: Models },
  { hash: "#/benchmarks", label: "Benchmarks", icon: IconChartBar, page: Benchmarks },
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
  const current = PAGES.find((item) => item.hash === hash || (item.hash === "#/chat" && hash.startsWith("#/chat/"))) ?? PAGES[0];
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
          <strong className="studio-wordmark"><img src="/brand/studio-logo-professional.webp" alt="" />Studio<span className="brand-dot">.</span></strong>
          <span>Your local AI workspace</span>
        </div>
        <nav aria-label="Main navigation">
          {PAGES.map((item) => (
            <a key={item.hash} href={item.hash} aria-current={item.hash === current.hash ? "page" : undefined}>
              <item.icon size={20} stroke={1.7} />{item.label}
            </a>
          ))}
        </nav>
        <div className="rail-note"><IconShieldLock size={22} /><strong>Private by design</strong><p>Conversations are saved on this computer. You choose the server.</p></div>
      </aside>
      <main className="stage">
        <div className="strip">
          <span><IconShieldLock size={16} /> Local workspace</span>
          <span><IconServer size={16} /> {endpointName}</span>
        </div>
        <section className={`plate${current.hash === "#/chat" ? " chat-plate" : ""}`}>
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
