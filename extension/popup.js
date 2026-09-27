document.getElementById('btnScan').addEventListener('click', async () => {
  const btn = document.getElementById('btnScan');
  const resultsCard = document.getElementById('resultsCard');
  const errorMsg = document.getElementById('errorMsg');

  btn.disabled = true;
  btn.innerText = "Analyzing Page...";
  errorMsg.classList.add('hidden');
  resultsCard.classList.add('hidden');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.id) throw new Error("Active tab unaccessible.");

    let pageData = {
      url: tab.url || "",
      caption: tab.title || "",
      handle: "@unknown"
    };

    const isRestricted = tab.url && (
      tab.url.startsWith("chrome://") || 
      tab.url.startsWith("chrome-extension://") || 
      tab.url.startsWith("edge://") || 
      tab.url.startsWith("about:")
    );

    if (!isRestricted) {
      try {
        const execResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            const handleEl = document.querySelector(
              "#channel-name a, #owner-text a, ytd-channel-name, @name, .ytd-channel-name"
            );
            return {
              url: window.location.href,
              caption: (document.body ? document.body.innerText : "").slice(0, 4000),
              handle: handleEl ? handleEl.innerText.trim() : "@unknown"
            };
          }
        });

        if (execResults && execResults[0] && execResults[0].result) {
          pageData = execResults[0].result;
        }
      } catch (e) {
        console.warn("DOM scraping fallback used:", e);
      }
    }

    const res = await fetch("http://127.0.0.1:8000/v1/audit/quick-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_url: pageData.url,
        caption: pageData.caption,
        creator_handle: pageData.handle
      })
    });

    if (!res.ok) throw new Error(`Server returned status code ${res.status}`);

    const audit = await res.json();
    renderResults(audit);

  } catch (err) {
    console.error("Audit Error:", err);
    errorMsg.innerText = "Connection Failed. Ensure 'python main.py' is running.";
    errorMsg.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerText = "Analyze Media Authenticity";
  }
});

function renderResults(audit) {
  document.getElementById('resultsCard').classList.remove('hidden');

  const score = audit.trust_score || 0;
  const scoreVal = document.getElementById('scoreVal');
  const gaugeFill = document.getElementById('gaugeFill');

  scoreVal.innerText = score;

  const maxDash = 283;
  const offset = maxDash - (maxDash * score) / 100;
  gaugeFill.style.strokeDashoffset = offset;

  let themeColor = '#e11d48'; // Rose for low trust
  if (score >= 80) {
    themeColor = '#059669'; // Emerald for high trust
  } else if (score >= 50) {
    themeColor = '#d97706'; // Amber for medium trust
  }

  scoreVal.style.color = themeColor;
  gaugeFill.style.stroke = themeColor;

  const badge = document.getElementById('ownershipBadge');
  const badgeText = document.getElementById('badgeText');
  const statusKey = audit.ownership_status || "unverified_reupload";

  badge.className = `badge badge-${statusKey}`;
  badgeText.innerText = statusKey.replace(/_/g, ' ').toUpperCase();

  document.getElementById('summaryReason').innerText = audit.summary_reason || "Audit completed.";

  const flagsList = document.getElementById('flagsList');
  flagsList.innerHTML = '';

  (audit.flags || []).forEach(flag => {
    const card = document.createElement('div');
    card.className = `flag-card ${flag.severity || 'info'}`;
    card.innerHTML = `
      <div class="flag-title">${flag.label || flag.type}</div>
      <div class="flag-reason">${flag.reason || ''}</div>
    `;
    flagsList.appendChild(card);
  });
}