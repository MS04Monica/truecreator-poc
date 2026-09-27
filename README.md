TrueCreator Scan ⚡
AI-Powered Media Authenticity & Regulatory Compliance Auditing Platform

A Chrome Extension and FastAPI Backend designed to detect undisclosed affiliate marketing, synthetic AI media, and bot re-uploader patterns in real time.

📖 Overview
TrueCreator Scan is an end-to-end audit system for modern social media streams (specifically YouTube Shorts). As affiliate farming, synthetic deepfakes, and re-uploaded aggregator content saturate digital feeds, TrueCreator provides consumers, platforms, and regulatory compliance teams with an instantaneous Trust Index (0–100) score and an itemized breakdown of compliance flags.

The system combines Google Gemini 1.5 Flash for deep multimodal contextual reasoning with a zero-latency local regex heuristic fallback engine, ensuring reliable, uninterrupted audits even under network throttling or API rate limits.

✨ Key Features
FTC Commercial Disclosure Audit: Automatically verifies if sponsored videos or affiliate links (Meesho, Flipkart, Amazon, Haulpack, etc.) include explicit tags (#ad, #sponsored) or native YouTube commercial disclosure badges ("Earns commission").

Synthetic Media & @AI Detection: Scans DOM metadata and channel badges for official YouTube AI tags and synthetic media indicators.

Re-uploader & Bot Aggregator Profiling: Identifies deal-bait channels, spam keywords (deals, duniya, loot, finds), and unverified content syndicators.

Engagement Farming & Typo-Bait Detection: Detects deceptive comments-baiting strategies (e.g., deliberate typos like "comant for link" or "DM for link").

Apple & Perplexity-Inspired Minimalist UI: Designed with a clean, executive light-mode aesthetic, SVG radial trust gauges, dynamic status badges, and expandable factor callouts.

Resilient Dual-Layer Backend: Runs high-accuracy LLM evaluations via Gemini 1.5 Flash, automatically falling back to deterministic local rule engines if offline or unauthenticated.

🛠️ Tech Stack
Backend (/backend)
Framework: Python 3.10+ & FastAPI

AI Engine: google-genai (Gemini 1.5 Flash)

Configuration: python-dotenv for secure environment variable management

Server: Uvicorn ASGI Server

Chrome Extension (/extension)
Manifest Version: Chrome Manifest V3

Frontend: HTML5, CSS3 (Custom Variables, SVG Gauges, CSS Animations)

DOM Scraper: Asynchronous chrome.scripting.executeScript for real-time page metadata extraction

📁 Repository Structure
Plaintext
truecreator-poc/
├── .gitignore               # Excludes venv, __pycache__, and .env secrets
├── README.md                # Project documentation
├── backend/
│   ├── main.py              # FastAPI server, Gemini client & local heuristic audit logic
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # Environment secrets (GEMINI_API_KEY)
└── extension/
    ├── manifest.json        # Extension permissions and background config
    ├── popup.html           # Minimalist interface layout and styles
    └── popup.js             # ActiveTab DOM scraper and API client
🚀 Quick Start Guide
Prerequisites
Python 3.10+

Google Chrome Browser

(Optional) Google Gemini API Key (Obtain from Google AI Studio)

1. Backend Setup
Navigate to the backend folder:

Bash
cd backend
Create and activate a virtual environment:

Windows:

PowerShell
python -m venv venv
.\venv\Scripts\activate
macOS / Linux:

Bash
python3 -m venv venv
source venv/bin/activate
Install dependencies:

Bash
pip install -r requirements.txt
Configure Environment Secrets:
Create a file named .env inside the backend/ directory:

Code snippet
GEMINI_API_KEY=your_actual_gemini_api_key_here
(Note: If no API key is provided, the backend automatically defaults to local rule-based heuristics).

Start the FastAPI server:

Bash
python main.py
The server will start at [http://127.0.0.1:8000](http://127.0.0.1:8000).

2. Chrome Extension Setup
Open Google Chrome and navigate to chrome://extensions/.

Enable Developer mode in the top-right corner.

Click Load unpacked.

Select the extension/ folder from this repository.

The TrueCreator Scan icon will appear in your Chrome extensions menu.

🧪 API Endpoints
POST /v1/audit/quick-check
Accepts scraped page DOM metadata and returns a structured compliance audit.

Request Body
JSON
{
  "video_url": "https://www.youtube.com/shorts/sample123",
  "caption": "Check out this amazing haul! Earns commission. Comment for link!",
  "creator_handle": "@DealWaliDuniya"
}
Response Body
JSON
{
  "audit_id": "aud_gemini_104",
  "status": "quick_done",
  "trust_score": 45,
  "ownership_status": "bot_aggregator",
  "summary_reason": "High Risk: Content combines unverified creator ownership and undisclosed affiliate intent.",
  "flags": [
    {
      "type": "unverified_authorship",
      "label": "Unverified Re-uploader",
      "severity": "medium",
      "confidence": 0.88,
      "reason": "Channel handle '@DealWaliDuniya' matches known deal-aggregator patterns."
    },
    {
      "type": "engagement_farming",
      "label": "Link-Bait Strategy",
      "severity": "high",
      "confidence": 0.91,
      "reason": "Uses comment-baiting to push off-platform affiliate links."
    }
  ],
  "preliminary": false
}
🛡️ License
This project is licensed under the MIT License — see the LICENSE file for details.