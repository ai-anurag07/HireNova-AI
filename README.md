# 🚀 HireNova | Multi-Agent AI Career Assistant

**Live Demo:** http://hirenova-ai.duckdns.org/ *(Note: Please use `http://` as SSL is pending)*

HireNova is an autonomous, end-to-end AI career platform built on an **Agent-to-Agent (A2A)** and **Model Context Protocol (MCP)** architecture. It acts as a personal career assistant capable of scraping job boards, semantically matching roles to a user's master resume, generating ATS-optimized PDF resumes, and conducting real-time voice mock interviews.

## ✨ Key Features

* **🧠 Multi-Agent Orchestration (Slack & Web):** A central Orchestrator LLM classifies user intents and delegates complex tasks to specialized worker agents (Job Agent, Resume Agent, Interview Agent) using JSON-RPC 2.0.
* **🕵️‍♂️ MCP Multi-Portal Scraper:** A resilient, concurrent web scraper that bypasses bot-protections to aggregate jobs from LinkedIn, Instahyre, and Wellfound using REST APIs, GraphQL, and headless Playwright browsers.
* **📊 Semantic Job Matching (Vector DB):** Embeds the user's master resume and scraped jobs into **ChromaDB**, calculating Cosine Similarity to surface the mathematically best-fitting roles.
* **📄 ATS Resume Studio:** Dynamically tailors a master resume to a specific Job Description (JD) using Llama-3, generating a pixel-perfect, ATS-compliant PDF via a headless HTML-to-PDF rendering engine.
* **🎙️ Live Voice AI Interviewer:** A real-time interview coach that generates highly technical questions based on the user's past projects. Utilizes **Groq Whisper API** for ultra-fast STT transcription and **Edge-TTS** for realistic human voice synthesis, concluding with an AI-generated scorecard.
* **📋 Kanban Application Tracker:** A full-stack Drag-and-Drop dashboard to track job applications, integrated with automated Company Research generation.

## 🛠️ Tech Stack

**Backend (Microservices Architecture)**
* **Framework:** FastAPI (Async)
* **Database:** PostgreSQL (via asyncpg / SQLAlchemy)
* **Vector Store:** ChromaDB
* **Cloud Storage:** MinIO (S3-compatible object storage)
* **Scraping:** Playwright (Headless Chromium), Requests, Regex
* **Background Tasks:** APScheduler (Cron jobs for automated job alerts)

**AI & Machine Learning**
* **LLM:** Llama-3.3-70b-versatile (via Groq API)
* **Speech-to-Text:** Whisper-large-v3
* **Text-to-Speech:** Microsoft Edge-TTS

**Frontend**
* **Framework:** Next.js 14 (App Router)
* **Styling:** Tailwind CSS + Lucide React
* **State Management:** React Hooks + Axios Interceptors

**Cloud & DevOps**
* **Deployment:** Google Cloud Platform (GCP Compute Engine Ubuntu VM)
* **Containerization:** Docker & Docker Compose
* **Networking:** Ngrok (Reverse proxy), IPTables, DuckDNS

## ⚙️ System Architecture

1. **Gateway/Auth:** JWT-based stateless authentication.
2. **Orchestrator Agent:** Receives natural language commands (via Web UI or Slack Webhook), classifies intent, and fires asynchronous A2A tasks.
3. **Execution:** Agents utilize specific MCP tools (e.g., executing the Playwright scraper in isolated async threads) and return strictly typed schemas.
4. **Persistence:** State, resumes, and tracker locations are persisted in PostgreSQL, with physical PDF and audio artifacts stored securely in MinIO.

## 🔒 Security
* Passwords hashed via `bcrypt` (Passlib).
* API endpoints secured via OAuth2 Bearer Tokens.
* Registration gated behind an invite-code bouncer.

---
*Architected and developed by Anurag.*
