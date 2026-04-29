# AI Outreach System

An autonomous lead generation and multi-channel outreach system designed for Nigerian businesses. This system finds leads on Google Maps, enriches them with contact details (email, WhatsApp, Instagram, Facebook), audits their digital presence, and writes personalized, AI-driven outreach messages.

## 🚀 Features

- **Lead Finder**: Scrapes Google Maps for specific niches in target cities.
- **Lead Enricher**: Finds official websites, social media profiles, and contact info using a smart search fallback chain (Google, SerpAPI, DuckDuckGo, Bing).
- **Email Verifier**: Validates email addresses using DNS MX record checks and SMTP handshakes.
- **General Auditor**: Performs deep audits of websites, Google Business Profiles, social media, and SEO.
- **Message Writer**: Generates personalized outreach sequences for Email, WhatsApp, Instagram, and Facebook using Claude 4.5 and Llama 3.3.

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
- Copy `ceo_config.example.json` to `ceo_config.json` and customize your outreach settings, service pricing, and owner details.

## 📈 Usage

The system is designed to be run in stages:

1. **Find Leads**:
   ```bash
   python lead_finder.py
   ```
2. **Enrich Leads**:
   ```bash
   python lead_enricher.py
   ```
3. **Verify Emails**:
   ```bash
   python email_verifier.py
   ```
4. **Audit and Write Messages**:
   ```bash
   python general_auditor.py
   python message_writer.py
   ```

Alternatively, you can use the `run` script (Windows):
```bash
./run
```

## 📂 Project Structure
- `lead_finder.py`: Initial discovery via Google Maps.
- `lead_enricher.py`: Deep search and contact extraction.
- `email_verifier.py`: Technical verification of found emails.
- `general_auditor.py`: Detailed business and digital audit.
- `message_writer.py`: AI-driven personalized message generation.
- `ceo_config.json`: Global settings and business logic.
- `results/`: Output directory for leads, audits, and messages (excluded from Git).

## 🛡️ Security
- Never commit your `.env` or `ceo_config.json` files.
- Sensitive results are stored in the `results/` folder, which is ignored by Git.

## 📄 License
MIT
