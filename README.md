# AI Outreach System

An autonomous lead generation and multi-channel outreach system designed for Nigerian businesses. This system finds leads on Google Maps, enriches them with contact details (email, WhatsApp, Instagram, Facebook), audits their digital presence, and writes personalized, AI-driven outreach messages.

The system is organized into a **5-Layer Modular Architecture** for intelligence, outreach, response management, scaling, and autonomous decision-making.

## 🚀 Features (5-Layer Architecture)

### 1. Intelligence
- **Lead Finder**: Scrapes Google Maps for specific niches in target cities, avoiding duplicates.
- **Lead Enricher**: Deep search and contact extraction using a smart fallback chain (Google -> SerpAPI -> DuckDuckGo -> Bing).
- **Auditors**: Deep audits of websites, Google Business Profiles, and SEO to uncover pain points.
- **Email Verifier**: Technical validation of emails via MX and SMTP.

### 2. Outreach
- **Message Writer**: Generates personalized, high-converting sequences for Email, WhatsApp, Instagram, and Facebook using Anthropic Claude (with Groq/Llama fallback).
- **Senders**: Multi-channel sending scripts for Email, WhatsApp, Instagram, and Facebook.
- **Sample Site Builder**: Builds personalized landing pages for leads.

### 3. Response Management
- **Reply Monitor**: Watches inboxes for incoming leads.
- **Reply Handler**: AI-driven reply drafting and nurture management, classifying intents (interested, questions, not interested).

### 4. AI CEO
- Autonomous decision engine that manages the whole pipeline.
- Builds daily schedules based on pipeline health, API limits, and previous outcomes.
- Automatically audits performance and triggers downstream tasks.

### 5. Scale
- Niche and city management to scale outreach across regions effectively.

---

## 🛠️ Setup

### 1. Prerequisites
- Python 3.10+
- Node.js (for Playwright browser management)
- Chrome or Edge browser installed

### 2. Installation
Clone the repository and install dependencies in a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 3. Configuration
You need to configure your environment variables and system settings before running.

1. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys:
   - `CLAUDE_API_KEY`: Primary AI engine (Anthropic).
   - `GROQ_API_KEY`: Fallback AI engine (Groq) - highly recommended for robustness.
   - `SERPAPI_KEY`: Used for lead enrichment fallback when Google blocks automated searches.
   - `BREVO_API_KEY`: For email sending.

2. **System Config**:
   Copy `ceo_config.example.json` to `ceo_config.json`.
   This file controls the business logic:
   - Target niches (e.g., `["salons", "clinics"]`)
   - Target cities (e.g., `["Uromi"]`)
   - Daily sending limits per channel.

---

## 📈 How to Use the System (Step-by-Step)

There are two ways to run the AI Outreach System: **Autonomous Mode (AI CEO)** or **Manual Step-by-Step Mode**.

> **⚠️ Windows Users Note**: Always run your python scripts with the `-X utf8` flag to prevent console crashes when rendering the UI. Example: `python -X utf8 ai_ceo.py`

### Approach A: The Autonomous AI CEO (Recommended)
The AI CEO acts as the orchestrator. It reads the current system state, decides what needs to be done, and executes the commands for you.

```bash
# Run a dry-run to see what the CEO plans to do without executing:
python -X utf8 ai_ceo.py --dry-run

# Run the CEO autonomously (it will execute its decisions immediately):
python -X utf8 ai_ceo.py --autonomous
```
The CEO will automatically trigger the lead finder, enricher, and senders based on your daily limits and pipeline health.

### Approach B: Manual Step-by-Step Execution
If you prefer fine-grained control, you can run the pipeline sequentially:

#### Step 1: Find Leads
```bash
python -X utf8 -m intelligence.lead_finder
```
*What it does: Scrapes Google Maps for your current niche in `ceo_config.json`. Saves raw leads to `results/leads/leads.json`.*

#### Step 2: Enrich Leads
```bash
python -X utf8 -m intelligence.lead_enricher
```
*What it does: Takes raw leads, searches for their official websites, scrapes their social media (Instagram/Facebook), reads reviews, finds competitors, and builds a comprehensive personality profile.*

#### Step 3: Write Messages
```bash
python -X utf8 -m outreach.message_writer
```
*What it does: Uses AI to draft highly personalized messages for all available channels (Email, WhatsApp, IG, Facebook) based on the enriched data. Saves to `results/messages/`.*

#### Step 4: Review Pending Messages (Optional but Recommended)
```bash
python -X utf8 ai_ceo.py review
```
*What it does: The AI CEO reviews the drafted messages for quality before they are cleared for sending.*

#### Step 5: Send Outreach
Execute the specific sender for the channels you want to target:
```bash
python -X utf8 -m outreach.instagram_sender
python -X utf8 -m outreach.whatsapp_sender
python -X utf8 -m outreach.email_sender
```

#### Step 6: Monitor Replies
```bash
python -X utf8 -m response_management.reply_monitor
```
*What it does: Checks for replies and updates the system state.*

---

## 📂 Project Structure

- `intelligence/`: Discovery and research scripts.
- `outreach/`: Message generation and sending logic.
- `response_management/`: Inbox monitoring and reply handling.
- `ai_ceo/`: Autonomous scheduling, reviewing, and decision engine.
- `scale/`: Campaign and niche scaling logic.
- `ceo_config.json`: Global settings and business logic.
- `results/`: Output directory (excluded from Git).

## 🛡️ Security
- **Never commit your `.env` or `ceo_config.json` files.**
- Sensitive results, lead data, and drafted messages are securely stored in the local `results/` folder, which is ignored by Git.

## 📄 License
MIT
