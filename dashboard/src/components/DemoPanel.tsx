"use client";

import { motion } from "framer-motion";
import { type DemoResult } from "@/services/api";
import { ShieldAlert, ShieldCheck, AlertTriangle, Unlock, Shield } from "lucide-react";

export default function DemoPanel({ result }: { result: DemoResult | null }) {
  if (!result) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ display: "flex", flexDirection: "column", gap: "24px" }}
    >
      <div
        className={`glass-panel ${result.security_value.attack_blocked ? 'glow-cyan' : 'glow-red'}`}
        style={{
          padding: "16px 24px",
          background: result.security_value.attack_blocked ? "var(--safe-bg)" : "var(--suspicious-bg)",
          border: `1px solid rgba(${result.security_value.attack_blocked ? '0,245,255' : '245,158,11'}, 0.2)`,
          display: "flex",
          alignItems: "center",
          gap: "12px"
        }}
      >
        {result.security_value.attack_blocked ? <ShieldCheck color="var(--safe)" /> : <AlertTriangle color="var(--suspicious)" />}
        <div className="mono" style={{ fontSize: "14px" }}>
          <strong style={{ color: result.security_value.attack_blocked ? "var(--safe)" : "var(--suspicious)" }}>Security Value Demonstrated: </strong>
          {result.security_value.attack_blocked
            ? "Firewall successfully blocked an attack that the unprotected model would have processed."
            : result.security_value.attack_detected
            ? "Firewall detected suspicious activity and warned before allowing the prompt."
            : "No injection detected in this prompt."}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        
        {/* UNPROTECTED */}
        <div className="glass-panel glow-red" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "4px", background: "var(--malicious)", boxShadow: "var(--red-glow)" }} />
          <div className="heading-syne" style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--malicious)", fontWeight: 700, fontSize: "18px" }}>
            <Unlock size={20} />
            Without Firewall
          </div>
          
          <div>
            <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>LLM Status</div>
            <div className="badge badge-neutral" style={{ padding: "6px 12px", background: "rgba(255,255,255,0.05)" }}>Bypassed (Not Analyzed)</div>
          </div>

          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>Raw LLM Response:</div>
            <div className="textarea-glass" style={{ flex: 1, minHeight: "150px", color: "var(--text-secondary)" }}>
              {result.without_firewall.llm_response || <span style={{ color: "var(--text-muted)" }}>No response received</span>}
            </div>
          </div>
        </div>

        {/* PROTECTED */}
        <div className="glass-panel glow-cyan" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "4px", background: "var(--safe)", boxShadow: "var(--cyan-glow)" }} />
          <div className="heading-syne" style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--safe)", fontWeight: 700, fontSize: "18px" }}>
            <Shield size={20} />
            With Firewall
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
            <div>
              <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>Analysis Result</div>
              <div className={`badge badge-${result.with_firewall.risk_level}`} style={{ padding: "6px 12px" }}>
                {result.with_firewall.risk_level === "malicious" ? <ShieldAlert size={14}/> : <ShieldCheck size={14}/>}
                {result.with_firewall.risk_level}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>Combined Risk Score</div>
              <div className="mono" style={{ fontSize: "16px", color: "var(--text-primary)", textShadow: "var(--cyan-glow)" }}>
                {(result.with_firewall.combined_score * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div className="mono" style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>
              {result.with_firewall.message ? "System Action:" : "Secured LLM Response:"}
            </div>
            {result.with_firewall.message ? (
              <div style={{ background: "var(--malicious-bg)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "var(--radius-sm)", padding: "16px", color: "var(--malicious)", flex: 1, display: "flex", alignItems: "center", gap: "12px", boxShadow: "var(--red-glow)" }}>
                <ShieldAlert size={24} />
                <div className="mono" style={{ fontWeight: 500, fontSize: "14px" }}>{result.with_firewall.message}</div>
              </div>
            ) : (
              <div className="textarea-glass" style={{ flex: 1, minHeight: "150px", color: "var(--cyan)" }}>
                {result.with_firewall.llm_response}
              </div>
            )}
          </div>
        </div>

      </div>
    </motion.div>
  );
}
