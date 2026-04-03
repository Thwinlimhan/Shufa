import { useEffect, useState } from "react";
import { apiPost } from "./api/client";
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
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    return (window.localStorage.getItem("workbench_theme") as "dark" | "light") || "dark";
  });

  useEffect(() => {
    apiPost<{ role: string; display_name: string }>("/auth/login", { role })
      .then((user) => {
        setIdentity(user.display_name);
      })
      .catch(() => {
        setIdentity("Unknown");
      });
  }, [role]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("workbench_theme", theme);
  }, [theme]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.ctrlKey) {
        if (event.key === "1") setTab("health");
        if (event.key === "2") setTab("strategies");
        if (event.key === "3") setTab("paper");
        if (event.key === "4") setTab("execution");
        if (event.key === "5") setTab("settings");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

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
          <button className="secondary-button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            Theme: {theme}
          </button>
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
        <div className="muted" style={{ marginTop: "1rem", fontSize: "0.82rem" }}>
          Shortcuts: `Ctrl+1..5` tabs, `Alt+B` backtest, `Alt+R` paper cycle, `Alt+A` approve.
        </div>
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
