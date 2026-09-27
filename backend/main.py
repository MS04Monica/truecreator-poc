import os
import json
import re
from typing import Optional, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="TrueCreator API PoC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuditRequest(BaseModel):
    video_url: str
    caption: Optional[str] = ""
    creator_handle: Optional[str] = "@unknown"

class Flag(BaseModel):
    type: str
    label: str
    severity: str  # "high", "medium", "info"
    confidence: float
    reason: str

class AuditResponse(BaseModel):
    audit_id: str
    status: str
    trust_score: int
    ownership_status: str  # "verified_original", "unverified_reupload", "bot_aggregator"
    summary_reason: str
    flags: List[Flag]
    preliminary: bool

# Safely read API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = None

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    try:
        from google import genai  # type: ignore
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        client = None


def run_local_heuristics(text: str, handle: str, url: str) -> dict:
    text_lower = text.lower()
    handle_lower = handle.lower()
    url_lower = url.lower()

    flags = []
    trust_score = 95
    ownership_status = "verified_original"

    # 1. Ownership & Re-upload Aggregator Detection
    deal_bot_keywords = ["deal", "deals", "duniya", "loot", "finds", "offers", "store", "fashionhub", "bargain"]
    is_deal_bot = any(k in handle_lower for k in deal_bot_keywords)

    if is_deal_bot:
        ownership_status = "bot_aggregator"
        trust_score -= 25
        flags.append({
            "type": "unverified_authorship",
            "label": "Unverified Re-uploader",
            "severity": "medium",
            "confidence": 0.88,
            "reason": f"Channel handle '{handle}' matches known deal-aggregator patterns rather than original creator profiles."
        })

    # 2. AI Content Badges & Indicators
    ai_patterns = [r"@\s*ai\b", r"\bai-generated\b", r"\bsynthetic\b", r"\bai content\b"]
    if any(re.search(p, text_lower) for p in ai_patterns):
        trust_score -= 40
        flags.append({
            "type": "ai_generated_content",
            "label": "AI-Generated Media",
            "severity": "high",
            "confidence": 0.95,
            "reason": "Detected YouTube's official @AI badge or synthetic media indicators on page."
        })

    # 3. Engagement Baiting & Typo-masking
    engagement_bait = ["comant", "coment", "comment for link", "dm for link", "comment link", "link in bio"]
    if any(b in text_lower for b in engagement_bait):
        trust_score -= 20
        flags.append({
            "type": "engagement_farming",
            "label": "Link-Bait Strategy",
            "severity": "high",
            "confidence": 0.91,
            "reason": "Uses deliberate typos ('comant') or comment-baiting to push off-platform affiliate links."
        })

    # 4. FTC Disclosures vs E-Commerce Intent
    affiliates = ["meesho", "flipkart", "nykaa", "myntra", "amazon", "haulpack", "haul", "finds"]
    valid_disclosures = ["earns commission", "commission earned", "#ad", "#sponsored", "#paidpartner", "paid partnership"]

    is_commercial = any(a in text_lower or a in url_lower or a in handle_lower for a in affiliates) or is_deal_bot
    has_disclosure = any(d in text_lower for d in valid_disclosures)

    if is_commercial and not has_disclosure:
        trust_score -= 25
        flags.append({
            "type": "missing_ftc_disclosure",
            "label": "Missing Commercial Disclosure",
            "severity": "high",
            "confidence": 0.94,
            "reason": "Promotes affiliate/e-commerce products without mandatory FTC labels or platform badges."
        })
    elif is_commercial and has_disclosure:
        flags.append({
            "type": "disclosed_affiliate",
            "label": "Disclosed Sponsorship",
            "severity": "info",
            "confidence": 0.98,
            "reason": "Commercial relationship is properly disclosed with a platform badge or disclosure tag."
        })

    # Score Normalization
    trust_score = max(trust_score, 15)

    if trust_score < 50:
        summary_reason = "High Risk: Content combines unverified creator ownership, synthetic elements, or undisclosed affiliate intent."
    elif trust_score < 80:
        summary_reason = "Moderate Risk: Commercial or aggregator patterns detected; verify creator source."
    else:
        summary_reason = "Low Risk: Authentic content with valid disclosures."

    if not flags:
        flags.append({
            "type": "organic_content",
            "label": "Organic Content",
            "severity": "info",
            "confidence": 0.90,
            "reason": "No automation, re-upload, or hidden commercial flags detected."
        })

    return {
        "audit_id": "aud_local_v4",
        "status": "quick_done",
        "trust_score": trust_score,
        "ownership_status": ownership_status,
        "summary_reason": summary_reason,
        "flags": flags,
        "preliminary": False
    }


@app.post("/v1/audit/quick-check", response_model=AuditResponse)
def quick_check(req: AuditRequest):
    scraped_text = (req.caption or "")[:3000]
    handle = req.creator_handle or "@unknown"
    video_url = req.video_url

    if client is None:
        return run_local_heuristics(scraped_text, handle, video_url)

    prompt = f"""
    You are an AI authenticity and regulatory compliance auditor.
    Analyze this social media post data:
    Creator Handle: {handle}
    URL: {video_url}
    Scraped Text / DOM: {scraped_text}

    Output STRICT JSON with this exact key structure:
    {{
        "trust_score": 25,
        "ownership_status": "unverified_reupload",
        "summary_reason": "High risk: Content combines unverified creator ownership and undisclosed affiliate intent.",
        "flags": [
            {{
                "type": "flag_code",
                "label": "Display Title",
                "severity": "high",
                "confidence": 0.95,
                "reason": "Explanation of flag."
            }}
        ]
    }}
    """

    try:
        from google.genai import types  # type: ignore
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        analysis = json.loads(response.text)
        return {
            "audit_id": "aud_gemini_104",
            "status": "quick_done",
            "trust_score": int(analysis.get("trust_score", 30)),
            "ownership_status": str(analysis.get("ownership_status", "unverified_reupload")),
            "summary_reason": str(analysis.get("summary_reason", "AI analysis complete.")),
            "flags": analysis.get("flags", []),
            "preliminary": False
        }
    except Exception:
        return run_local_heuristics(scraped_text, handle, video_url)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)