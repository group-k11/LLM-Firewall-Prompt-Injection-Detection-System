"use client";

import { motion } from "framer-motion";
import { type CheckPromptResult } from "@/services/api";
import { ShieldAlert, ShieldCheck, AlertTriangle, Cpu, Layers, Code2 } from "lucide-react";

interface ResultPanelProps {
  result: CheckPromptResult | null;
}

function ScoreBar({ label, value, colorVar }: { label: string; value: number; colorVar: string }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ marginBottom: "12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px", color: "var(--text-secondary)" }}>
        <span>{label}</span>
        <span className="mono">{pct}%</span>
      </div>
      <div className="score-track">
        <motion.div
          className="score-fill"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{ background: `var(${colorVar})` }}
        />
      </div>
    </div>
  );
}

const LAYER_ICONS: Record<string, string> = {
  rule_engine:          "📋",
  svm_classifier:       "🔢",
  transformer:          "🧠",
  encoding_normalizer:  "🔣",
  nested_detector:      "📦",
  session_tracker:      "🔄",
};

const CATEGORY_DISPLAY: Record<string, { label: string; color: string }> = {
  instruction_override:  { label: "Instruction Override",   color: "#ff3b3b" },
  jailbreak:             { label: "Jailbreak (DAN)",        color: "#ff6b6b" },
  prompt_extraction:     { label: "Prompt Extraction",      color: "#ff9500" },
  privilege_escalation:  { label: "Privilege Escalation",   color: "#ffcc00" },
  safety_bypass:         { label: "Safety Bypass",          color: "#ff3b3b" },
  roleplay_attack:       { label: "Roleplay Attack",        color: "#bf5af2" },
  encoding_attack:       { label: "Encoding Obfuscation",   color: "var(--cyan)" },
  nested_attack:         { label: "Nested Injection",       color: "#30d158" },
  hypothetical:          { label: "Hypothetical Bypass",    color: "#ff9f0a" },
  token_injection:       { label: "Token Injection",        color: "#ff453a" },
  multi_turn_escalation: { label: "Multi-Turn Escalation",  color: "#ff2d55" },
  unknown_injection:     { label: "Unknown Injection",      color: "#8e8e93" },
  none:                  { label: "Safe",                   color: "var(--safe)" },
};

export default function ResultPanel({ result }: ResultPanelProps) {
  if (!result) {
    return (
      <div className="glass-panel" style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "400px", color: "var(--text-muted)" }}>
        <div style={{ textAlign: "center" }}>
          <ShieldCheck size={48} style={{ opacity: 0.2, margin: "0 auto 16px" }} />
          <p className="mono">Awaiting prompt analysis…</p>
        </div>
      </div>
    );
  }

  const isBlocked    = result.risk_level === "malicious";
  const isSuspicious = result.risk_level === "suspicious";
  const riskColor    = isBlocked ? "--malicious" : isSuspicious ? "--suspicious" : "--safe";
  const catInfo      = CATEGORY_DISPLAY[result.attack_category] ?? { label: result.attack_category, color: "var(--text-muted)" };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`glass-panel ${isBlocked ? "glow-red" : "glow-cyan"}`}
      style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px", height: "100%", overflowY: "auto" }}
    >
      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 className="heading-syne" style={{ fontSize: "18px", margin: "0 0 4px", color: isBlocked ? "var(--red)" : "var(--cyan)" }}>
            Analysis Result
          </h2>
          <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {result.processing_time_ms.toFixed(0)}ms · {result.firewall_active ? "Firewall ON" : "Bypass Mode"}
          </div>
        </div>
        <div className={`badge badge-${result.risk_level}`} style={{ padding: "6px 14px", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
          {isBlocked ? <ShieldAlert size={16} /> : isSuspicious ? <AlertTriangle size={16} /> : <ShieldCheck size={16} />}
          {result.risk_level.toUpperCase()}
        </div>
      </div>

      {/* ── Attack category badge ── */}
      {result.attack_category && result.attack_category !== "none" && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="mono" style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Category:
          </span>
          <span
            className="mono"
            style={{
              fontSize: "11px",
              padding: "3px 10px",
              borderRadius: "100px",
              border: `1px solid ${catInfo.color}44`,
              color: catInfo.color,
              background: `${catInfo.color}11`,
              fontWeight: 700,
            }}
          >
            {catInfo.label}
          </span>
        </div>
      )}

      {/* ── Block / Warning message ── */}
      {(result.warning || result.message) && (
        <div
          className="mono"
          style={{
            padding: "14px 16px",
            background: `var(${riskColor}-bg)`,
            border: `1px solid rgba(255,59,59,0.25)`,
            borderRadius: "var(--radius-sm)",
            color: `var(${riskColor})`,
            fontSize: "13px",
            display: "flex",
            gap: "12px",
            alignItems: "flex-start",
            boxShadow: isBlocked ? "var(--red-glow)" : "none",
          }}
        >
          <div style={{ marginTop: "2px", flexShrink: 0 }}>
            {isBlocked ? <ShieldAlert size={18} /> : <AlertTriangle size={18} />}
          </div>
          <div>
            <div style={{ fontWeight: 700, marginBottom: "4px" }}>
              {isBlocked ? "🚫 Prompt Blocked" : "⚠ Suspicious — Sanitized"}
            </div>
            <div style={{ opacity: 0.85 }}>{result.message || result.warning}</div>
          </div>
        </div>
      )}

      {/* ── Detection Scores ── */}
      <div>
        <h3 className="mono" style={{ fontSize: "13px", color: "var(--text-primary)", marginBottom: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
          <Cpu size={14} color="var(--cyan)" /> Detection Scores
        </h3>
        <ScoreBar label="SVM / TF-IDF"             value={result.svm_score}         colorVar="--cyan" />
        <ScoreBar label="Transformer (MiniLM)"      value={result.transformer_score} colorVar="--cyan" />
        {result.encoding_anomaly !== undefined && (
          <ScoreBar label="Encoding Anomaly"        value={result.encoding_anomaly}  colorVar="--suspicious" />
        )}
        {result.nested_score !== undefined && result.nested_score > 0 && (
          <ScoreBar label="Nested Injection Score"  value={result.nested_score}      colorVar="--suspicious" />
        )}
        {result.session_boost !== undefined && result.session_boost > 0 && (
          <ScoreBar label={`Session Escalation Boost`} value={result.session_boost} colorVar="--malicious" />
        )}
        <ScoreBar label="Final Risk Score"          value={result.combined_score}    colorVar={riskColor} />
      </div>

      {/* ── Triggered Detection Layers ── */}
      {result.triggered_layers && result.triggered_layers.length > 0 && (
        <div>
          <h3 className="mono" style={{ fontSize: "13px", color: "var(--text-primary)", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
            <Layers size={14} color="var(--cyan)" /> Triggered Layers
          </h3>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {result.triggered_layers.map((layer, idx) => (
              <span key={idx} className="mono" style={{
                background: "rgba(0,245,255,0.08)",
                color: "var(--cyan)",
                border: "1px solid rgba(0,245,255,0.2)",
                padding: "3px 10px",
                borderRadius: "100px",
                fontSize: "11px",
              }}>
                {LAYER_ICONS[layer] ?? "•"} {layer.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Triggered Rules ── */}
      {result.triggered_rules && result.triggered_rules.length > 0 && (
        <div>
          <h3 className="mono" style={{ fontSize: "13px", color: "var(--text-primary)", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
            <Code2 size={14} color="var(--red)" /> Matched Patterns
          </h3>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {result.triggered_rules.map((rule, idx) => (
              <span key={idx} className="mono" style={{
                background: "var(--red-bg)",
                color: "var(--red)",
                border: "1px solid rgba(255,59,59,0.3)",
                padding: "3px 10px",
                borderRadius: "100px",
                fontSize: "11px",
                fontWeight: 600,
              }}>
                {rule}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Reason ── */}
      {result.reason && (
        <div className="mono" style={{ fontSize: "11px", color: "var(--text-muted)", padding: "10px 12px", background: "rgba(255,255,255,0.02)", borderRadius: "6px", border: "1px solid var(--card-border)" }}>
          <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>Reason: </span>
          {result.reason}
        </div>
      )}

      {/* ── LLM Output ── */}
      {result.llm_response && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <h3 className="mono" style={{ fontSize: "13px", color: "var(--cyan)", margin: 0 }}>
              &gt; LLM Output
            </h3>
            {result.provider && (
              <span className="mono" style={{ fontSize: "10px", background: "rgba(255,255,255,0.05)", color: "var(--text-muted)", padding: "2px 8px", borderRadius: "100px", border: "1px solid var(--card-border)" }}>
                {result.provider.toUpperCase()}
              </span>
            )}
          </div>
          <div className="textarea-glass" style={{
            flex: 1,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            minHeight: "100px",
            color: "var(--text-secondary)",
            fontSize: "13px",
          }}>
            {result.llm_response}
          </div>
        </div>
      )}
    </motion.div>
  );
}
