"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";

interface StatsCardProps {
  title: string;
  value: number | string;
  icon: ReactNode;
  colorVar: string;
  delay?: number;
}

export default function StatsCard({ title, value, icon, colorVar, delay = 0 }: StatsCardProps) {
  const glowClass = colorVar === "--malicious" ? "glow-red" : "glow-cyan";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={`glass-panel ${glowClass}`}
      style={{
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Subtle glow background */}
      <div
        style={{
          position: "absolute",
          top: "-50%",
          right: "-10%",
          width: "100px",
          height: "100px",
          background: `var(${colorVar})`,
          filter: "blur(60px)",
          opacity: 0.15,
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 className="mono" style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500, margin: 0, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {title}
        </h3>
        <div style={{ color: `var(${colorVar})` }}>{icon}</div>
      </div>

      <div className="heading-syne" style={{ fontSize: "36px", fontWeight: 700, color: "var(--text-primary)", lineHeight: 1 }}>
        {value}
      </div>
    </motion.div>
  );
}
