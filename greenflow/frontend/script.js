/* ── Config ─────────────────────────────────────────────────────── */
const BASE = window.location.port === '8000' ? '' : `http://${window.location.hostname}:8000`;
const API = `${BASE}/api/v1`;

/* ── State ──────────────────────────────────────────────────────── */
let eventCount = 0, scoreSum = 0;
let latestCO2 = null, latestRisk = null;
let execCountdown = 60;

/* ── Clock ──────────────────────────────────────────────────────── */
function tickClock() {
  const clockEl = document.getElementById('clock');
  if (clockEl) {
    clockEl.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
}
setInterval(tickClock, 1000);
tickClock();

/* ── SSE ────────────────────────────────────────────────────────── */
function connectSSE() {
  const pill = document.getElementById('pill');
  const pillText = document.getElementById('pill-text');
  if (!pill || !pillText) return;

  const es = new EventSource(`${API}/stream/events`);
  es.onopen = () => { pillText.textContent = 'Live'; pill.style.cssText = ''; };
  es.onmessage = e => {
    try { handleEvent(JSON.parse(e.data)); } catch (_) { }
  };
  es.onerror = () => {
    pillText.textContent = 'Reconnecting…';
    pill.style.background = 'rgba(239,68,68,.12)';
    pill.style.color = '#ef4444';
    pill.style.borderColor = 'rgba(239,68,68,.3)';
    es.close();
    setTimeout(connectSSE, 3000);
  };
}

function handleEvent(data) {
  eventCount++;
  if (data.carbon_score !== undefined) scoreSum += data.carbon_score;

  const eventsEl = document.getElementById('kpi-events');
  const scoreEl = document.getElementById('kpi-score');
  const co2El = document.getElementById('kpi-co2');
  const tempEl = document.getElementById('kpi-temp');
  const aqiEl = document.getElementById('kpi-aqi');
  const feedCountEl = document.getElementById('feed-count');

  if (eventsEl) eventsEl.textContent = eventCount;
  if (scoreEl) scoreEl.textContent = eventCount ? (scoreSum / eventCount).toFixed(3) : '—';
  
  if (data.co2_ppm !== undefined) {
    latestCO2 = data.co2_ppm;
    if (co2El) co2El.textContent = data.co2_ppm.toFixed(1);
  }
  if (data.temperature_c !== undefined && tempEl)
    tempEl.textContent = data.temperature_c.toFixed(1) + ' °C';
  if (data.aqi !== undefined && aqiEl)
    aqiEl.textContent = data.aqi;

  if (feedCountEl) feedCountEl.textContent = eventCount + ' events';

  const feed = document.getElementById('feed');
  if (feed) {
    const score = data.carbon_score ?? null;
    const cls = score === null ? 'score-lo' : score >= .6 ? 'score-hi' : score >= .3 ? 'score-mid' : 'score-lo';
    const item = document.createElement('div');
    item.className = 'feed-item';
    item.innerHTML = `
      <span class="feed-source">${data.source || 'sensor'}</span>
      <span style="color:var(--muted2);flex:1;font-size:.75rem">${new Date((data.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}</span>
      ${score !== null ? `<span class="feed-score ${cls}">${score.toFixed(3)}</span>` : ''}
    `;
    feed.prepend(item);
    while (feed.children.length > 60) feed.lastChild.remove();
  }
}

/* ════════════════════════════════════════════════════════════════
   1. CO₂ PREDICTION FETCH
════════════════════════════════════════════════════════════════ */
async function fetchPrediction() {
  try {
    const r = await fetch(`${API}/analytics/prediction/co2`);
    if (!r.ok) return;
    const d = await r.json();

    latestCO2 = d.current_co2;
    const predValEl = document.getElementById('pred-value');
    const currCo2El = document.getElementById('current-co2');
    const trendLabelEl = document.getElementById('trend-label');
    const confFillEl = document.getElementById('conf-fill');
    const confPctEl = document.getElementById('conf-pct');
    const badge = document.getElementById('pred-badge');
    const arrow = document.getElementById('trend-arrow');
    const kpiCo2El = document.getElementById('kpi-co2');

    if (predValEl) predValEl.innerHTML = `${d.predicted_co2_30min.toFixed(1)}<span class="co2-unit">ppm</span>`;
    if (currCo2El) currCo2El.textContent = d.current_co2.toFixed(1);
    if (trendLabelEl) trendLabelEl.textContent = d.trend;

    const conf = Math.round(d.confidence * 100);
    if (confFillEl) confFillEl.style.width = conf + '%';
    if (confPctEl) confPctEl.textContent = conf + '%';

    if (badge) {
      const diff = d.predicted_co2_30min - d.current_co2;
      badge.textContent = diff > 0 ? `+${diff.toFixed(1)} ▲` : `${diff.toFixed(1)} ▼`;
      badge.className = 'card-badge ' + (diff > 5 ? 'danger' : diff > 0 ? 'warn' : 'live');
    }

    if (arrow) {
      if (d.trend === 'increasing') { arrow.textContent = '↑'; arrow.className = 'trend-arrow up'; }
      else if (d.trend === 'decreasing') { arrow.textContent = '↓'; arrow.className = 'trend-arrow down'; }
      else { arrow.textContent = '→'; arrow.className = 'trend-arrow stable'; }
    }

    if (kpiCo2El) kpiCo2El.textContent = d.current_co2.toFixed(1);
    flashUpdate('co2-pred-card');
    if (typeof updateSimulatorCalc === 'function') updateSimulatorCalc();
  } catch (e) { console.warn('Prediction fetch:', e); }
}

/* ════════════════════════════════════════════════════════════════
   2. RISK METER
════════════════════════════════════════════════════════════════ */
const RISK_COLORS = {
  SAFE: '#22c55e',
  MODERATE: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
};

function setGaugeAngle(score) {
  const needle = document.getElementById('gauge-needle');
  if (needle) {
    const angle = -90 + (score / 100) * 180;
    needle.setAttribute('transform', `rotate(${angle}, 90, 100)`);
  }
}

async function fetchRisk() {
  try {
    const r = await fetch(`${API}/analytics/risk-score`);
    if (!r.ok) return;
    const d = await r.json();
    latestRisk = d;

    const score = d.current_score ?? 0;
    const levelRaw = (d.safety_level || 'SAFE').toUpperCase();
    const level = ['SAFE', 'MODERATE', 'HIGH', 'CRITICAL'].includes(levelRaw) ? levelRaw : 'SAFE';
    const color = RISK_COLORS[level];

    const scoreEl = document.getElementById('gauge-score');
    const levelEl = document.getElementById('gauge-level');
    const riskBadge = document.getElementById('risk-badge');
    const metaRiskEl = document.getElementById('meta-risk');

    if (scoreEl) { scoreEl.textContent = score.toFixed(0); scoreEl.style.color = color; }
    if (levelEl) { levelEl.textContent = level; levelEl.style.color = color; }

    if (riskBadge) {
      riskBadge.textContent = level;
      riskBadge.className = 'card-badge ' + ({ 'SAFE': 'live', 'MODERATE': 'warn', 'HIGH': 'warn', 'CRITICAL': 'danger' }[level] || 'live');
    }

    setGaugeAngle(score);

    if (metaRiskEl) { metaRiskEl.textContent = level; metaRiskEl.style.color = color; }
    flashUpdate('risk-card');
  } catch (e) { console.warn('Risk fetch:', e); }
}

/* ════════════════════════════════════════════════════════════════
   3. AI RECOMMENDATION
════════════════════════════════════════════════════════════════ */
const REC_ICONS = {
  'traffic': '🚗', 'ventil': '💨', 'advisory': '📢',
  'emergency': '🚨', 'policy': '📋', 'default': '✅'
};

function getRecIcon(text) {
  const t = text.toLowerCase();
  for (const [k, v] of Object.entries(REC_ICONS)) {
    if (t.includes(k)) return v;
  }
  return '✅';
}

async function fetchRecommendation() {
  try {
    const r = await fetch(`${API}/analytics/recommendation`);
    if (!r.ok) return;
    const d = await r.json();

    const panel = document.getElementById('rec-panel');
    const levelEl = document.getElementById('rec-action-level');
    const list = document.getElementById('rec-list');
    const explEl = document.getElementById('rec-explanation');
    const badge = document.getElementById('rec-update-badge');

    if (!panel || !levelEl || !list) return;

    const levelRaw = (d.action_level || 'safe').toLowerCase();
    levelEl.className = 'rec-action-level ' + levelRaw;
    levelEl.innerHTML = `<span>●</span> ${d.action_level}`;

    if (levelRaw === 'critical') panel.classList.add('emergency');
    else panel.classList.remove('emergency');

    list.innerHTML = '';
    (d.recommendations || []).slice(0, 4).forEach(rec => {
      const div = document.createElement('div');
      div.className = 'rec-item';
      div.innerHTML = `<span class="rec-icon">${getRecIcon(rec)}</span><span>${rec}</span>`;
      list.appendChild(div);
    });

    if (explEl) explEl.innerHTML = `<strong>AI Analysis:</strong> ${d.explanation || '—'}`;
    if (badge) {
      badge.textContent = new Date().toLocaleTimeString();
      badge.className = 'card-badge live';
    }
  } catch (e) { console.warn('Rec fetch:', e); }
}

/* ════════════════════════════════════════════════════════════════
   4. WHAT-IF SIMULATOR
════════════════════════════════════════════════════════════════ */
let _simTimer = null;

function updateSimulator() {
  const tSlider = document.getElementById('traffic-slider');
  const vSlider = document.getElementById('ventilation-slider');
  const iSlider = document.getElementById('industry-slider');
  if (!tSlider || !vSlider || !iSlider) return;

  const tVal = parseInt(tSlider.value);
  const vVal = parseInt(vSlider.value);
  const iVal = parseInt(iSlider.value);
  
  document.getElementById('traffic-val').textContent = tVal + '%';
  document.getElementById('ventilation-val').textContent = vVal + '%';
  document.getElementById('industry-val').textContent = iVal + '%';

  clearTimeout(_simTimer);
  _simTimer = setTimeout(() => runSimulation(tVal, vVal, iVal), 400);
}

async function runSimulation(tPct, vPct, iPct) {
  const badge = document.getElementById('sim-badge');
  if (badge) {
    badge.textContent = '⏳ Calculating…';
    badge.className = 'card-badge warn';
  }

  const safetyColor = r => r < 30 ? '#22c55e' : r < 55 ? '#f59e0b' : r < 75 ? '#f97316' : '#ef4444';

  try {
    const res = await fetch(`${API}/simulate/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        traffic_reduction_pct: tPct,
        ventilation_increase_pct: vPct,
        industry_reduction_pct: iPct,
      })
    });
    if (!res.ok) throw new Error(res.status);
    const d = await res.json();

    const simCo2El = document.getElementById('sim-co2');
    const simCo2DeltaEl = document.getElementById('sim-co2-delta');
    const simRiskEl = document.getElementById('sim-risk');
    const simRiskDeltaEl = document.getElementById('sim-risk-delta');
    const simSavingEl = document.getElementById('sim-saving');
    const simSafetyEl = document.getElementById('sim-safety');

    const rColor = safetyColor(d.new_risk_score);
    if (simCo2El) simCo2El.textContent = d.new_predicted_co2.toFixed(1);
    if (simCo2DeltaEl) {
      const co2Delta = d.new_predicted_co2 - d.baseline_co2;
      simCo2DeltaEl.innerHTML = `<span class="${co2Delta <= 0 ? 'delta-pos' : 'delta-neg'}">${co2Delta <= 0 ? '↓' : '↑'} ${Math.abs(co2Delta).toFixed(1)} ppm</span>`;
    }

    if (simRiskEl) { simRiskEl.textContent = d.new_risk_score.toFixed(1); simRiskEl.style.color = rColor; }
    if (simRiskDeltaEl) {
      const rDelta = d.new_risk_score - d.baseline_risk;
      simRiskDeltaEl.innerHTML = `<span class="${rDelta <= 0 ? 'delta-pos' : 'delta-neg'}">${rDelta <= 0 ? '↓' : '↑'} ${Math.abs(rDelta).toFixed(1)} pts</span>`;
    }

    if (simSavingEl) simSavingEl.textContent = d.co2_reduction_ppm.toFixed(1);
    if (simSafetyEl) { simSafetyEl.textContent = d.alert_level; simSafetyEl.style.color = rColor; }

    let summaryEl = document.getElementById('sim-summary');
    if (!summaryEl && simSavingEl) {
      summaryEl = document.createElement('div');
      summaryEl.id = 'sim-summary';
      summaryEl.style.cssText = 'margin-top:.9rem;padding:.75rem 1rem;border-radius:8px;background:rgba(34,197,94,.06);border:1px solid rgba(34,197,94,.15);font-size:.78rem;line-height:1.6;color:var(--muted2);animation:fadeSlide .4s ease';
      simSavingEl.closest('.sim-result').after(summaryEl);
    }
    if (summaryEl) summaryEl.innerHTML = `<strong style="color:var(--accent)">📊 AI Impact Analysis</strong><br/>${d.impact_summary}`;

    if (badge) {
      badge.textContent = '✅ API Result';
      badge.className = 'card-badge live';
    }
  } catch (err) {
    if (badge) {
      badge.textContent = '⚠️ Error';
      badge.className = 'card-badge danger';
    }
    console.warn('Simulate API error:', err);
  }
}

/* ════════════════════════════════════════════════════════════════
   5. EXECUTIVE SUMMARY
════════════════════════════════════════════════════════════════ */
async function fetchExecutiveSummary() {
  const body = document.getElementById('exec-body');
  if (!body) return;
  body.classList.add('refreshing');

  try {
    const r = await fetch(`${API}/chatbot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: 'Provide a 3-sentence executive briefing: current CO₂ status, risk level, and the top recommended action. Be concise and data-backed.'
      })
    });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();

    body.classList.remove('refreshing');
    typeWriter(body, d.answer || 'Summary unavailable.');
    const updatedEl = document.getElementById('meta-updated');
    const co2StatusEl = document.getElementById('meta-co2-status');
    if (updatedEl) updatedEl.textContent = new Date().toLocaleTimeString();
    if (co2StatusEl) co2StatusEl.textContent = latestCO2 ? latestCO2.toFixed(1) + ' ppm' : '—';
  } catch (e) {
    body.classList.remove('refreshing');
    body.textContent = 'Executive summary temporarily unavailable.';
  }
}

function typeWriter(el, text, speed = 18) {
  el.textContent = '';
  el.classList.add('exec-typing');
  let i = 0;
  const t = setInterval(() => {
    el.textContent += text[i++];
    if (i >= text.length) { clearInterval(t); el.classList.remove('exec-typing'); }
  }, speed);
}

function startExecCountdown() {
  execCountdown = 60;
  const ring = document.getElementById('countdown-ring');
  const countEl = document.getElementById('exec-countdown');
  if (!ring || !countEl) return;
  const circumference = 56.5;

  const tick = setInterval(() => {
    execCountdown--;
    countEl.textContent = execCountdown;
    ring.style.strokeDashoffset = circumference * (1 - execCountdown / 60);
    if (execCountdown <= 0) {
      clearInterval(tick);
      fetchExecutiveSummary().then(() => startExecCountdown());
    }
  }, 1000);
}

/* ── Helpers ────────────────────────────────────────────────────── */
function flashUpdate(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('just-updated');
  void el.offsetWidth; // reflow
  el.classList.add('just-updated');
}

/* ── AI Chat ────────────────────────────────────────────────────── */
async function askQuestion() {
  const questionEl = document.getElementById('user-question');
  if (!questionEl) return;
  const question = questionEl.value.trim();
  if (!question) return;

  const btn = document.getElementById('ask-btn');
  const answerBox = document.getElementById('answer-box');
  if (!btn || !answerBox) return;

  btn.disabled = true;
  btn.textContent = '⏳ Thinking…';
  answerBox.style.display = 'block';
  answerBox.textContent = '';
  try {
    const res = await fetch(`${API}/chatbot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: question }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    answerBox.innerHTML = `<strong style="color:var(--accent)">Answer</strong><br/>${data.answer}`;
  } catch (err) {
    answerBox.innerHTML = `<span style="color:var(--danger)">Error: ${err.message}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ Ask AI';
  }
}

/* ── Polling ────────────────────────────────────────────────────── */
async function pollAll() {
  await Promise.allSettled([
    fetchPrediction(),
    fetchRisk(),
    fetchRecommendation(),
  ]);
}

/* ── Boot ───────────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  connectSSE();
  pollAll();                            // immediate first load
  setInterval(pollAll, 15000);         // refresh every 15s
  updateSimulator();                    // init simulator display
  fetchExecutiveSummary().then(() => startExecCountdown()); 

  const qInput = document.getElementById('user-question');
  if (qInput) {
    qInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && e.ctrlKey) askQuestion();
    });
  }
});
