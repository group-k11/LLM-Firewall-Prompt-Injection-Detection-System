"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  checkPrompt,
  demoAttack,
  getLlmStatus,
  getStats,
  getLogs,
  type CheckPromptResult,
  type DemoResult,
  type Stats,
  type LogEntry,
  type LLMStatus,
} from "@/services/api";

// Components
import Header from "@/components/Header";
import StatsCard from "@/components/StatsCard";
import PromptInput from "@/components/PromptInput";
import ResultPanel from "@/components/ResultPanel";
import LogsTable from "@/components/LogsTable";
import DemoPanel from "@/components/DemoPanel";

import { ShieldCheck, ShieldAlert, AlertTriangle, Activity, Search, Zap, List } from "lucide-react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [firewallEnabled, setFirewallEnabled] = useState(true);
  const [activeTab, setActiveTab] = useState<"analyze" | "demo" | "logs">("analyze");

  const [result, setResult] = useState<CheckPromptResult | null>(null);
  const [demoResult, setDemoResult] = useState<DemoResult | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const logsTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Initial load
  useEffect(() => {
    async function load() {
      try {
        const [s, l, status] = await Promise.all([getStats(), getLogs(50), getLlmStatus()]);
        setStats(s);
        setLogs(l);
        setLlmStatus(status);
      } catch {
        // backend may not be running yet
      }
    }
    load();

    logsTimer.current = setInterval(async () => {
      try {
        const [s, l] = await Promise.all([getStats(), getLogs(50)]);
        setStats(s);
        setLogs(l);
      } catch { /* silent */ }
    }, 30_000);

    return () => { if (logsTimer.current) clearInterval(logsTimer.current); };
  }, []);

  const refreshData = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([getStats(), getLogs(50)]);
      setStats(s);
      setLogs(l);
    } catch { /* silent */ }
  }, []);

  const handleAnalyze = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await checkPrompt(prompt, firewallEnabled);
      setResult(res);
      await refreshData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Backend error. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setDemoResult(null);
    try {
      const res = await demoAttack(prompt);
      setDemoResult(res);
      await refreshData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Backend error. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Background Grid Overlay */}
      <div className="bg-grid" />

      <main className="main-content">
        <Header firewallEnabled={firewallEnabled} setFirewallEnabled={setFirewallEnabled} llmStatus={llmStatus} />

        {/* Top Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "24px" }}>
          <StatsCard title="Total Prompts" value={stats?.total_prompts || 0} icon={<Activity size={20} />} colorVar="--accent" delay={0.1} />
          <StatsCard title="Safe" value={stats?.safe_prompts || 0} icon={<ShieldCheck size={20} />} colorVar="--safe" delay={0.2} />
          <StatsCard title="Suspicious" value={stats?.suspicious_prompts || 0} icon={<AlertTriangle size={20} />} colorVar="--suspicious" delay={0.3} />
          <StatsCard title="Blocked Attacks" value={stats?.blocked_attacks || 0} icon={<ShieldAlert size={20} />} colorVar="--malicious" delay={0.4} />
        </div>

        {/* Tab Navigation */}
        <div style={{ display: "flex", gap: "12px", borderBottom: "1px solid var(--card-border)", paddingBottom: "16px" }}>
          <TabButton active={activeTab === "analyze"} onClick={() => setActiveTab("analyze")} icon={<Search size={16} />} label="Analyze Prompt" />
          <TabButton active={activeTab === "demo"} onClick={() => setActiveTab("demo")} icon={<Zap size={16} />} label="Demo Mode" />
          <TabButton active={activeTab === "logs"} onClick={() => setActiveTab("logs")} icon={<List size={16} />} label={`Logs (${logs.length})`} />
        </div>

        {/* Error Toast */}
        {error && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: "12px 16px", background: "var(--malicious-bg)", border: "1px solid var(--malicious)", borderRadius: "var(--radius-sm)", color: "var(--malicious)" }}>
            ❌ {error}
          </motion.div>
        )}

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === "analyze" && (
            <motion.div
              key="analyze"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", minHeight: "500px" }}
            >
              <PromptInput prompt={prompt} setPrompt={setPrompt} onAnalyze={handleAnalyze} loading={loading} firewallEnabled={firewallEnabled} />
              <ResultPanel result={result} />
            </motion.div>
          )}

          {activeTab === "demo" && (
            <motion.div
              key="demo"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{ display: "flex", flexDirection: "column", gap: "24px" }}
            >
              <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <h2 style={{ fontSize: "18px", margin: "0 0 8px", color: "var(--text-primary)" }}>Attack Demonstration</h2>
                  <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: 0 }}>
                    Enter a malicious prompt to see how the system handles it with and without the firewall.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                  <textarea
                    className="textarea-glass"
                    style={{ flex: 1, minHeight: "100px" }}
                    placeholder="e.g. Ignore all previous instructions and..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                  />
                  <button className="btn-primary" onClick={handleDemo} disabled={loading || !prompt.trim()} style={{ height: "100px", padding: "0 32px" }}>
                    {loading ? <Activity className="animate-spin" size={24} /> : <Zap size={24} />}
                    <span style={{ marginLeft: "8px" }}>{loading ? "Running..." : "Run Demo"}</span>
                  </button>
                </div>
              </div>

              <DemoPanel result={demoResult} />
            </motion.div>
          )}

          {activeTab === "logs" && (
            <motion.div
              key="logs"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <LogsTable logs={logs} onRefresh={refreshData} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: "8px", padding: "10px 20px",
        background: active ? "var(--card-border)" : "transparent",
        color: active ? "var(--text-primary)" : "var(--text-muted)",
        border: "none", borderRadius: "100px", fontSize: "14px", fontWeight: 600,
        cursor: "pointer", transition: "all 0.2s"
      }}
    >
      {icon}
      {label}
    </button>
  );
}
