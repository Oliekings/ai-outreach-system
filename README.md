# AI Outreach System

An autonomous lead generation and multi-channel outreach system designed for Nigerian businesses. This system finds leads on Google Maps, enriches them with contact details (email, WhatsApp, Instagram, Facebook), audits their digital presence, and writes personalized, AI-driven outreach messages.

The system is organized into a **5-Layer Modular Architecture** for intelligence, outreach, response management, scaling, and autonomous decision-making.

## 🚀 Features (5-Layer Architecture)

### 1. Intelligence
- **Lead Finder**: Scrapes Google Maps for specific niches in target cities, avoiding duplicates.
- **Dynamic Backlog Backpressure**: Automatically calculates a dynamic backlog threshold (e.g. double the daily target, minimum 30 leads) based on configurable period limits (`morning_leads_limit`, `afternoon_leads_limit`, `evening_leads_limit`). Skips lead discovery if the active backlog is too large.
- **Lead Enricher**: Deep search and contact extraction using a smart fallback chain (Google -> SerpAPI -> DuckDuckGo -> Bing).
- **Contact Filtering**: Automatically filters out uncontactable leads (no email AND no phone/WhatsApp) from `leads.json` to keep outreach pipelines hyper-efficient.
- **Auditors**: Deep audits of websites, Google Business Profiles, and SEO to uncover pain points.
- **Email Verifier**: Technical validation of emails via MX and SMTP.

### 2. Outreach
- **Message Writer**: Generates personalized, high-converting sequences for Email, WhatsApp, Instagram, and Facebook using Anthropic Claude (with Groq/Llama fallback).
- **Senders**: Multi-channel sending scripts for Email, WhatsApp, Instagram, and Facebook.
- **Sequence Safety & Safeguards**:
  - Automatically avoids sending sequence messages if a later step in the campaign sequence has already been executed.
  - Multi-recipient safeguards halt duplicate email outreach to secondary addresses once a successful delivery is made.
- **Sample Site Builder**: Builds personalized landing pages for leads.

### 3. Response Management
- **Reply Monitor**: Watches inboxes for incoming leads. Includes **automated WhatsApp unread chat scanning** via Playwright.
- **WhatsApp Safety Checker**: Automatically crawls the last 15 active WhatsApp outreach contacts during each scan to capture any replies that didn't trigger unread badges.
- **Reply Handler**: AI-driven reply drafting and nurture management, classifying intents (interested, questions, not interested). Includes a `--auto-approve` command line interface.
- **Automated Reply Dispatch**: Sends approved, drafted response management replies directly back to WhatsApp contacts.
- **Auditable Logging**: Records WhatsApp outreach and replies in dedicated logs (`results/logs/whatsapp_log.json`).

### 4. AI CEO
- Autonomous decision engine that manages the whole pipeline.
- Builds daily schedules based on pipeline health, API limits, and previous outcomes.
- **High-Frequency Quick Check Cycle**: Triggers a swift sweep every 15 minutes during business hours to fetch/send replies, auto-approve pending reviews, and handle nurturing.
- **Single-Instance Locking**: Guarantees sole execution using a socket lock (port `5056`).
- **Active Operations Window**: Operates only on configured days/hours (`send_days`, `send_hours`), sleeping in high-efficiency standby mode on weekends and off-hours.
- **File-Driven Autonomous Fallback**: Monitors file modification times for pending sequences and reply drafts; if they sit longer than `review_deadline_hours` (e.g. 12 hours), the AI CEO autonomously approves and dispatches them.
- **Owner Limit Protection**: Respects the `lock_manual_limits` configuration (defaults to `true`) preventing automated overrides of the owner's manual daily email and WhatsApp limits.

### 5. Scale
- Niche and city management to scale outreach across regions effectively.
- **Strategy Safety**: Preserves locked manual limits when migrating to new cities or recommending optimized limits.

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
