# 🏥 ClaimPilot: AI-Powered Medical Revenue Cycle Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> ClaimPilot is an intelligent, open-source AI agent engineered specifically for healthcare revenue cycle management. Instead of functioning as a generic "chatbot," ClaimPilot operates autonomously as a rigorous reasoning engine: it analyzes denied insurance claims, diagnoses the root cause against retrieved medical policies, identifies missing clinical evidence, and generates highly targeted, policy-cited appeal letters.

### 🔗 [Live Demo on GitHub Pages](https://sarvanithin.github.io/ClaimPilot/)

---

### 📸 Application Demo

*(Demo GIF or screenshot of the agent's logic pathway showing the bifurcated tracks and generated appeals)*

> **Note for Contributors:** Please add a GIF here showcasing the Gap Analysis UI and the resulting Appeal generation.

---

## 🚀 Key Differentiators: Beyond a "Chatbot"

Why is ClaimPilot different from just pasting clinical notes into ChatGPT?

1. **Grounded Verification (RAG):** It doesn't hallucinate definitions. ClaimPilot fetches verbatim chunks of CMS and Commercial Medical Policies from a local Vector Database (ChromaDB) to ground its logic.
2. **Missing Evidence Detection (Gap Analysis):** Before drafting an appeal, the AI cross-references the doctor's clinical notes against the actual medical policy and explicitly outputs a checklist of whatever required criteria you forgot to include in the chart.
3. **Self-Critique & Token Optimization:** The agent uses a multi-step loop. After drafting the initial letter, it sends the draft back to an editor LLM to explicitly verify citations. We optimize these complex pipelines using the **Martian Router API**, forcing the LLM to adhere to strict word counts and JSON shapes to minimize compute expenditure.
4. **Predictive Success Scoring:** Based on the gap analysis, the AI computes a 0-100% Probability Score on how likely the appeal is to succeed, allowing billing teams to prioritize their backlog.

---

## 🏗️ System Architecture & Data Flow

ClaimPilot uses a decoupled, asynchronous microservices architecture.

### 1. The Core Stack
- **AI Agent Engine (Backend):** Python + FastAPI + LangChain. Orchestrates a state machine connecting specialized LLM agents (Classifier, Retriever, Writer, Editor).
- **Knowledge Base (Database):** Local persistent ChromaDB instance utilizing dense text embeddings to match semantic clinical language to strict policy headers.
- **Frontend (UI):** React + Tailwind CSS single-page application built for high-throughput billing environments.
- **LLM Backbone:** Configured dynamically via the Martian API Router (`openai/gpt-4o-mini`) to hit performance constraints.

### 2. The Agent Workflow (`/claims/analyze`)
When a claim (Procedure Code, Diagnoses, Claim Reason, Clinical Notes) is ingested:

1. **Denial Classification (`classifier.py`):** The agent first classifies the abstract denial text into a structured taxonomy (`medical_necessity`, `coding_error`, etc.).
2. **Policy Retrieval (`retriever.py`):** Synthesizing the diagnosis and procedure codes, a query fetches the top `k` most statistically relevant policy paragraphs.
3. **Medical Necessity Analysis:** The AI contrasts the Doctor's Notes against the Policy Chunks to identify what criteria were satisfied and what failed. 
4. **Iterative Drafting (`appeal_writer.py`):** The AI writes a formal letter, and passes it through an internal "critique" loop to strip out fluff, summarize the clinical gaps, and compute the success percentage.

---

## 🛠️ Requirements & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (For frontend, if building from source)
- An active `GROQ_API_KEY` to route LLM requests efficiently.

### 1. Backend Initialization

Clone the repo, open the project directory, and initialize the virtual environment:

```bash
# Setup Environment
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Export API Keys (GROQ endpoint used as default)
export GROQ_API_KEY="sk-your-key-here"

# Start the highly concurrent FastAPI server
uvicorn backend.main:app --reload --port 8000
```

*Note: By default, the app initializes the ChromaDB client lazily upon first request, ingesting mocked policies if the database is empty.*

### 2. Frontend Initialization

While the project contains a standard Vite setup in `/frontend`, for rapid staging/deployment environments without Node dependency compilation overhead, you can run the Standalone UI:

```bash
# Start a simple Python HTTP server from the project root
python3 -m http.server 3000

# Navigate to: http://localhost:3000/frontend/public/standalone.html
```

*(This standalone entrypoint serves React and Babel over robust CDNs to ensure zero-friction deployment to internal billing departments).*

---

## 🧪 Evaluation & Benchmarking

Accuracy is critical in healthcare. ClaimPilot includes a built-in automated LLM-as-a-judge evaluation harness (`evaluation/eval_runner.py`) inspired by the ARES framework.

The harness evaluates:
- **Classification Accuracy:** Did it correctly identify the CARC/RARC root cause?
- **Tone Professionalism:** Is the tone assertive but deferential to payer reviewers?
- **Citation Specificity:** Did it exactly quote the LCD/NCD/Policy number?

To run tests against the 10 complex mock scenarios:
```bash
python -m evaluation.eval_runner
```

---

*Designed for high accuracy, precision, and deterministic workflows over conversational ambiguity.*
