import json
import os
import re
import shutil
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from groq import Groq

load_dotenv()

os.makedirs("results/sites", exist_ok=True)
os.makedirs("results/sites/previews", exist_ok=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# AI CLIENT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_ai_response(prompt: str, max_tokens: int = 4000) -> str:
    try:
        claude = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        if True: # Fallback on any error
            groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        raise e


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# NICHE COLOR SCHEMES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NICHE_THEMES = {
    "restaurant": {
        "primary": "#C8860A",
        "secondary": "#1A1A1A",
        "accent": "#F5F0E8",
        "font": "Playfair Display",
        "hero_phrase": "Experience Unforgettable Flavours"
    },
    "salon": {
        "primary": "#8B4F7E",
        "secondary": "#2D2D2D",
        "accent": "#FDF5F9",
        "font": "Cormorant Garamond",
        "hero_phrase": "Where Beauty Meets Excellence"
    },
    "clinic": {
        "primary": "#1B6CA8",
        "secondary": "#1A1A2E",
        "accent": "#F0F8FF",
        "font": "Poppins",
        "hero_phrase": "Your Health Is Our Priority"
    },
    "hotel": {
        "primary": "#8B6914",
        "secondary": "#1A1A1A",
        "accent": "#FAFAF5",
        "font": "Cormorant Garamond",
        "hero_phrase": "Luxury Redefined"
    },
    "school": {
        "primary": "#2E6B3E",
        "secondary": "#1A1A2E",
        "accent": "#F0FFF4",
        "font": "Poppins",
        "hero_phrase": "Building Tomorrow's Leaders Today"
    },
    "pharmacy": {
        "primary": "#1B8A6B",
        "secondary": "#1A2E2E",
        "accent": "#F0FFF8",
        "font": "Poppins",
        "hero_phrase": "Your Trusted Health Partner"
    },
    "gym": {
        "primary": "#D4380D",
        "secondary": "#0A0A0A",
        "accent": "#FFF2F0",
        "font": "Oswald",
        "hero_phrase": "Transform Your Body, Transform Your Life"
    },
    "church": {
        "primary": "#4A2C7A",
        "secondary": "#1A1A2E",
        "accent": "#F8F5FF",
        "font": "Playfair Display",
        "hero_phrase": "A Place of Hope, Love and Faith"
    },
    "real_estate": {
        "primary": "#1A3A5C",
        "secondary": "#0A0A1A",
        "accent": "#F5F8FF",
        "font": "Poppins",
        "hero_phrase": "Find Your Perfect Home"
    },
    "default": {
        "primary": "#1A3A5C",
        "secondary": "#0A0A1A",
        "accent": "#F5F8FF",
        "font": "Poppins",
        "hero_phrase": "Excellence in Every Detail"
    }
}


def get_theme(niche: str) -> dict:
    niche_lower = niche.lower()
    for key in NICHE_THEMES:
        if key in niche_lower:
            return NICHE_THEMES[key]
    return NICHE_THEMES["default"]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SITE CONTENT GENERATOR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def generate_site_content(lead: dict) -> dict:
    name = lead["name"]
    niche = lead.get("niche", "business")
    city = lead.get("city", "Nigeria")
    personality = lead.get("personality") or {}
    reviews = lead.get("reviews_analysis") or {}
    ig = lead.get("instagram") or {}
    fb = lead.get("facebook") or {}

    praises = reviews.get("praises", [])
    complaints = reviews.get("complaints", [])
    vibe = personality.get("vibe", "professional")
    key_pride = personality.get("key_pride", "")
    target_audience = personality.get("target_audience", "customers")

    # Rating
    rating = lead.get("rating", "")
    review_count = lead.get("reviews", "")

    # Contact info
    phone = lead.get("contact_whatsapp") or lead.get("phone") or ""
    email = lead.get("contact_email") or ""
    address = lead.get("address") or f"{city}, Nigeria"
    whatsapp = lead.get("contact_whatsapp") or ""

    prompt = f"""
You are building website content for a real business. Generate compelling, 
specific, and authentic content based on what we know about this business.

Business: {name}
Type: {niche}
City: {city}
Vibe: {vibe}
What customers love: {praises}
Key pride: {key_pride}
Target audience: {target_audience}
Rating: {rating} ({review_count} reviews)

Generate ONLY valid JSON with this exact structure:
{{
  "tagline": "compelling 6-8 word tagline specific to this business",
  "hero_description": "2 sentence compelling description of what makes this business special",
  "about_text": "3 sentence authentic about us paragraph that feels personal and real",
  "service_1_name": "first key service or offering name",
  "service_1_desc": "one sentence description",
  "service_2_name": "second key service or offering",
  "service_2_desc": "one sentence description", 
  "service_3_name": "third key service or offering",
  "service_3_desc": "one sentence description",
  "testimonial_1": "realistic positive customer testimonial based on known praises",
  "testimonial_1_author": "realistic Nigerian customer name",
  "testimonial_2": "second realistic testimonial",
  "testimonial_2_author": "second realistic Nigerian customer name",
  "cta_text": "compelling call to action button text (max 5 words)",
  "whatsapp_message": "pre-filled WhatsApp message when customer clicks chat",
  "meta_description": "SEO meta description for this business page"
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=1500)
        clean = re.sub(r'```json|```', '', response).strip()
        start = clean.find('{')
        end = clean.rfind('}')
        if start != -1 and end != -1:
            content = json.loads(clean[start:end+1])
            # Add contact data
            content["phone"] = phone
            content["email"] = email
            content["address"] = address
            content["whatsapp"] = whatsapp
            content["rating"] = str(rating)
            content["review_count"] = str(review_count)
            content["instagram_url"] = ig.get("url", "")
            content["facebook_url"] = fb.get("url", "")
            return content
    except Exception as e:
        print(f"   âš ï¸  Content generation failed: {e}")

    # Fallback content
    return {
        "tagline": f"Welcome to {name}",
        "hero_description": f"{name} is one of {city}'s finest {niche} establishments, dedicated to excellence and customer satisfaction.",
        "about_text": f"At {name}, we take pride in delivering exceptional service to every customer. Located in the heart of {city}, we have built our reputation on quality, consistency and genuine care for the people we serve.",
        "service_1_name": "Premium Service",
        "service_1_desc": "World-class service tailored to your needs.",
        "service_2_name": "Expert Team",
        "service_2_desc": "Experienced professionals dedicated to excellence.",
        "service_3_name": "Customer Care",
        "service_3_desc": "Your satisfaction is our top priority.",
        "testimonial_1": "Absolutely wonderful experience. Highly recommended!",
        "testimonial_1_author": "Chukwuemeka O.",
        "testimonial_2": "Best in the city. Will definitely be coming back!",
        "testimonial_2_author": "Fatima A.",
        "cta_text": "Contact Us Today",
        "whatsapp_message": f"Hello {name}, I found your website and I'd like to make an enquiry.",
        "meta_description": f"{name} - Premium {niche} in {city}, Nigeria. Contact us today.",
        "phone": phone,
        "email": email,
        "address": address,
        "whatsapp": whatsapp,
        "rating": str(rating),
        "review_count": str(review_count),
        "instagram_url": ig.get("url", ""),
        "facebook_url": fb.get("url", ""),
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HTML SITE GENERATOR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_html_site(lead: dict, content: dict, theme: dict) -> str:
    name = lead["name"]
    city = lead.get("city", "Nigeria")
    niche = lead.get("niche", "business")

    # WhatsApp number formatting
    wa_number = content.get("whatsapp", "").replace("+", "").replace(" ", "").replace("-", "")
    if wa_number.startswith("0"):
        wa_number = "234" + wa_number[1:]
    wa_link = f"https://wa.me/{wa_number}?text={content.get('whatsapp_message', '').replace(' ', '%20')}"

    # Social links
    ig_url = content.get("instagram_url", "")
    fb_url = content.get("facebook_url", "")

    # Rating stars
    try:
        rating_float = float(content.get("rating", 0))
        full_stars = int(rating_float)
        stars_html = "â˜…" * full_stars + "â˜†" * (5 - full_stars)
    except:
        stars_html = "â˜…â˜…â˜…â˜…â˜…"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{content.get('meta_description', '')}">
    <title>{name} | {city}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family={content.get('font', theme['font']).replace(' ', '+')}:wght@300;400;600;700&family=Poppins:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --primary: {theme['primary']};
            --secondary: {theme['secondary']};
            --accent: {theme['accent']};
            --white: #ffffff;
            --gray: #6B7280;
            --light-gray: #F9FAFB;
        }}

        body {{
            font-family: 'Poppins', sans-serif;
            color: var(--secondary);
            overflow-x: hidden;
        }}

        /* â”€â”€ NAVIGATION â”€â”€ */
        nav {{
            position: fixed;
            top: 0;
            width: 100%;
            z-index: 1000;
            padding: 1rem 2rem;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 20px rgba(0,0,0,0.08);
        }}

        .nav-logo {{
            font-family: '{theme['font']}', serif;
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--primary);
            text-decoration: none;
        }}

        .nav-links {{
            display: flex;
            gap: 2rem;
            list-style: none;
        }}

        .nav-links a {{
            text-decoration: none;
            color: var(--secondary);
            font-size: 0.9rem;
            font-weight: 500;
            transition: color 0.3s;
        }}

        .nav-links a:hover {{ color: var(--primary); }}

        .nav-cta {{
            background: var(--primary);
            color: white !important;
            padding: 0.6rem 1.4rem;
            border-radius: 50px;
            font-weight: 600 !important;
        }}

        .nav-cta:hover {{ opacity: 0.9; }}

        .hamburger {{
            display: none;
            flex-direction: column;
            gap: 5px;
            cursor: pointer;
        }}

        .hamburger span {{
            width: 25px;
            height: 2px;
            background: var(--secondary);
            transition: 0.3s;
        }}

        /* â”€â”€ HERO â”€â”€ */
        .hero {{
            min-height: 100vh;
            background: linear-gradient(135deg, var(--secondary) 0%, {theme['primary']}44 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 6rem 2rem 4rem;
            position: relative;
            overflow: hidden;
        }}

        .hero::before {{
            content: '';
            position: absolute;
            width: 600px;
            height: 600px;
            background: var(--primary);
            border-radius: 50%;
            opacity: 0.05;
            top: -200px;
            right: -200px;
        }}

        .hero::after {{
            content: '';
            position: absolute;
            width: 400px;
            height: 400px;
            background: var(--primary);
            border-radius: 50%;
            opacity: 0.08;
            bottom: -150px;
            left: -100px;
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
            max-width: 800px;
        }}

        .hero-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            padding: 0.4rem 1.2rem;
            border-radius: 50px;
            font-size: 0.8rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
        }}

        .hero h1 {{
            font-family: '{theme['font']}', serif;
            font-size: clamp(2.5rem, 6vw, 5rem);
            color: white;
            line-height: 1.1;
            margin-bottom: 1.5rem;
            font-weight: 700;
        }}

        .hero h1 span {{ color: var(--primary); filter: brightness(1.5); }}

        .hero-desc {{
            color: rgba(255,255,255,0.8);
            font-size: 1.1rem;
            line-height: 1.8;
            margin-bottom: 2.5rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}

        .hero-buttons {{
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }}

        .btn-primary {{
            background: var(--primary);
            color: white;
            padding: 1rem 2.5rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}

        .btn-secondary {{
            background: transparent;
            color: white;
            padding: 1rem 2.5rem;
            border-radius: 50px;
            border: 2px solid rgba(255,255,255,0.5);
            text-decoration: none;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s;
        }}

        .btn-secondary:hover {{
            background: rgba(255,255,255,0.1);
            border-color: white;
        }}

        .hero-stats {{
            display: flex;
            justify-content: center;
            gap: 3rem;
            margin-top: 4rem;
            flex-wrap: wrap;
        }}

        .stat {{
            text-align: center;
            color: white;
        }}

        .stat-number {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
            filter: brightness(1.5);
            display: block;
        }}

        .stat-label {{
            font-size: 0.8rem;
            opacity: 0.7;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* â”€â”€ SECTIONS â”€â”€ */
        section {{ padding: 5rem 2rem; }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        .section-badge {{
            display: inline-block;
            color: var(--primary);
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }}

        .section-title {{
            font-family: '{theme['font']}', serif;
            font-size: clamp(1.8rem, 4vw, 2.8rem);
            font-weight: 700;
            margin-bottom: 1rem;
            line-height: 1.2;
        }}

        .section-desc {{
            color: var(--gray);
            font-size: 1.05rem;
            line-height: 1.8;
            max-width: 600px;
        }}

        /* â”€â”€ ABOUT â”€â”€ */
        .about {{ background: var(--accent); }}

        .about-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4rem;
            align-items: center;
        }}

        .about-visual {{
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 20px;
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }}

        .about-visual-text {{
            font-family: '{theme['font']}', serif;
            font-size: 5rem;
            color: rgba(255,255,255,0.15);
            font-weight: 700;
            text-align: center;
            padding: 2rem;
        }}

        .about-badge-float {{
            position: absolute;
            bottom: 2rem;
            right: 2rem;
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        .about-badge-float .stars {{ color: #F59E0B; font-size: 1rem; }}
        .about-badge-float .rating {{ font-weight: 700; font-size: 1.2rem; color: var(--secondary); }}
        .about-badge-float .reviews {{ font-size: 0.75rem; color: var(--gray); }}

        .about-features {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            margin-top: 2rem;
        }}

        .feature {{
            display: flex;
            align-items: flex-start;
            gap: 1rem;
        }}

        .feature-icon {{
            width: 44px;
            height: 44px;
            background: var(--primary);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2rem;
            flex-shrink: 0;
        }}

        .feature-text h4 {{
            font-weight: 600;
            margin-bottom: 0.3rem;
            font-size: 0.95rem;
        }}

        .feature-text p {{
            color: var(--gray);
            font-size: 0.85rem;
            line-height: 1.6;
        }}

        /* â”€â”€ SERVICES â”€â”€ */
        .services-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2rem;
            margin-top: 3rem;
        }}

        .service-card {{
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}

        .service-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            border-bottom-color: var(--primary);
        }}

        .service-icon {{
            width: 56px;
            height: 56px;
            background: var(--accent);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
            margin-bottom: 1.2rem;
        }}

        .service-card h3 {{
            font-weight: 600;
            margin-bottom: 0.6rem;
            font-size: 1rem;
        }}

        .service-card p {{
            color: var(--gray);
            font-size: 0.88rem;
            line-height: 1.7;
        }}

        /* â”€â”€ TESTIMONIALS â”€â”€ */
        .testimonials {{ background: var(--secondary); }}

        .testimonials .section-title {{ color: white; }}
        .testimonials .section-badge {{ color: var(--primary); filter: brightness(1.5); }}

        .testimonials-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-top: 3rem;
        }}

        .testimonial-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 2rem;
            transition: all 0.3s;
        }}

        .testimonial-card:hover {{
            background: rgba(255,255,255,0.08);
            transform: translateY(-3px);
        }}

        .testimonial-stars {{ color: #F59E0B; font-size: 1rem; margin-bottom: 1rem; }}

        .testimonial-text {{
            color: rgba(255,255,255,0.85);
            font-size: 0.95rem;
            line-height: 1.8;
            font-style: italic;
            margin-bottom: 1.5rem;
        }}

        .testimonial-author {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .author-avatar {{
            width: 44px;
            height: 44px;
            background: var(--primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 0.9rem;
        }}

        .author-name {{
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
        }}

        .author-label {{
            color: rgba(255,255,255,0.5);
            font-size: 0.78rem;
        }}

        /* â”€â”€ CONTACT â”€â”€ */
        .contact {{ background: var(--accent); }}

        .contact-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4rem;
            align-items: start;
        }}

        .contact-info {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .contact-item {{
            display: flex;
            align-items: flex-start;
            gap: 1rem;
        }}

        .contact-icon {{
            width: 44px;
            height: 44px;
            background: var(--primary);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.1rem;
            flex-shrink: 0;
        }}

        .contact-detail h4 {{
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 0.2rem;
        }}

        .contact-detail a, .contact-detail p {{
            color: var(--gray);
            text-decoration: none;
            font-size: 0.88rem;
        }}

        .contact-detail a:hover {{ color: var(--primary); }}

        .whatsapp-cta {{
            background: #25D366;
            color: white;
            padding: 1rem 2rem;
            border-radius: 12px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.8rem;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.3s;
            margin-top: 0.5rem;
        }}

        .whatsapp-cta:hover {{
            background: #1ebe57;
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(37,211,102,0.3);
        }}

        .contact-form {{
            background: white;
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.06);
        }}

        .contact-form h3 {{
            font-weight: 600;
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
        }}

        .form-group {{
            margin-bottom: 1.2rem;
        }}

        .form-group input,
        .form-group textarea {{
            width: 100%;
            padding: 0.9rem 1.2rem;
            border: 1.5px solid #E5E7EB;
            border-radius: 10px;
            font-family: 'Poppins', sans-serif;
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.3s;
            resize: none;
        }}

        .form-group input:focus,
        .form-group textarea:focus {{
            border-color: var(--primary);
        }}

        .form-submit {{
            width: 100%;
            background: var(--primary);
            color: white;
            border: none;
            padding: 1rem;
            border-radius: 10px;
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .form-submit:hover {{
            opacity: 0.9;
            transform: translateY(-1px);
        }}

        /* â”€â”€ FOOTER â”€â”€ */
        footer {{
            background: var(--secondary);
            color: rgba(255,255,255,0.6);
            padding: 3rem 2rem 2rem;
        }}

        .footer-content {{
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
        }}

        .footer-brand {{
            font-family: '{theme['font']}', serif;
            font-size: 1.3rem;
            color: white;
            font-weight: 700;
        }}

        .footer-social {{
            display: flex;
            gap: 1rem;
        }}

        .footer-social a {{
            width: 38px;
            height: 38px;
            background: rgba(255,255,255,0.08);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255,255,255,0.7);
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.3s;
        }}

        .footer-social a:hover {{
            background: var(--primary);
            color: white;
        }}

        .footer-copy {{
            width: 100%;
            text-align: center;
            padding-top: 2rem;
            margin-top: 2rem;
            border-top: 1px solid rgba(255,255,255,0.08);
            font-size: 0.8rem;
        }}

        /* â”€â”€ FLOATING WHATSAPP â”€â”€ */
        .float-wa {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 58px;
            height: 58px;
            background: #25D366;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 25px rgba(37,211,102,0.4);
            z-index: 999;
            text-decoration: none;
            color: white;
            font-size: 1.5rem;
            transition: all 0.3s;
            animation: pulse 2s infinite;
        }}

        .float-wa:hover {{
            transform: scale(1.1);
            box-shadow: 0 12px 35px rgba(37,211,102,0.5);
        }}

        @keyframes pulse {{
            0% {{ box-shadow: 0 8px 25px rgba(37,211,102,0.4); }}
            50% {{ box-shadow: 0 8px 35px rgba(37,211,102,0.7); }}
            100% {{ box-shadow: 0 8px 25px rgba(37,211,102,0.4); }}
        }}

        /* â”€â”€ SAMPLE BANNER â”€â”€ */
        .sample-banner {{
            background: linear-gradient(90deg, var(--primary), {theme['secondary']});
            color: white;
            text-align: center;
            padding: 0.8rem 2rem;
            font-size: 0.85rem;
            font-weight: 500;
            position: sticky;
            top: 0;
            z-index: 9999;
        }}

        .sample-banner strong {{ font-weight: 700; }}

        /* â”€â”€ RESPONSIVE â”€â”€ */
        @media (max-width: 768px) {{
            .nav-links {{ display: none; }}
            .hamburger {{ display: flex; }}
            .about-grid,
            .contact-grid,
            .testimonials-grid {{ grid-template-columns: 1fr; }}
            .services-grid {{ grid-template-columns: 1fr; }}
            .hero h1 {{ font-size: 2.2rem; }}
            .hero-stats {{ gap: 1.5rem; }}
            .about-visual {{ height: 250px; }}
        }}

        /* â”€â”€ ANIMATIONS â”€â”€ */
        .fade-in {{
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }}

        .fade-in.visible {{
            opacity: 1;
            transform: translateY(0);
        }}
    </style>
</head>
<body>

    <!-- Sample Banner -->
    <div class="sample-banner">
        ðŸŒŸ This is a <strong>free sample website</strong> built specially for <strong>{name}</strong> â€” 
        <a href="{wa_link}" style="color:white;font-weight:700;">Click here to get yours live today â†’</a>
    </div>

    <!-- Navigation -->
    <nav>
        <a href="#" class="nav-logo">{name}</a>
        <ul class="nav-links">
            <li><a href="#about">About</a></li>
            <li><a href="#services">Services</a></li>
            <li><a href="#testimonials">Reviews</a></li>
            <li><a href="#contact" class="nav-cta">{content.get('cta_text', 'Contact Us')}</a></li>
        </ul>
        <div class="hamburger">
            <span></span><span></span><span></span>
        </div>
    </nav>

    <!-- Hero -->
    <section class="hero" id="home">
        <div class="hero-content fade-in">
            <div class="hero-badge">ðŸ“ {city}, Nigeria</div>
            <h1>{name}<br><span>{content.get('tagline', theme['hero_phrase'])}</span></h1>
            <p class="hero-desc">{content.get('hero_description', '')}</p>
            <div class="hero-buttons">
                <a href="{wa_link}" class="btn-primary">ðŸ’¬ Chat on WhatsApp</a>
                <a href="#about" class="btn-secondary">Learn More</a>
            </div>
            {'<div class="hero-stats"><div class="stat"><span class="stat-number">' + content.get('rating', '4.5') + '</span><span class="stat-label">Star Rating</span></div><div class="stat"><span class="stat-number">' + content.get('review_count', '100+') + '</span><span class="stat-label">Happy Customers</span></div><div class="stat"><span class="stat-number">100%</span><span class="stat-label">Satisfaction</span></div></div>' if content.get('rating') else ''}
        </div>
    </section>

    <!-- About -->
    <section class="about" id="about">
        <div class="container">
            <div class="about-grid">
                <div class="about-visual fade-in">
                    <div class="about-visual-text">{name[0] if name else 'B'}</div>
                    {'<div class="about-badge-float"><div class="stars">' + stars_html + '</div><div class="rating">' + content.get('rating', '4.5') + '/5</div><div class="reviews">' + content.get('review_count', '') + ' reviews</div></div>' if content.get('rating') else ''}
                </div>
                <div class="fade-in">
                    <span class="section-badge">Who We Are</span>
                    <h2 class="section-title">About {name}</h2>
                    <p class="section-desc">{content.get('about_text', '')}</p>
                    <div class="about-features">
                        <div class="feature">
                            <div class="feature-icon">âœ“</div>
                            <div class="feature-text">
                                <h4>Quality First</h4>
                                <p>We never compromise on the quality of what we deliver to our customers.</p>
                            </div>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">â¤</div>
                            <div class="feature-text">
                                <h4>Customer Focused</h4>
                                <p>Every decision we make starts and ends with your satisfaction in mind.</p>
                            </div>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">ðŸ†</div>
                            <div class="feature-text">
                                <h4>Proven Track Record</h4>
                                <p>Trusted by hundreds of customers across {city} and beyond.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Services -->
    <section id="services">
        <div class="container">
            <div class="fade-in" style="text-align:center;margin-bottom:1rem;">
                <span class="section-badge">What We Offer</span>
                <h2 class="section-title">Our Services</h2>
            </div>
            <div class="services-grid">
                <div class="service-card fade-in">
                    <div class="service-icon">â­</div>
                    <h3>{content.get('service_1_name', 'Premium Service')}</h3>
                    <p>{content.get('service_1_desc', 'World-class service tailored to your needs.')}</p>
                </div>
                <div class="service-card fade-in">
                    <div class="service-icon">ðŸŽ¯</div>
                    <h3>{content.get('service_2_name', 'Expert Solutions')}</h3>
                    <p>{content.get('service_2_desc', 'Experienced professionals dedicated to excellence.')}</p>
                </div>
                <div class="service-card fade-in">
                    <div class="service-icon">ðŸ’Ž</div>
                    <h3>{content.get('service_3_name', 'Customer Care')}</h3>
                    <p>{content.get('service_3_desc', 'Your satisfaction is our top priority.')}</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Testimonials -->
    <section class="testimonials" id="testimonials">
        <div class="container">
            <div class="fade-in" style="text-align:center;margin-bottom:1rem;">
                <span class="section-badge">Customer Reviews</span>
                <h2 class="section-title" style="color:white;">What Customers Say</h2>
            </div>
            <div class="testimonials-grid">
                <div class="testimonial-card fade-in">
                    <div class="testimonial-stars">â˜…â˜…â˜…â˜…â˜…</div>
                    <p class="testimonial-text">"{content.get('testimonial_1', 'Absolutely wonderful experience!')}"</p>
                    <div class="testimonial-author">
                        <div class="author-avatar">{content.get('testimonial_1_author', 'C.O')[0]}</div>
                        <div>
                            <div class="author-name">{content.get('testimonial_1_author', 'Chukwuemeka O.')}</div>
                            <div class="author-label">Verified Customer</div>
                        </div>
                    </div>
                </div>
                <div class="testimonial-card fade-in">
                    <div class="testimonial-stars">â˜…â˜…â˜…â˜…â˜…</div>
                    <p class="testimonial-text">"{content.get('testimonial_2', 'Best experience ever. Highly recommended!')}"</p>
                    <div class="testimonial-author">
                        <div class="author-avatar">{content.get('testimonial_2_author', 'F.A')[0]}</div>
                        <div>
                            <div class="author-name">{content.get('testimonial_2_author', 'Fatima A.')}</div>
                            <div class="author-label">Verified Customer</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact -->
    <section class="contact" id="contact">
        <div class="container">
            <div class="fade-in" style="margin-bottom:3rem;">
                <span class="section-badge">Get In Touch</span>
                <h2 class="section-title">Contact {name}</h2>
                <p class="section-desc">We'd love to hear from you. Reach out through any of the channels below.</p>
            </div>
            <div class="contact-grid">
                <div class="contact-info fade-in">
                    {'<div class="contact-item"><div class="contact-icon">ðŸ“ž</div><div class="contact-detail"><h4>Phone</h4><a href="tel:' + content.get('phone','') + '">' + content.get('phone','') + '</a></div></div>' if content.get('phone') else ''}
                    {'<div class="contact-item"><div class="contact-icon">âœ‰</div><div class="contact-detail"><h4>Email</h4><a href="mailto:' + content.get('email','') + '">' + content.get('email','') + '</a></div></div>' if content.get('email') else ''}
                    <div class="contact-item">
                        <div class="contact-icon">ðŸ“</div>
                        <div class="contact-detail">
                            <h4>Location</h4>
                            <p>{content.get('address', city + ', Nigeria')}</p>
                        </div>
                    </div>
                    {'<div class="contact-item"><div class="contact-icon">ðŸ“±</div><div class="contact-detail"><h4>Social Media</h4>' + ('<a href="' + ig_url + '" target="_blank">Instagram</a> &nbsp;' if ig_url else '') + ('<a href="' + fb_url + '" target="_blank">Facebook</a>' if fb_url else '') + '</div></div>' if ig_url or fb_url else ''}
                    <a href="{wa_link}" class="whatsapp-cta" target="_blank">
                        ðŸ’¬ Chat With Us on WhatsApp
                    </a>
                </div>
                <div class="contact-form fade-in">
                    <h3>Send Us a Message</h3>
                    <div class="form-group">
                        <input type="text" placeholder="Your Name" />
                    </div>
                    <div class="form-group">
                        <input type="tel" placeholder="Your Phone Number" />
                    </div>
                    <div class="form-group">
                        <textarea rows="4" placeholder="Your message..."></textarea>
                    </div>
                    <button class="form-submit" onclick="sendViaWhatsApp()">
                        Send Message â†’
                    </button>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <div class="footer-content">
            <div class="footer-brand">{name}</div>
            <div class="footer-social">
                {('<a href="' + wa_link + '" target="_blank">ðŸ’¬</a>') if wa_link else ''}
                {('<a href="' + ig_url + '" target="_blank">ðŸ“¸</a>') if ig_url else ''}
                {('<a href="' + fb_url + '" target="_blank">ðŸ‘</a>') if fb_url else ''}
            </div>
        </div>
        <div class="footer-copy">
            Â© {datetime.now().year} {name}. All rights reserved. | {city}, Nigeria
        </div>
    </footer>

    <!-- Floating WhatsApp -->
    <a href="{wa_link}" class="float-wa" target="_blank" title="Chat with us">ðŸ’¬</a>

    <script>
        // Scroll animations
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('visible');
                }}
            }});
        }}, {{ threshold: 0.1 }});

        document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

        // WhatsApp form
        function sendViaWhatsApp() {{
            const name = document.querySelector('input[placeholder="Your Name"]').value;
            const phone = document.querySelector('input[placeholder="Your Phone Number"]').value;
            const message = document.querySelector('textarea').value;
            if (!name || !message) {{
                alert('Please fill in your name and message');
                return;
            }}
            const text = `Hello {name}, my name is ${{name}} (${{phone}}). ${{message}}`;
            window.open(`https://wa.me/{wa_number}?text=${{encodeURIComponent(text)}}`, '_blank');
        }}

        // Mobile menu
        document.querySelector('.hamburger').addEventListener('click', () => {{
            const nav = document.querySelector('.nav-links');
            nav.style.display = nav.style.display === 'flex' ? 'none' : 'flex';
            nav.style.flexDirection = 'column';
            nav.style.position = 'absolute';
            nav.style.top = '70px';
            nav.style.left = '0';
            nav.style.right = '0';
            nav.style.background = 'white';
            nav.style.padding = '1rem 2rem';
            nav.style.boxShadow = '0 10px 30px rgba(0,0,0,0.1)';
        }});
    </script>
</body>
</html>"""

    return html


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN BUILDER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def build_sample_site(lead: dict) -> dict:
    name = lead["name"]
    niche = lead.get("niche", "business")
    safe_name = re.sub(r'[^a-z0-9]', '-', name.lower()).strip('-')

    print(f"\n   ðŸŒ Building sample site for: {name}")

    # Get theme
    theme = get_theme(niche)
    print(f"   ðŸŽ¨ Theme: {niche} | Primary: {theme['primary']}")

    # Generate content
    print(f"   âœï¸  Generating personalized content...")
    content = generate_site_content(lead)

    # Build HTML
    print(f"   ðŸ”¨ Building HTML site...")
    html = build_html_site(lead, content, theme)

    # Save site
    site_path = f"results/sites/{safe_name}.html"
    with open(site_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Save metadata
    meta = {
        "business_name": name,
        "niche": niche,
        "city": lead.get("city", "Nigeria"),
        "site_path": site_path,
        "theme": theme,
        "content": content,
        "built_at": datetime.now().isoformat(),
        "status": "ready"
    }

    meta_path = f"results/sites/{safe_name}_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"   âœ… Site built: {site_path}")

    return meta


def build_all_sites(
    enriched_file: str = "results/leads/enriched_leads.json",
    only_interested: bool = False
) -> list:
    """Build sample sites for leads"""

    with open(enriched_file, "r") as f:
        leads = json.load(f)

    # Filter leads
    if only_interested:
        leads = [l for l in leads if l.get("status") == "interested"]
        print(f"\nðŸŒ Building sites for {len(leads)} interested leads")
    else:
        leads = [l for l in leads if not l.get("site_built")]
        print(f"\nðŸŒ Building sites for {len(leads)} leads")

    if not leads:
        print("âœ… No leads need sites built")
        return []

    print("=" * 55)

    results = []
    for i, lead in enumerate(leads, 1):
        print(f"\n[{i}/{len(leads)}]", end="")
        try:
            meta = build_sample_site(lead)
            results.append(meta)

            # Mark lead as having site built
            lead["site_built"] = True
            lead["site_path"] = meta["site_path"]

        except Exception as e:
            print(f"\n   âŒ Failed: {str(e)[:80]}")
            continue

    # Update leads file
    with open(enriched_file, "r") as f:
        all_leads = json.load(f)

    built_names = {r["business_name"] for r in results}
    for lead in all_leads:
        if lead["name"] in built_names:
            lead["site_built"] = True

    with open(enriched_file, "w") as f:
        json.dump(all_leads, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*55}")
    print(f"ðŸŒ SAMPLE SITES COMPLETE")
    print(f"{'='*55}")
    print(f"Sites built:    {len(results)}")
    print(f"Saved to:       results/sites/")
    print(f"{'='*55}")

    return results


if __name__ == "__main__":
    build_all_sites()
