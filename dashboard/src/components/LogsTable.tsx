"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { type LogEntry } from "@/services/api";
import { ShieldCheck, ShieldAlert, AlertTriangle, Search, Download, X } from "lucide-react";

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
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all" | "safe" | "suspicious" | "malicious">("all");

  // Filtered logs based on search query and risk filter
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch =
        !searchQuery.trim() ||
        log.prompt.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.decision.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(log.id).includes(searchQuery);

      const matchesRisk = riskFilter === "all" || log.risk_level === riskFilter;

      return matchesSearch && matchesRisk;
    });
  }, [logs, searchQuery, riskFilter]);

  // Export as CSV
  const exportCSV = () => {
    const headers = [
      "ID", "Prompt", "Risk Level", "Decision", "Reason",
      "SVM Score", "Transformer Score", "Combined Score", "Confidence",
      "LLM Provider", "Response Time (ms)", "Timestamp"
    ];
    const rows = filteredLogs.map((log) => [
      log.id,
      `"${log.prompt.replace(/"/g, '""')}"`,
      log.risk_level,
      log.decision,
      `"${log.reason.replace(/"/g, '""')}"`,
      (log.svm_score * 100).toFixed(1),
      (log.transformer_score * 100).toFixed(1),
      (log.combined_score * 100).toFixed(1),
      (log.confidence * 100).toFixed(1),
      log.llm_provider || "—",
      log.response_time_ms?.toFixed(0) || "—",
      log.timestamp
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    downloadFile(csv, "firewall_logs.csv", "text/csv");
  };

  // Export as JSON
  const exportJSON = () => {
    const json = JSON.stringify(filteredLogs, null, 2);
    downloadFile(json, "firewall_logs.json", "application/json");
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const riskFilterButtons: { label: string; value: typeof riskFilter; color: string }[] = [
    { label: "All", value: "all", color: "var(--text-secondary)" },
    { label: "Safe", value: "safe", color: "var(--safe)" },
    { label: "Suspicious", value: "suspicious", color: "var(--suspicious)" },
    { label: "Malicious", value: "malicious", color: "var(--malicious)" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel"
      style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}
    >
      {/* Header Bar */}
      <div style={{ padding: "16px 24px", borderBottom: "1px solid var(--card-border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <h2 className="heading-syne" style={{ fontSize: "18px", margin: 0, color: "var(--cyan)" }}>
          Recent Analysis Logs
          <span className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginLeft: "8px", fontWeight: 400 }}>
            ({filteredLogs.length} of {logs.length})
          </span>
        </h2>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button onClick={exportCSV} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "11px" }} title="Export filtered logs as CSV">
            <Download size={12} /> CSV
          </button>
          <button onClick={exportJSON} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "11px" }} title="Export filtered logs as JSON">
            <Download size={12} /> JSON
          </button>
          <button onClick={onRefresh} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }}>
            Refresh Data
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ padding: "12px 24px", borderBottom: "1px solid var(--card-border)", display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
        {/* Search Input */}
        <div style={{ flex: 1, minWidth: "200px", position: "relative" }}>
          <Search size={14} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search prompts, decisions, reasons..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              background: "rgba(0,0,0,0.5)",
              border: "1px solid var(--card-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-primary)",
              fontFamily: "var(--font-mono)",
              fontSize: "13px",
              padding: "8px 12px 8px 32px",
              transition: "border-color 0.2s",
              outline: "none",
            }}
            onFocus={(e) => (e.target.style.borderColor = "var(--cyan)")}
            onBlur={(e) => (e.target.style.borderColor = "var(--card-border)")}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "2px" }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Risk Level Filter Buttons */}
        <div style={{ display: "flex", gap: "6px" }}>
          {riskFilterButtons.map(({ label, value, color }) => (
            <button
              key={value}
              onClick={() => setRiskFilter(value)}
              style={{
                padding: "5px 12px",
                fontSize: "11px",
                fontFamily: "var(--font-mono)",
                fontWeight: 600,
                borderRadius: "100px",
                border: `1px solid ${riskFilter === value ? color : "var(--card-border)"}`,
                background: riskFilter === value ? `${color}15` : "transparent",
                color: riskFilter === value ? color : "var(--text-muted)",
                cursor: "pointer",
                transition: "all 0.2s",
                textTransform: "uppercase",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="logs-table-container" style={{ maxHeight: "600px", overflowY: "auto" }}>
        {filteredLogs.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
            {logs.length === 0 ? "No logs available yet." : "No logs match your search / filter criteria."}
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
              {filteredLogs.map((log, i) => {
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
