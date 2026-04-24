"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Shield, ShieldAlert, AlertTriangle, Activity, Clock } from "lucide-react";
import type { SessionPromptRecord } from "@/services/api";

interface SessionTimelineProps {
  history: SessionPromptRecord[];
  sessionId: string;
  cumulativeSuspicion: number;
  totalBlocked: number;
  totalSuspicious: number;
}

function RiskIcon({ level }: { level: string }) {
  if (level === "malicious")  return <ShieldAlert size={14} color="var(--red)" />;
  if (level === "suspicious") return <AlertTriangle size={14} color="var(--suspicious)" />;
  return <Shield size={14} color="var(--safe)" />;
}

function formatRelativeTime(unixTs: number): string {
  const diff = Date.now() / 1000 - unixTs;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  return `${Math.round(diff / 3600)}h ago`;
}

export default function SessionTimeline({
  history,
  sessionId,
  cumulativeSuspicion,
  totalBlocked,
  totalSuspicious,
}: SessionTimelineProps) {
  const riskPct = Math.round(cumulativeSuspicion * 100);
  const riskColor =
    cumulativeSuspicion >= 0.6 ? "var(--red)"
    : cumulativeSuspicion >= 0.3 ? "var(--suspicious)"
    : "var(--safe)";

  return (
    <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Activity size={18} color="var(--cyan)" />
          <h3 className="heading-syne" style={{ fontSize: "16px", margin: 0, color: "var(--cyan)" }}>
            Session Timeline
          </h3>
        </div>
        <span className="mono" style={{ fontSize: "10px", color: "var(--text-muted)", maxWidth: "120px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {sessionId.slice(0, 8)}…
        </span>
      </div>

      {/* Session suspicion bar */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
          <span className="mono" style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Session Risk Level
          </span>
          <span className="mono" style={{ fontSize: "11px", color: riskColor, fontWeight: 700 }}>
            {riskPct}%
          </span>
        </div>
        <div style={{ height: "6px", background: "var(--card-border)", borderRadius: "3px", overflow: "hidden" }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${riskPct}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            style={{ height: "100%", background: riskColor, borderRadius: "3px", boxShadow: `0 0 8px ${riskColor}` }}
          />
        </div>
      </div>

      {/* Quick stats */}
      <div className="mono" style={{ display: "flex", gap: "16px" }}>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--red)", fontWeight: 700 }}>{totalBlocked}</span> blocked
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--suspicious)", fontWeight: 700 }}>{totalSuspicious}</span> suspicious
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--text-primary)", fontWeight: 700 }}>{history.length}</span> in window
        </div>
      </div>

      {/* Timeline entries */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "260px", overflowY: "auto" }}>
        {history.length === 0 ? (
          <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "center", padding: "20px 0" }}>
            No prompts in current session yet
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {[...history].reverse().map((record, idx) => {
              const bgColor =
                record.risk_level === "malicious"  ? "rgba(255,59,59,0.08)"
                : record.risk_level === "suspicious" ? "rgba(245,158,11,0.08)"
                : "rgba(0,245,255,0.04)";
              const borderColor =
                record.risk_level === "malicious"  ? "rgba(255,59,59,0.25)"
                : record.risk_level === "suspicious" ? "rgba(245,158,11,0.25)"
                : "rgba(0,245,255,0.15)";

              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  style={{
                    padding: "10px 12px",
                    background: bgColor,
                    border: `1px solid ${borderColor}`,
                    borderRadius: "6px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "10px",
                  }}
                >
                  {/* Risk icon */}
                  <div style={{ marginTop: "2px", flexShrink: 0 }}>
                    <RiskIcon level={record.risk_level} />
                  </div>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      className="mono"
                      style={{
                        fontSize: "12px",
                        color: "var(--text-secondary)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {record.prompt_preview}
                    </div>
                    <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
                      <span className="mono" style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "3px" }}>
                        <Clock size={10} /> {formatRelativeTime(record.timestamp)}
                      </span>
                      <span className="mono" style={{
                        fontSize: "10px",
                        color: record.risk_level === "malicious" ? "var(--red)" : record.risk_level === "suspicious" ? "var(--suspicious)" : "var(--safe)",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}>
                        {record.decision.replace("_with_warning", "⚠")}
                      </span>
                      <span className="mono" style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        {Math.round(record.risk_score * 100)}%
                      </span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
