document.addEventListener('DOMContentLoaded', () => {
  const btnScan = document.getElementById('btnScan');
  const resultsCard = document.getElementById('resultsCard');
  const errorMsg = document.getElementById('errorMsg');

  if (!btnScan) return;

  btnScan.addEventListener('click', async () => {
    btnScan.disabled = true;
    btnScan.innerText = "Analyzing Media...";
    if (errorMsg) errorMsg.classList.add('hidden');
    if (resultsCard) resultsCard.classList.add('hidden');

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) throw new Error("Cannot access active browser tab.");

      // Grab entire rendered page text directly—no fragile selectors
      const execResults = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          const fullText = document.body ? document.body.innerText : "";
          return {
            url: window.location.href,
            caption: fullText.slice(0, 6000),
            handle: fullText.slice(0, 6000)
          };
        }
      });

      const pageData = execResults?.[0]?.result || { url: tab.url, caption: "", handle: "" };

      // Localhost FastAPI Endpoint
      const LOCAL_API_URL = "http://127.0.0.1:8000/v1/audit/quick-check";
      
      const res = await fetch(LOCAL_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_url: pageData.url,
          caption: pageData.caption,
          creator_handle: pageData.handle
        })
      });

      if (!res.ok) throw new Error(`Local backend returned error code ${res.status}`);

      const auditData = await res.json();
      renderResults(auditData);

    } catch (err) {
      console.error("Audit Error:", err);
      if (errorMsg) {
        errorMsg.innerText = err.message || "Failed to connect to local backend (127.0.0.1:8000).";
        errorMsg.classList.remove('hidden');
      }
    } finally {
      btnScan.disabled = false;
      btnScan.innerText = "Analyze Media Authenticity";
    }
  });
});

function renderResults(audit) {
  const resultsCard = document.getElementById('resultsCard');
  const scoreVal = document.getElementById('scoreVal');
  const gaugeFill = document.getElementById('gaugeFill');
  const badge = document.getElementById('ownershipBadge');
  const badgeText = document.getElementById('badgeText');
  const summaryReason = document.getElementById('summaryReason');
  const flagsList = document.getElementById('flagsList');
  const API_URL = "https://truecreator-poc.vercel.app/v1/audit/quick-check";

  if (!resultsCard) return;
  resultsCard.classList.remove('hidden');

  const score = Math.max(0, Math.min(100, parseInt(audit.trust_score) || 0));
  if (scoreVal) scoreVal.innerText = score;

  if (gaugeFill) {
    const maxDash = 283;
    const offset = maxDash - (maxDash * score) / 100;
    gaugeFill.style.strokeDashoffset = offset;

    let themeColor = '#f43f5e'; // Red (<50)
    if (score >= 80) themeColor = '#10b981'; // Green (>=80)
    else if (score >= 50) themeColor = '#f59e0b'; // Amber (50-79)

    gaugeFill.style.stroke = themeColor;
    if (scoreVal) scoreVal.style.color = themeColor;
  }

  if (badge && badgeText) {
    const statusKey = (audit.ownership_status || "unverified_reupload").toLowerCase();
    badge.className = `badge badge-${statusKey}`;
    badgeText.innerText = statusKey.replace(/_/g, ' ').toUpperCase();
  }

  if (summaryReason) {
    summaryReason.innerText = audit.summary_reason || "Audit evaluation complete.";
  }

  if (flagsList) {
    flagsList.innerHTML = '';
    const flags = Array.isArray(audit.flags) ? audit.flags : [];

    flags.forEach(flag => {
      const card = document.createElement('div');
      card.className = `flag-card ${flag.severity || 'info'}`;
      card.innerHTML = `
        <div class="flag-title">${escapeHtml(flag.label || flag.type)}</div>
        <div class="flag-reason">${escapeHtml(flag.reason || '')}</div>
      `;
      flagsList.appendChild(card);
    });
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}