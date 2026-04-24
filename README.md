# 🔐 LLM Firewall – Prompt Injection Detection System

![Dashboard UI](https://img.shields.io/badge/UI-Next.js%2014-black?style=flat-square&logo=next.js)
![Backend API](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![ML Models](https://img.shields.io/badge/ML-Scikit--Learn%20%7C%20Transformers-blue?style=flat-square&logo=scikit-learn)

**LLM Firewall** is a production-grade security middleware designed to protect Large Language Model (LLM) applications from **prompt injection**, **jailbreak attacks**, and **adversarial obfuscation**. 

It acts as a protective layer between end-users and your LLM API (OpenRouter, Ollama), intercepting prompts in real-time, executing a hybrid machine-learning pipeline, and neutralizing threats before they reach the model.

---

## 🚀 Key Features & Dashboard Integration

The system includes a premium, SaaS-style Next.js dashboard that visualizes the security pipeline in real-time.

### 1. Hybrid ML Detection Engine
The firewall doesn't rely on a single point of failure. It scores prompts using three distinct methodologies, all visible in the **Analyze Prompt** dashboard tab:
* **Rule-Based Engine:** Checks against 30+ known regex attack patterns (e.g., token injection, instruction overrides).
* **Syntactic ML (SVM + TF-IDF):** Achieves **97.4% accuracy** by detecting structural anomalies and known malicious vocabulary.
* **Semantic ML (Sentence Transformers):** Achieves **95.9% accuracy** using `all-MiniLM-L6-v2` embeddings to catch zero-day attacks that bypass traditional keyword filters by analyzing the *intent* of the prompt.
* *Dashboard UI:* Displays the individual SVM and Transformer scores as animated progress bars, along with the final combined risk percentage.

### 2. Adversarial Preprocessing
Attackers often use obfuscation to bypass filters. The firewall normalizes inputs *before* ML classification:
* Decodes hidden **Base64** strings.
* Translates **Leetspeak** (`1gn0r3` → `ignore`).
* Collapses spaced characters (`b y p a s s` → `bypass`).
* *Dashboard UI:* You can test this using the "Obfuscated" example button. The firewall correctly flags leetspeak attacks with 100% confidence.

### 3. Real-Time Attack Demonstration (Demo Mode)
To prove the firewall's efficacy, the dashboard includes a side-by-side **Demo Mode**:
* **Left Panel (Without Firewall):** Shows the raw, vulnerable LLM response if the prompt was passed directly to the model.
* **Right Panel (With Firewall):** Shows the firewall intercepting the attack, displaying the security value (e.g., "Attack Blocked") and preventing the LLM from executing malicious instructions.

### 4. Dynamic LLM Routing
* Integrates directly with the **Openrouter API** for ultra-fast gpt-oss-120b inference on safe prompts.
* Automatic fallback to a local **Ollama** instance if the primary cloud provider experiences an outage or timeout.
* *Dashboard UI:* The top-right header displays a live indicator of the active LLM provider and model.

### 5. Persistent Audit Logging
* All prompts, risk scores, decisions, and processing latencies are logged to an SQLite database.
* *Dashboard UI:* The **Logs** tab provides a searchable, real-time table of recent activity with color-coded risk badges (Safe / Suspicious / Malicious).

---

## 🏗️ System Architecture

```text
User Input 
  │
  ▼
[ Next.js Dashboard ] ── POST /check_prompt ──┐
                                              │
  ┌───────────────────────────────────────────┴────────────────────────────────────────┐
  │                           FASTAPI SECURITY MIDDLEWARE                              │
  │                                                                                    │
  │  1. Preprocessor (Normalizes Base64, Leetspeak, Whitespace)                        │
  │  2. Rule Engine  (Regex heuristic checks)                                          │
  │  3. ML Pipeline  (TF-IDF SVM  +  MiniLM Transformer)                               │
  │  4. Decision Engine (Calculates Hybrid Risk: Safe / Suspicious / Malicious)        │
  │  5. Database Logger (Records metrics to SQLite)                                    │
  └───────────────────────────────────────────┬────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┴────────────────────────┐
               [MALICIOUS]                                      [SAFE / SUSPICIOUS]
                    │                                                  │
             Returns HTTP 403                                     Forwards to
            "Prompt Blocked"                                      LLM Connector
                                                                       │
                                                      ┌────────────────┴────────────────┐
                                                [ Openrouter API ]                      [ Ollama ]
                                              (Primary Cloud)                  (Local Fallback)
```

---

## ⚙️ Tech Stack

### Backend (Security Layer)
* **Python 3** & **FastAPI**
* **Scikit-learn** (TF-IDF + SVM)
* **Sentence-Transformers** (Semantic Embeddings)
* **SQLite** (Audit Logging)
* **OpenRouter** & **HTTPX** (LLM Integrations)

### Frontend (Dashboard)
* **Next.js 14** (App Router)
* **React** & **Framer Motion** (Fluid UI animations)
* **Vanilla CSS** (Custom Dark/Light SaaS theme with glassmorphism)
* **Lucide React** (Iconography)

---

## 🚀 Installation & Setup

### 1. Backend Setup
```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Train the Machine Learning Models (takes ~1 minute)
python train_model.py

# Start the FastAPI server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Dashboard Setup
```bash
# Navigate to dashboard
cd dashboard

# Install dependencies
npm install

# Configure Environment Variables
# Ensure .env.local contains: NEXT_PUBLIC_API_URL=http://localhost:8000

# Start the development server
npm run dev
```

### 3. Usage
Open [http://localhost:3000](http://localhost:3000) in your browser. Use the provided quick-action buttons to test Safe, Injection, and Obfuscated prompts.

---

## 👨‍💻 Contributors

* Siddesh Shirote
* Satyam Shrivastav
* Sujit Patil
* Sarthak Tagalpallewar
* Sourav Kataria
* Team Members (Group 11)

## 📜 License
This project is for academic, educational, and cybersecurity research purposes.
