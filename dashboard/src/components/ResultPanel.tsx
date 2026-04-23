"use client";

import { motion } from "framer-motion";
import { type CheckPromptResult } from "@/services/api";
import { ShieldAlert, ShieldCheck, AlertTriangle } from "lucide-react";

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
        <div className="score-fill" style={{ width: `${pct}%`, background: `var(${colorVar})` }} />
      </div>
    </div>
  );
}

export default function ResultPanel({ result }: ResultPanelProps) {
  if (!result) {
    return (
      <div className="glass-panel" style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "400px", color: "var(--text-muted)" }}>
        <div style={{ textAlign: "center" }}>
          <ShieldCheck size={48} style={{ opacity: 0.2, margin: "0 auto 16px" }} />
          <p>Awaiting prompt analysis...</p>
        </div>
      </div>
    );
  }

  const isBlocked = result.risk_level === "malicious";
  const isSuspicious = result.risk_level === "suspicious";
  const riskColor = isBlocked ? "--malicious" : isSuspicious ? "--suspicious" : "--safe";

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`glass-panel ${isBlocked ? 'glow-red' : isSuspicious ? 'glow-cyan' : 'glow-cyan'}`}
      style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px", height: "100%" }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 className="heading-syne" style={{ fontSize: "18px", margin: "0 0 4px", color: isBlocked ? "var(--red)" : "var(--cyan)" }}>Analysis Result</h2>
          <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Processed in {result.processing_time_ms.toFixed(0)}ms
          </div>
        </div>
        <div className={`badge badge-${result.risk_level}`} style={{ padding: "6px 14px", fontSize: "13px" }}>
          {isBlocked ? <ShieldAlert size={16} /> : isSuspicious ? <AlertTriangle size={16} /> : <ShieldCheck size={16} />}
          {result.risk_level}
        </div>
      </div>

      {/* Warning/Block Message */}
      {(result.warning || result.message) && (
        <div
          className="mono"
          style={{
            padding: "16px",
            background: `var(${riskColor}-bg)`,
            border: `1px solid rgba(var(${riskColor}), 0.2)`,
            borderRadius: "var(--radius-sm)",
            color: `var(${riskColor})`,
            fontSize: "13px",
            display: "flex",
            gap: "12px",
            alignItems: "flex-start",
            boxShadow: isBlocked ? "var(--red-glow)" : "none",
          }}
        >
          <div style={{ marginTop: "2px" }}>
            {isBlocked ? <ShieldAlert size={20} /> : <AlertTriangle size={20} />}
          </div>
          <div>
            <div style={{ fontWeight: 600, marginBottom: "4px" }}>
              {isBlocked ? "Prompt Blocked" : "Suspicious Prompt Tagged"}
            </div>
            <div style={{ opacity: 0.9 }}>{result.message || result.warning}</div>
          </div>
        </div>
      )}

      {/* Scores */}
      <div>
        <h3 className="mono" style={{ fontSize: "14px", color: "var(--text-primary)", marginBottom: "16px" }}>Detection Scores</h3>
        <ScoreBar label="SVM (TF-IDF)" value={result.svm_score} colorVar="--cyan" />
        <ScoreBar label="Transformer (MiniLM)" value={result.transformer_score} colorVar="--cyan" />
        <ScoreBar label="Composite Risk Score" value={result.combined_score} colorVar={riskColor} />
      </div>

      {/* Triggered Rules */}
      {result.triggered_rules && result.triggered_rules.length > 0 && (
        <div>
          <h3 className="mono" style={{ fontSize: "14px", color: "var(--text-primary)", marginBottom: "12px" }}>Triggered Rules</h3>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {result.triggered_rules.map((rule, idx) => (
              <span key={idx} className="mono" style={{ background: "var(--red-bg)", color: "var(--red)", border: "1px solid rgba(255,59,59,0.3)", padding: "4px 10px", borderRadius: "100px", fontSize: "11px", fontWeight: 600 }}>
                {rule}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* LLM Response */}
      {result.llm_response && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 className="mono" style={{ fontSize: "14px", color: "var(--cyan)", margin: 0 }}>&gt; LLM Output</h3>
            {result.provider && (
              <span className="badge badge-neutral" style={{ fontSize: "10px", background: "rgba(255,255,255,0.05)" }}>
                {result.provider.toUpperCase()}
              </span>
            )}
          </div>
          <div className="textarea-glass" style={{
            flex: 1,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
            minHeight: "100px",
            color: "var(--text-secondary)"
          }}>
            {result.llm_response}
          </div>
        </div>
      )}
    </motion.div>
  );
}
