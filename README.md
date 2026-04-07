# ⚡ ZAP AI Onboarding Automation

An AI-powered pipeline that automates the onboarding of new business clients for Zap Group.  
The system scans a business's digital assets, extracts structured data, generates a client card and a personalized onboarding script, and saves everything to a mock CRM — automatically.

---

## Overview

The pipeline consists of 5 automated steps:

| Step | Description | Technology |
|------|-------------|------------|
| 1 | **Digital Asset Scanning** – website, Dapei Zahav, social media | `requests`, `BeautifulSoup` |
| 2 | **Structured Data Extraction** – name, region, services, hours, phones | Groq LLM (JSON mode) |
| 3 | **Client Card Generation** – professional Markdown document for the producer | Groq LLM |
| 4 | **Onboarding Script Generation** – smart questions, setup steps, KPIs, WhatsApp message | Groq LLM |
| 5 | **CRM Save + Notifications** – WhatsApp & Email (simulated) | JSON / mock |

---

## Architecture

```
main.py              ← Streamlit UI + pipeline orchestration
├── scraper.py       ← Web scraping & contact info extraction
├── ai_processor.py  ← Groq LLM interactions (extraction, card, script)
└── crm.py           ← Mock CRM (JSON files, deduplication, notifications)

.streamlit/
└── config.toml      ← Theme & toolbar configuration

crm_data/
└── ZAP-YYYYMMDD-XXXXXX.json   ← One file per client record
```

---

## Installation

**Prerequisites:** Python 3.10+

```bash
# Clone the repository
git clone https://github.com/NetaDor1/zapProject.git
cd zapProject

# Install dependencies
pip install streamlit groq requests beautifulsoup4 lxml python-dotenv
```

---

## Running the App

```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Project Structure

```
zapProject/
├── main.py              # Streamlit UI – forms, pipeline execution, results display
├── scraper.py           # URL scraping, phone / email / address / hours extraction
├── ai_processor.py      # Prompts, Groq API calls, JSON parsing
├── crm.py               # Save, update, deduplication, activity log
├── .env                 # Environment variables (not committed to git)
├── .streamlit/
│   └── config.toml      # Streamlit theme and toolbar settings
└── crm_data/            # Client records (auto-created at runtime)
```

### `scraper.py`
Scrapes up to 3 URLs using regex patterns to extract Israeli phone numbers, emails, addresses, and business hours. Strips HTML noise and returns clean text for AI analysis.

### `ai_processor.py`
- **`extract_business_profile`** — Extracts a structured JSON profile from raw scraped text (JSON mode).
- **`generate_client_card`** — Produces a consistently formatted Markdown client card.
- **`generate_onboarding_script`** — Builds a full onboarding script with smart intake questions, setup steps, KPIs, and AI insights.
- Includes `_parse_json_safe` and `_repair_truncated_json` to handle malformed LLM responses gracefully.

### `crm.py`
- Saves client records as JSON with a unique ID in the format `ZAP-YYYYMMDD-XXXXXX`.
- **Deduplication** — detects existing records by business name or URL and updates them instead of creating duplicates.
- Simulates WhatsApp and email delivery with a full activity log.

---

## Environment Variables

Copy the example file and add your key:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
GROQ_API_KEY=gsk_...
```

Get a free API key at: [console.groq.com/keys](https://console.groq.com/keys)

> The API key can also be entered directly in the app's sidebar under **Settings**.

---

## Design Decisions

**Groq (`llama-3.1-8b-instant`) as the LLM provider** — free tier with fast inference, sufficient for structured Hebrew text extraction without hitting rate limits on a prototype.

**Streamlit for the UI** — enables rapid prototyping of data pipelines with minimal frontend code, keeping the focus on the AI logic.

**Local JSON files as the CRM** — no database setup required for a prototype; records are human-readable, easy to inspect during a demo, and trivial to replace with a real DB later.

**Modular structure (`scraper` / `ai_processor` / `crm`)** — each layer has a single responsibility and can be swapped or extended independently without touching the others.

**Strict prompt templates with separate system and user prompts** — reduces LLM hallucination and ensures a consistent, predictable output format across different businesses.

**Built-in demo mode** — allows a full end-to-end demonstration without an API key or live internet access.

---

## Demo Mode

The app ships with a **built-in demo mode** — no API key required.  
Demo mode uses a pre-built sample client (an air conditioning technician in the Krayot area) and simulates all pipeline steps with mock data.

To activate: check **Demo Mode (no API)** in the sidebar and click **Start the Process**.
