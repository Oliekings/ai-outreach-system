# AI Outreach System

An autonomous lead generation and multi-channel outreach system designed for Nigerian businesses. This system finds leads on Google Maps, enriches them with contact details (email, WhatsApp, Instagram, Facebook), audits their digital presence, and writes personalized, AI-driven outreach messages.

The system is organized into a **5-Layer Modular Architecture** for intelligence, outreach, response management, scaling, and autonomous decision-making.

## 🚀 Features (5-Layer Architecture)

### 1. Intelligence
- **Lead Finder**: Scrapes Google Maps for specific niches in target cities.
- **Lead Enricher**: Deep search and contact extraction with a smart search fallback chain.
- **Auditors**: Deep audits of websites, Google Business Profiles, and SEO.
- **Email Verifier**: Technical validation of emails via MX and SMTP.

### 2. Outreach
- **Message Writer**: Generates personalized sequences for Email, WhatsApp, Instagram, and Facebook.
- **Senders**: Multi-channel sending via Brevo (Email), WhatsApp Web, Instagram, and Facebook.
- **Sample Site Builder**: Builds personalized landing pages for leads.

### 3. Response Management
- **Reply Monitor**: Watches inboxes for incoming leads.
- **Reply Handler**: AI-driven reply drafting and nurture management.

### 4. AI CEO
- Autonomous decision engine, scheduling, and high-level system auditing.

### 5. Scale
- Niche and city management to scale outreach across Nigeria.

## 🛠️ Setup

### 1. Prerequisites
- Python 3.8+
- Node.js (for Playwright browser management)

### 2. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configuration
- Copy `.env.example` to `.env` and fill in your API keys (Anthropic, Groq, SerpAPI, Brevo).
- Copy `ceo_config.example.json` to `ceo_config.json` and customize your settings.

## 📈 Usage

The system uses a modular Python structure. Run modules from the project root:

1. **Intelligence Phase**:
   ```bash
   python -m intelligence.lead_finder
   python -m intelligence.lead_enricher
   python -m intelligence.email_verifier
   ```

2. **Outreach Phase**:
   ```bash
   python -m intelligence.general_auditor
   python -m outreach.message_writer
   ```

3. **Response Management**:
   ```bash
   python -m response_management.reply_monitor
   python -m response_management.reply_handler --report
   ```

## 📂 Project Structure

- `intelligence/`: Discovery and research scripts.
- `outreach/`: Message generation and sending logic.
- `response_management/`: Inbox monitoring and reply handling.
- `ai_ceo/`: Autonomous scheduling and dashboard.
- `scale/`: Campaign and niche scaling logic.
- `ceo_config.json`: Global settings and business logic.
- `results/`: Output directory (excluded from Git).

## 🛡️ Security
- Never commit your `.env` or `ceo_config.json` files.
- Sensitive results are stored in the `results/` folder, which is ignored by Git.

## 📄 License
MIT
