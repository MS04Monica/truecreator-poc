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
    severity: str
    confidence: float
    reason: str

class AuditResponse(BaseModel):
    audit_id: str
    status: str
    trust_score: int
    ownership_status: str
    summary_reason: str
    flags: List[Flag]
    preliminary: bool

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = None

if GEMINI_API_KEY:
    try:
        from google import genai  # type: ignore
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        client = None


def run_local_heuristics(text: str, handle: str, url: str) -> dict:
    text_lower = text.lower()

    # Prevent fake static 95s if browser extraction is completely blank
    if not text_lower.strip():
        return {
            "audit_id": "aud_local_v6",
            "status": "quick_done",
            "trust_score": 30,
            "ownership_status": "unverified_reupload",
            "summary_reason": "Low Confidence: Unable to extract text data from browser window.",
            "flags": [{
                "type": "scraping_failed",
                "label": "Missing Page Data",
                "severity": "high",
                "confidence": 1.0,
                "reason": "Could not extract readable DOM text from current tab."
            }],
            "preliminary": False
        }

    flags = []
    trust_score = 95
    ownership_status = "verified_original"

    # 1. Aggregator / Deal Bot Handle Detection
    deal_keywords = ["deal", "deals", "duniya", "loot", "finds", "offers", "store", "fashionhub", "bargain"]
    if any(k in text_lower for k in deal_keywords):
        ownership_status = "bot_aggregator"
        trust_score -= 25
        flags.append({
            "type": "unverified_authorship",
            "label": "Unverified Deal Aggregator",
            "severity": "medium",
            "confidence": 0.90,
            "reason": "Channel text matches deal-aggregator patterns rather than original creator profiles."
        })

    # 2. AI Content Detection
    if any(p in text_lower for p in ["@ai", "@ ai", "ai-generated", "synthetic"]):
        trust_score -= 40
        flags.append({
            "type": "ai_generated_content",
            "label": "AI-Generated Media",
            "severity": "high",
            "confidence": 0.95,
            "reason": "Detected YouTube official @AI badge or synthetic media tags."
        })

    # 3. Typo-baiting / Comment Farming
    if any(b in text_lower for b in ["comant", "coment", "comment for link", "dm for link", "link in bio"]):
        trust_score -= 20
        flags.append({
            "type": "engagement_farming",
            "label": "Link-Bait Strategy",
            "severity": "high",
            "confidence": 0.92,
            "reason": "Uses deliberate typo comment-baiting ('comant for link') to redirect viewers off-platform."
        })

    # 4. FTC / E-Commerce Disclosures
    if any(a in text_lower for a in ["saree", "meesho", "flipkart", "amazon", "haulpack", "myntra"]):
        if not any(d in text_lower for d in ["#ad", "#sponsored", "earns commission", "paid partnership"]):
            trust_score -= 25
            flags.append({
                "type": "missing_ftc_disclosure",
                "label": "Missing Commercial Disclosure",
                "severity": "high",
                "confidence": 0.94,
                "reason": "Promotes affiliate/e-commerce products without required disclosure labels (#ad / #sponsored)."
            })

    trust_score = max(trust_score, 10)

    if trust_score < 50:
        summary_reason = "High Risk: Content combines aggregator traits, synthetic markers, or undisclosed commercial intent."
    elif trust_score < 80:
        summary_reason = "Moderate Risk: Commercial intent detected without full FTC disclosures."
    else:
        summary_reason = "Low Risk: Authentic creator content with valid disclosures."

    if not flags:
        flags.append({
            "type": "organic_content",
            "label": "Organic Content",
            "severity": "info",
            "confidence": 0.90,
            "reason": "No automation, re-upload, or hidden commercial flags detected."
        })

    return {
        "audit_id": "aud_local_v6",
        "status": "quick_done",
        "trust_score": trust_score,
        "ownership_status": ownership_status,
        "summary_reason": summary_reason,
        "flags": flags,
        "preliminary": False
    }


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "TrueCreator API Local PoC"
    }


@app.post("/v1/audit/quick-check", response_model=AuditResponse)
def quick_check(req: AuditRequest):
    scraped_text = (req.caption or "")[:5000]
    handle = req.creator_handle or "@unknown"
    video_url = req.video_url

    if client is None:
        return run_local_heuristics(scraped_text, handle, video_url)

    prompt = f"""
    You are an AI authenticity auditor evaluating a YouTube Short.
    URL: {video_url}
    Scraped Page Content: {scraped_text}

    Evaluate regulatory disclosures, AI generation badges, and deal-bot aggregator patterns.
    Output STRICT JSON with key structure:
    {{
        "trust_score": 15,
        "ownership_status": "bot_aggregator",
        "summary_reason": "High risk: Undisclosed affiliate link pushing from aggregator profile.",
        "flags": [
            {{
                "type": "missing_ftc_disclosure",
                "label": "Missing FTC Disclosure",
                "severity": "high",
                "confidence": 0.95,
                "reason": "Promotes affiliate link without disclosure."
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
            "audit_id": "aud_gemini_106",
            "status": "quick_done",
            "trust_score": int(analysis.get("trust_score", 30)),
            "ownership_status": str(analysis.get("ownership_status", "unverified_reupload")),
            "summary_reason": str(analysis.get("summary_reason", "AI evaluation complete.")),
            "flags": analysis.get("flags", []),
            "preliminary": False
        }
    except Exception:
        return run_local_heuristics(scraped_text, handle, video_url)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)