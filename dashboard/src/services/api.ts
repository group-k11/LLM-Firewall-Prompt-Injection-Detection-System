import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export interface CheckPromptResult {
  status: string;
  risk_level: string;
  confidence: number;
  svm_score: number;
  transformer_score: number;
  combined_score: number;
  triggered_rules: string[];
  llm_response: string | null;
  llm_called: boolean;
  provider: string | null;
  processing_time_ms: number;
  warning: string | null;
  message: string | null;
  reason: string;
  firewall_active: boolean;
}

export interface DemoResult {
  prompt: string;
  without_firewall: CheckPromptResult;
  with_firewall: CheckPromptResult;
  security_value: {
    attack_detected: boolean;
    attack_blocked: boolean;
    risk_level: string;
    triggered_rules: string[];
  };
}

export interface Stats {
  total_prompts: number;
  safe_prompts: number;
  suspicious_prompts: number;
  malicious_prompts: number;
  blocked_attacks: number;
  llm_calls_made: number;
}

export interface LogEntry {
  id: number;
  prompt: string;
  timestamp: string;
  risk_score: number;
  risk_level: string;
  decision: string;
  reason: string;
  svm_score: number;
  transformer_score: number;
  combined_score: number;
  confidence: number;
  triggered_rules: string[];
  llm_provider: string;
  llm_response: string;
  llm_called: number;
  response_time_ms: number;
}

export interface LLMStatus {
  groq: { available: boolean; model: string | null };
  ollama: { available: boolean; model: string | null };
  active_provider: string;
}

export async function checkPrompt(
  prompt: string,
  firewallEnabled: boolean
): Promise<CheckPromptResult> {
  const { data } = await api.post("/check_prompt", {
    prompt,
    firewall_enabled: firewallEnabled,
  });
  return data;
}

export async function demoAttack(prompt: string): Promise<DemoResult> {
  const { data } = await api.post("/demo_attack", { prompt });
  return data;
}

export async function getLlmStatus(): Promise<LLMStatus> {
  const { data } = await api.get("/llm_status");
  return data;
}

export async function getStats(): Promise<Stats> {
  const { data } = await api.get("/stats");
  return data;
}

export async function getLogs(limit = 50): Promise<LogEntry[]> {
  const { data } = await api.get("/logs", { params: { limit } });
  return data;
}
