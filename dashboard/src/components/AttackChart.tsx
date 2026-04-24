"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { BarChart2 } from "lucide-react";
import type { AttackTrends } from "@/services/api";

interface AttackChartProps {
  trends: AttackTrends | null;
  loading?: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  instruction_override:  "Instruction Override",
  jailbreak:             "Jailbreak (DAN)",
  prompt_extraction:     "Prompt Extraction",
  privilege_escalation:  "Privilege Escalation",
  safety_bypass:         "Safety Bypass",
  roleplay_attack:       "Roleplay Attack",
  encoding_attack:       "Encoding Obfuscation",
  nested_attack:         "Nested Injection",
  hypothetical:          "Hypothetical Bypass",
  token_injection:       "Token Injection",
  multi_turn_escalation: "Multi-Turn Escalation",
  unknown_injection:     "Unknown Injection",
  none:                  "Safe",
};

const CATEGORY_COLORS: Record<string, string> = {
  instruction_override:  "#ff3b3b",
  jailbreak:             "#ff6b6b",
  prompt_extraction:     "#ff9500",
  privilege_escalation:  "#ffcc00",
  safety_bypass:         "#ff3b3b",
  roleplay_attack:       "#bf5af2",
  encoding_attack:       "#00f5ff",
  nested_attack:         "#30d158",
  hypothetical:          "#ff9f0a",
  token_injection:       "#ff453a",
  multi_turn_escalation: "#ff2d55",
  unknown_injection:     "#8e8e93",
  none:                  "#30d158",
};

function DonutChart({ data }: { data: Array<{ label: string; value: number; color: string }> }) {
  const [hovered, setHovered] = useState<number | null>(null);

  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return (
    <div className="mono" style={{ textAlign: "center", color: "var(--text-muted)", padding: "40px 0", fontSize: "13px" }}>
      No attack data yet
    </div>
  );

  const SIZE = 160;
  const CX = SIZE / 2;
  const CY = SIZE / 2;
  const R_OUTER = 68;
  const R_INNER = 44;

  let cumAngle = -Math.PI / 2;
  const arcs = data.map((d, i) => {
    const fraction = d.value / total;
    const startAngle = cumAngle;
    const endAngle = cumAngle + fraction * 2 * Math.PI;
    cumAngle = endAngle;

    const x1 = CX + R_OUTER * Math.cos(startAngle);
    const y1 = CY + R_OUTER * Math.sin(startAngle);
    const x2 = CX + R_OUTER * Math.cos(endAngle);
    const y2 = CY + R_OUTER * Math.sin(endAngle);
    const x3 = CX + R_INNER * Math.cos(endAngle);
    const y3 = CY + R_INNER * Math.sin(endAngle);
    const x4 = CX + R_INNER * Math.cos(startAngle);
    const y4 = CY + R_INNER * Math.sin(startAngle);
    const largeArc = fraction > 0.5 ? 1 : 0;

    return {
      ...d,
      path: `M ${x1} ${y1} A ${R_OUTER} ${R_OUTER} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${R_INNER} ${R_INNER} 0 ${largeArc} 0 ${x4} ${y4} Z`,
      fraction,
      index: i,
    };
  });

  const hoveredItem = hovered !== null ? data[hovered] : null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
      {/* SVG Donut */}
      <div style={{ position: "relative", flexShrink: 0 }}>
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          {arcs.map((arc) => (
            <path
              key={arc.index}
              d={arc.path}
              fill={arc.color}
              opacity={hovered === null || hovered === arc.index ? 1 : 0.3}
              style={{
                cursor: "pointer",
                filter: hovered === arc.index ? `drop-shadow(0 0 6px ${arc.color})` : "none",
                transition: "opacity 0.2s, filter 0.2s",
              }}
              onMouseEnter={() => setHovered(arc.index)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
          {/* Center text */}
          <text
            x={CX} y={CY - 8}
            textAnchor="middle"
            fill={hoveredItem ? hoveredItem.color : "var(--text-primary)"}
            fontSize="22"
            fontWeight="700"
            fontFamily="'Syne', sans-serif"
          >
            {hoveredItem ? hoveredItem.value : total}
          </text>
          <text
            x={CX} y={CY + 10}
            textAnchor="middle"
            fill="var(--text-muted)"
            fontSize="9"
            fontFamily="'JetBrains Mono', monospace"
          >
            {hoveredItem ? CATEGORY_LABELS[hoveredItem.label] || hoveredItem.label : "TOTAL"}
          </text>
        </svg>
      </div>

      {/* Legend */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px", minWidth: "140px" }}>
        {data.slice(0, 7).map((d, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              opacity: hovered === null || hovered === i ? 1 : 0.4,
              cursor: "pointer",
              transition: "opacity 0.2s",
            }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            <div style={{ width: "10px", height: "10px", borderRadius: "2px", background: d.color, flexShrink: 0 }} />
            <span className="mono" style={{ fontSize: "11px", color: "var(--text-secondary)", flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {CATEGORY_LABELS[d.label] || d.label}
            </span>
            <span className="mono" style={{ fontSize: "11px", color: d.color, fontWeight: 700 }}>
              {d.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniBarChart({ byDay }: { byDay: AttackTrends["by_day"] }) {
  if (byDay.length === 0) return null;
  const maxVal = Math.max(...byDay.map((d) => d.total), 1);

  return (
    <div>
      <div className="mono" style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
        Daily Threat Volume (last {byDay.length} days)
      </div>
      <div style={{ display: "flex", gap: "4px", alignItems: "flex-end", height: "60px" }}>
        {byDay.map((day, i) => {
          const heightPct = (day.total / maxVal) * 100;
          const blockedPct = day.total > 0 ? (day.blocked / day.total) * 100 : 0;
          return (
            <div
              key={i}
              title={`${day.date}: ${day.total} total, ${day.blocked} blocked`}
              style={{
                flex: 1,
                height: "60px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-end",
                gap: "2px",
              }}
            >
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${heightPct}%` }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                style={{
                  background: `linear-gradient(to top, var(--red) ${blockedPct}%, var(--suspicious) ${blockedPct}%)`,
                  borderRadius: "2px 2px 0 0",
                  minHeight: day.total > 0 ? "3px" : "0",
                }}
              />
              <div className="mono" style={{ fontSize: "8px", color: "var(--text-muted)", textAlign: "center" }}>
                {day.date.slice(5)}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mono" style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
        <span style={{ fontSize: "10px", color: "var(--red)" }}>■ Blocked</span>
        <span style={{ fontSize: "10px", color: "var(--suspicious)" }}>■ Suspicious</span>
      </div>
    </div>
  );
}

export default function AttackChart({ trends, loading }: AttackChartProps) {
  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: "20px", minHeight: "200px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="mono" style={{ color: "var(--text-muted)", fontSize: "13px" }}>Loading attack trends…</span>
      </div>
    );
  }

  const donutData = trends
    ? Object.entries(trends.by_category)
        .filter(([k]) => k !== "none")
        .map(([label, value]) => ({
          label,
          value,
          color: CATEGORY_COLORS[label] || "#8e8e93",
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel"
      style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "20px" }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <BarChart2 size={18} color="var(--cyan)" />
        <h3 className="heading-syne" style={{ fontSize: "16px", margin: 0, color: "var(--cyan)" }}>
          Attack Categories
        </h3>
      </div>

      {/* Donut chart */}
      <DonutChart data={donutData} />

      {/* Daily bar chart */}
      {trends && trends.by_day.length > 0 && (
        <MiniBarChart byDay={trends.by_day} />
      )}

      {/* Layer hits */}
      {trends && Object.keys(trends.layer_hits).length > 0 && (
        <div>
          <div className="mono" style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
            Detection Layer Hits
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {Object.entries(trends.layer_hits)
              .sort(([, a], [, b]) => b - a)
              .map(([layer, count]) => {
                const total = Object.values(trends.layer_hits).reduce((s, v) => s + v, 1);
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={layer}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "3px" }}>
                      <span className="mono" style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                        {layer.replace(/_/g, " ")}
                      </span>
                      <span className="mono" style={{ fontSize: "11px", color: "var(--cyan)" }}>{count}</span>
                    </div>
                    <div className="score-track">
                      <motion.div
                        className="score-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.5 }}
                        style={{ background: "var(--cyan)" }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </motion.div>
  );
}
