import { useEffect, useState } from "react";
import { apiPost, setAuthToken } from "./api/client";
import { DataHealthPage } from "./pages/DataHealthPage";
import { ExecutionPage } from "./pages/ExecutionPage";
import { PaperPortfolioPage } from "./pages/PaperPortfolioPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StrategyRegistryPage } from "./pages/StrategyRegistryPage";

type TabKey = "health" | "strategies" | "paper" | "execution" | "settings";

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "health", label: "Data Health" },
  { key: "strategies", label: "Strategy Registry" },
  { key: "paper", label: "Paper Portfolio" },
  { key: "execution", label: "Execution" },
  { key: "settings", label: "Settings" }
];

export function App() {
  const [tab, setTab] = useState<TabKey>("health");
  const [role, setRole] = useState<string>("operator");
  const [identity, setIdentity] = useState<string>("Operator");

  useEffect(() => {
    apiPost<{ role: string; token: string; display_name: string }>("/auth/login", { role })
      .then((user) => {
        setAuthToken(user.token);
        setIdentity(user.display_name);
      })
      .catch(() => {
        setIdentity("Unknown");
      });
  }, [role]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">Crypto Workbench</div>
          <h1>Research. Falsify. Paper trade.</h1>
        </div>
        <div className="auth-panel">
          <div className="eyebrow">Operator</div>
          <div className="auth-name">{identity}</div>
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="viewer">viewer</option>
            <option value="operator">operator</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <nav className="nav">
          {tabs.map((item) => (
            <button
              key={item.key}
              className={item.key === tab ? "nav-item active" : "nav-item"}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        <div className="workspace">
          {tab === "health" && <DataHealthPage />}
          {tab === "strategies" && <StrategyRegistryPage />}
          {tab === "paper" && <PaperPortfolioPage />}
          {tab === "execution" && <ExecutionPage />}
          {tab === "settings" && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}
