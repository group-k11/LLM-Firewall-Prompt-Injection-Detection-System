"use client";

import { Shield, Database, Zap } from "lucide-react";
import { type LLMStatus } from "@/services/api";

interface HeaderProps {
  firewallEnabled: boolean;
  setFirewallEnabled: (val: boolean | ((v: boolean) => boolean)) => void;
  llmStatus: LLMStatus | null;
}

// Provider display metadata
const PROVIDER_META: Record<string, { label: string; color: string }> = {
  groq:       { label: "GROQ",       color: "var(--safe)" },
  openrouter: { label: "OPENROUTER", color: "#bf5af2"     },
  ollama:     { label: "OLLAMA",     color: "#ff9500"     },
  none:       { label: "OFFLINE",    color: "var(--malicious)" },
};

export default function Header({ firewallEnabled, setFirewallEnabled, llmStatus }: HeaderProps) {
  const activeProvider = llmStatus?.active_provider ?? "none";
  const isActive = activeProvider !== "none";
  const providerMeta = PROVIDER_META[activeProvider] ?? PROVIDER_META["none"];

  // Pick the model name from the correct provider
  const modelName =
    activeProvider === "groq"       ? llmStatus?.groq?.model :
    activeProvider === "openrouter" ? llmStatus?.openrouter?.model :
    activeProvider === "ollama"     ? llmStatus?.ollama?.model :
    null;

  return (
    <header
      className="glass-panel"
      style={{ padding: "16px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}
    >
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            background: "var(--accent-bg)",
            color: "var(--accent)",
            padding: "8px",
            borderRadius: "8px",
            boxShadow: "var(--cyan-glow)",
          }}
        >
          <Shield size={24} />
        </div>
        <div>
          <h1 className="mono" style={{ fontSize: "18px", fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }}>
            <a href="/" style={{ color: "var(--text-primary)", textDecoration: "none" }}>
              LLM_FIREWALL
            </a>
          </h1>
          <p
            className="mono"
            style={{
              fontSize: "11px",
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "1px",
              margin: 0,
            }}
          >
            v2.0 · Prompt Injection Detection
          </p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
        {/* LLM Provider Indicator */}
        <div className="mono" style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          {activeProvider === "groq" ? (
            <Zap size={16} color={providerMeta.color} />
          ) : (
            <Database size={16} color={isActive ? providerMeta.color : "var(--text-muted)"} />
          )}
          <span style={{ color: "var(--text-secondary)" }}>
            LLM:{" "}
            <strong style={{ color: providerMeta.color }}>{providerMeta.label}</strong>
          </span>
          {isActive && modelName && (
            <span
              className="badge badge-neutral"
              style={{
                fontSize: "10px",
                marginLeft: "4px",
                background: "rgba(255,255,255,0.05)",
                border: `1px solid ${providerMeta.color}33`,
                color: providerMeta.color,
              }}
            >
              {modelName}
            </span>
          )}
          {!isActive && (
            <span className="badge badge-neutral" style={{ fontSize: "10px", color: "var(--malicious)" }}>
              OFFLINE
            </span>
          )}
        </div>

        <div style={{ width: "1px", height: "24px", background: "var(--card-border)" }} />

        {/* Firewall Toggle */}
        <div className="toggle-wrapper mono">
          <span
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: firewallEnabled ? "var(--safe)" : "var(--malicious)",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {firewallEnabled && (
              <div className="pulse-dot" style={{ background: "var(--safe)", animation: "pulse-cyan 2s infinite" }} />
            )}
            {!firewallEnabled && <div className="pulse-dot" />}
            FIREWALL {firewallEnabled ? "ON" : "OFF"}
          </span>
          <div
            className="toggle-switch"
            data-on={firewallEnabled}
            role="switch"
            aria-checked={firewallEnabled}
            tabIndex={0}
            onClick={() => setFirewallEnabled((v) => !v)}
            onKeyDown={(e) => e.key === " " && setFirewallEnabled((v) => !v)}
          >
            <div className="toggle-thumb" />
          </div>
        </div>
      </div>
    </header>
  );
}
