"use client";

import { motion } from "framer-motion";
import { type LogEntry } from "@/services/api";
import { ShieldCheck, ShieldAlert, AlertTriangle } from "lucide-react";

interface LogsTableProps {
  logs: LogEntry[];
  onRefresh: () => void;
}

function riskColor(level: string) {
  if (level === "malicious") return "var(--malicious)";
  if (level === "suspicious") return "var(--suspicious)";
  return "var(--safe)";
}

export default function LogsTable({ logs, onRefresh }: LogsTableProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel"
      style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}
    >
      <div style={{ padding: "16px 24px", borderBottom: "1px solid var(--card-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 className="heading-syne" style={{ fontSize: "18px", margin: 0, color: "var(--cyan)" }}>Recent Analysis Logs</h2>
        <button onClick={onRefresh} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }}>
          Refresh Data
        </button>
      </div>

      <div className="logs-table-container" style={{ maxHeight: "600px", overflowY: "auto" }}>
        {logs.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
            No logs available yet.
          </div>
        ) : (
          <table className="logs-table">
            <thead>
              <tr>
                <th style={{ width: "60px" }}>ID</th>
                <th style={{ width: "250px" }}>Prompt</th>
                <th style={{ width: "120px" }}>Risk</th>
                <th style={{ width: "100px" }}>Decision</th>
                <th>SVM</th>
                <th>TF-M</th>
                <th>Combined</th>
                <th>Provider</th>
                <th>Time</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => {
                const isBlocked = log.risk_level === "malicious";
                const isSuspicious = log.risk_level === "suspicious";
                return (
                  <motion.tr
                    key={log.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <td className="mono" style={{ color: "var(--text-muted)" }}>#{log.id}</td>
                    <td>
                      <div
                        title={log.prompt}
                        style={{
                          maxWidth: "250px",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          fontFamily: "var(--font-mono)",
                          fontSize: "12px",
                        }}
                      >
                        {log.prompt}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", color: riskColor(log.risk_level), fontWeight: 600 }}>
                        {isBlocked ? <ShieldAlert size={14} /> : isSuspicious ? <AlertTriangle size={14} /> : <ShieldCheck size={14} />}
                        <span style={{ textTransform: "capitalize" }}>{log.risk_level}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${log.decision === "blocked" ? "malicious" : log.decision === "allowed_with_warning" ? "suspicious" : "safe"}`}>
                        {log.decision.replace("_with_warning", "")}
                      </span>
                    </td>
                    <td className="mono">{(log.svm_score * 100).toFixed(1)}%</td>
                    <td className="mono">{(log.transformer_score * 100).toFixed(1)}%</td>
                    <td className="mono">{(log.combined_score * 100).toFixed(1)}%</td>
                    <td style={{ color: "var(--accent)" }}>{log.llm_provider ? log.llm_provider.toUpperCase() : "—"}</td>
                    <td className="mono">{log.response_time_ms ? `${log.response_time_ms.toFixed(0)}ms` : "—"}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                      {new Date(log.timestamp).toLocaleString(undefined, {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit"
                      })}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </motion.div>
  );
}
