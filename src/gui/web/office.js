const WS_URL = `ws://${location.host}/ws/office`;

// ── Agent color map ──
const AGENT_COLORS = {};
function agentColor(role) {
  if (!role) return 'var(--dim)';
  if (AGENT_COLORS[role]) return AGENT_COLORS[role];
  let hash = 0;
  for (let i = 0; i < role.length; i++) hash = role.charCodeAt(i) + ((hash << 5) - hash);
  AGENT_COLORS[role] = `hsl(${Math.abs(hash) % 360}, 60%, 65%)`;
  return AGENT_COLORS[role];
}

// ── Agent personality tags ──
const PERSONALITY_TAGS = {
  'strategy-manager': ['Strategy', 'Data-driven'],
  'product-manager': ['Product', 'UX'],
  'project-manager': ['Timeline', 'Scope'],
  'fullstack-architect': ['Architecture', 'Schema'],
  'backend-senior': ['Backend', 'API'],
  'frontend-senior': ['Frontend', 'Components'],
  'qa-engineer': ['QA', 'Testing'],
  'infra-expert': ['Infra', 'CI/CD'],
  'data-engineer': ['Data', 'Pipeline'],
  'doc-secretary': ['Docs', 'Notion'],
  'external-advisor': ["Devil's Advocate", 'Critical'],
  'codegen-developer': ['Codegen', 'Multi-repo'],
  'notion-editor': ['Notion', 'Block Edit'],
};

// ── Crew membership map ──
const CREW_MAP = {
  'strategy-manager': 'Research', 'product-manager': 'Planning', 'project-manager': 'Planning',
  'fullstack-architect': 'Architect', 'backend-senior': 'Architect',
  'frontend-senior': 'Frontend', 'qa-engineer': 'QA', 'infra-expert': 'Infra',
  'data-engineer': 'Data', 'doc-secretary': 'Documentation', 'external-advisor': 'Review',
  'codegen-developer': 'Codegen', 'notion-editor': 'NotionEdit',
};

// ── State ──
const state = {
  agents: {},
  totalTokens: 0,
  activeCrew: null,
  startTime: null,
  autoScroll: true,
  agentStats: {},  // role -> {tasks, tasksDone, tokens, errors, lastSpeech}
};

// ── Init ──
async function init() {
  const [agents, crews] = await Promise.all([
    fetch('/api/agents').then(r => r.json()),
    fetch('/api/crews').then(r => r.json()),
  ]);

  const loungeEl = document.getElementById('lounge-agents');
  agents.forEach(a => {
    const id = a.agent_id || a.role;
    const role = a.role || id;
    const crew = a.crew || CREW_MAP[a.agent_id] || '';
    const color = agentColor(role);
    const initials = shortName(role).slice(0, 2);
    const el = document.createElement('div');
    el.className = 'agent-av';
    el.title = role;
    el.innerHTML = `<div class="av-circle" style="background:${color}">${initials}<span class="av-status"></span></div><div class="av-name">${shortName(role)}</div><div class="av-speech"></div>`;
    el.onclick = () => openProfile(role);
    loungeEl.appendChild(el);
    state.agents[role] = { role, crew, status: 'idle', speech: '', desk_el: el, icon_el: el.querySelector('.av-status'), speech_el: el.querySelector('.av-speech'), agentId: id, zone: 'lounge' };
    state.agentStats[role] = { tasks: 0, tasksDone: 0, tokens: 0, errors: 0, lastSpeech: '', history: [] };
  });

  buildDashboard();

  const ctrlEl = document.getElementById('controls');
  crews.forEach(c => {
    if (['codegen', 'notion-edit', 'notion'].includes(c.name)) return;
    const btn = document.createElement('button');
    btn.textContent = c.name;
    btn.title = c.description;
    btn.onclick = () => runCrew(c.name, btn);
    ctrlEl.appendChild(btn);
  });

  // Auto-scroll detection
  const msgList = document.getElementById('msg-list');
  msgList.addEventListener('scroll', () => {
    const atBottom = msgList.scrollHeight - msgList.scrollTop - msgList.clientHeight < 60;
    state.autoScroll = atBottom;
    document.getElementById('scroll-btn').classList.toggle('visible', !atBottom);
  });

  connectWS();
}

// ── WebSocket ──
function connectWS() {
  const ws = new WebSocket(WS_URL);
  const statusEl = document.getElementById('conn-status');
  ws.onopen = () => { statusEl.textContent = 'connected'; statusEl.style.color = 'var(--green)'; };
  ws.onclose = () => { statusEl.textContent = 'disconnected'; statusEl.style.color = 'var(--red)'; setTimeout(connectWS, 2000); };
  ws.onerror = () => ws.close();
  ws.onmessage = (e) => handleEvent(JSON.parse(e.data));
}

// ── Event Handler ──
function handleEvent(ev) {
  const [cat, action] = ev.type.split('.');

  addMessage(ev, cat, action);

  if (cat === 'crew') {
    if (action === 'started') {
      state.activeCrew = ev.crew;
      state.startTime = Date.now();
      updateTimer();
      updateMeeting(ev.crew, 'In progress...');
    } else if (action === 'completed' || action === 'failed') {
      if (ev.payload?.tokens?.total) state.totalTokens += ev.payload.tokens.total;
      updateMeeting(ev.crew, action === 'completed' ? 'Completed' : `Failed: ${ev.payload?.error || ''}`);
      state.activeCrew = null;
      state.startTime = null;
      resetAllDesks();
      updateButtons(false);
    }
    updateTokens();
  }

  if (cat === 'agent') {
    const a = findAgent(ev.agent);
    if (!a) return;
    const s = state.agentStats[a.role];
    if (action === 'started') {
      setAgentStatus(a, 'working');
      if (s) s.tasks++;
    } else if (action === 'completed') {
      setAgentStatus(a, 'speaking');
      a.speech = truncate(ev.payload?.text, 80);
      a.speech_el.textContent = a.speech;
      if (s) { s.tasksDone++; s.lastSpeech = truncate(ev.payload?.text, 60); s.history.push(truncate(ev.payload?.text, 120)); if (s.history.length > 20) s.history.shift(); }
      setTimeout(() => setAgentStatus(a, 'idle'), 3000);
    } else if (action === 'error') {
      setAgentStatus(a, 'error');
      if (s) s.errors++;
      showErrorVignette();
    }
    updateDashboard();
  }

  if (cat === 'tool') {
    const a = findAgent(ev.agent);
    if (!a) return;
    if (action === 'started') { setAgentStatus(a, 'tool'); flashToolHighlight(a); }
    else if (action === 'finished') setAgentStatus(a, 'working');
    else if (action === 'error') { setAgentStatus(a, 'error'); showErrorVignette(); }
  }

  if (cat === 'llm') {
    if (ev.payload?.tokens) {
      const t = ev.payload.tokens;
      const total = (t.prompt || 0) + (t.completion || 0);
      if (total) state.totalTokens += total;
      if (ev.agent) { const a = findAgent(ev.agent); if (a) { const s = state.agentStats[a.role]; if (s) s.tokens += total; } }
      updateTokens();
      updateDashboard();
    }
  }
}

// ── Messenger rendering ──
function addMessage(ev, cat, action) {
  const list = document.getElementById('msg-list');

  if (cat === 'crew') {
    if (action === 'started') {
      list.appendChild(createSeparator());
      list.appendChild(createCrewBanner(`${ev.crew} meeting started`));
    } else if (action === 'completed') {
      const elapsed = ev.payload?.elapsed_sec ? ` (${Math.round(ev.payload.elapsed_sec)}s)` : '';
      list.appendChild(createCrewBanner(`${ev.crew} completed${elapsed}`));
      list.appendChild(createSeparator());
    } else if (action === 'failed') {
      list.appendChild(createCrewBanner(`${ev.crew} FAILED: ${ev.payload?.error || 'unknown'}`, true));
      list.appendChild(createSeparator());
    }
  } else if (cat === 'agent') {
    if (action === 'completed' && ev.payload?.text) {
      list.appendChild(createSpeechBubble(ev.agent, ev.payload.text));
    } else if (action === 'error') {
      list.appendChild(createErrorBubble(ev.agent, ev.payload?.error || 'Unknown error'));
    }
  } else if (cat === 'llm') {
    if (action === 'completed' && ev.payload?.text) {
      list.appendChild(createThinkingBubble(ev.agent || state.activeCrew, ev.payload.text));
    }
  } else if (cat === 'tool') {
    if (action === 'started') {
      list.appendChild(createSystemMsg(`${shortName(ev.agent)} uses ${ev.tool || 'tool'}`));
    } else if (action === 'error') {
      list.appendChild(createErrorBubble(ev.agent, `Tool ${ev.tool}: ${ev.payload?.error || 'error'}`));
    }
  } else if (cat === 'task') {
    if (action === 'started') {
      list.appendChild(createSystemMsg(`Task: ${truncate(ev.task, 60)}`));
    } else if (action === 'completed') {
      const file = ev.payload?.output_file ? ` -> ${ev.payload.output_file}` : '';
      list.appendChild(createSystemMsg(`Task completed (${ev.payload?.output_len || 0} chars)${file}`));
    } else if (action === 'failed') {
      list.appendChild(createSystemMsg(`Task FAILED: ${truncate(ev.payload?.error, 80)}`));
    }
  }

  if (state.autoScroll) scrollToBottom();
}

// ── Message factories ──
function createSpeechBubble(agent, text) {
  const el = document.createElement('div');
  el.className = 'msg speech';
  el.innerHTML = `<div class="name" style="color:${agentColor(agent)}">${escHtml(shortName(agent))}</div><div class="bubble">${escHtml(truncate(text, 500))}</div>`;
  return el;
}

function createThinkingBubble(agent, text) {
  const el = document.createElement('div');
  el.className = 'msg thinking';
  el.innerHTML = `<div class="name" style="color:${agentColor(agent)}">${escHtml(shortName(agent))}</div><div class="bubble">(${escHtml(truncate(text, 300))})</div>`;
  return el;
}

function createErrorBubble(agent, text) {
  const el = document.createElement('div');
  el.className = 'msg error-msg';
  el.innerHTML = `<div class="name" style="color:var(--red)">${escHtml(shortName(agent))}</div><div class="bubble">${escHtml(text)}</div>`;
  return el;
}

function createSystemMsg(text) {
  const el = document.createElement('div');
  el.className = 'msg system';
  el.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
  return el;
}

function createCrewBanner(text, isError = false) {
  const el = document.createElement('div');
  el.className = 'msg crew-banner' + (isError ? ' error' : '');
  el.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
  return el;
}

function createSeparator() { return document.createElement('hr'); }

function shortName(role) {
  if (!role) return '?';
  const match = role.match(/^(.+?)\s*\(/);
  return match ? match[1] : role.split(' ').slice(0, 2).join(' ');
}

// ── Helpers ──
function findAgent(role) {
  if (!role) return null;
  return state.agents[role] || Object.values(state.agents).find(a => role.includes(a.role) || a.role.includes(role));
}

function setAgentStatus(a, status) {
  a.status = status;
  const iconMap = {working:'\u2328\uFE0F', thinking:'\uD83D\uDCAD', speaking:'\uD83D\uDCAC', tool:'\uD83D\uDD27', error:'\u26A0\uFE0F', idle:''};
  a.icon_el.textContent = iconMap[status] || '';
  a.desk_el.classList.toggle('active', status !== 'idle');
  a.desk_el.classList.toggle('error', status === 'error');
  const targetZone = status === 'idle' ? 'lounge' : (state.activeCrew ? 'meeting' : 'work');
  moveToZone(a, targetZone);
}

function moveToZone(a, zone) {
  if (a.zone === zone) return;
  a.zone = zone;
  const containers = { work: 'work-agents', meeting: 'meeting-agents', lounge: 'lounge-agents' };
  const target = document.getElementById(containers[zone]);
  if (target && a.desk_el.parentElement !== target) {
    target.appendChild(a.desk_el);
  }
}

function resetAllDesks() { Object.values(state.agents).forEach(a => setAgentStatus(a, 'idle')); }
function truncate(s, n) { if (!s) return ''; s = String(s); return s.length > n ? s.slice(0, n) + '...' : s; }
function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function updateTokens() {
  document.getElementById('tokens').innerHTML = `Tokens: <b>${(state.totalTokens/1000).toFixed(1)}k</b>`;
}

function updateMeeting(crew, text) {
  document.getElementById('meeting-crew').innerHTML = crew ? `${crew} — ${escHtml(text)}` : 'No active crew';
}

let timerInterval;
function updateTimer() {
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (!state.startTime) { document.getElementById('timer').textContent = ''; return; }
    const s = Math.floor((Date.now() - state.startTime) / 1000);
    const m = Math.floor(s / 60);
    document.getElementById('timer').innerHTML = `<b>${String(m).padStart(2,'0')}:${String(s%60).padStart(2,'0')}</b>`;
  }, 1000);
}

function scrollToBottom() {
  const list = document.getElementById('msg-list');
  list.scrollTop = list.scrollHeight;
  state.autoScroll = true;
  document.getElementById('scroll-btn').classList.remove('visible');
}

// ── Dashboard ──
function buildDashboard() {
  const container = document.getElementById('dash-cards');
  container.innerHTML = '';
  Object.values(state.agents).forEach(a => {
    const tags = PERSONALITY_TAGS[a.agentId] || [];
    const card = document.createElement('div');
    card.className = 'dash-card';
    card.id = `dc-${a.role.replace(/\s/g, '_')}`;
    card.innerHTML = `
      <div class="dc-header">
        <div class="dc-dot" id="dcd-${a.role.replace(/\s/g, '_')}"></div>
        <div class="dc-name" style="color:${agentColor(a.role)}">${shortName(a.role)}</div>
      </div>
      <div class="dc-tags">${tags.map(t => `<span class="dc-tag">${t}</span>`).join('')}</div>
      <div class="dc-stats">
        <div class="dc-stat"><span class="dc-stat-label">Tasks</span><div class="dc-bar"><div class="dc-bar-fill" id="dcb-tasks-${a.role.replace(/\s/g, '_')}" style="width:0%;background:var(--green)"></div></div><span class="dc-stat-val" id="dcv-tasks-${a.role.replace(/\s/g, '_')}">0/0</span></div>
        <div class="dc-stat"><span class="dc-stat-label">Tokens</span><div class="dc-bar"><div class="dc-bar-fill" id="dcb-tokens-${a.role.replace(/\s/g, '_')}" style="width:0%;background:var(--accent)"></div></div><span class="dc-stat-val" id="dcv-tokens-${a.role.replace(/\s/g, '_')}">0</span></div>
        <div class="dc-stat"><span class="dc-stat-label">Errors</span><div class="dc-bar"><div class="dc-bar-fill" id="dcb-errors-${a.role.replace(/\s/g, '_')}" style="width:0%;background:var(--red)"></div></div><span class="dc-stat-val" id="dcv-errors-${a.role.replace(/\s/g, '_')}">0</span></div>
      </div>
      <div class="dc-speech" id="dcs-${a.role.replace(/\s/g, '_')}"></div>
    `;
    container.appendChild(card);
  });
}

function updateDashboard() {
  let activeCount = 0;
  const maxTokens = Math.max(1, ...Object.values(state.agentStats).map(s => s.tokens));
  Object.values(state.agents).forEach(a => {
    const s = state.agentStats[a.role];
    if (!s) return;
    const key = a.role.replace(/\s/g, '_');
    const dot = document.getElementById(`dcd-${key}`);
    if (dot) {
      dot.className = 'dc-dot' + (a.status === 'error' ? ' error' : a.status !== 'idle' ? ' active' : '');
      if (a.status !== 'idle') activeCount++;
    }
    const taskPct = s.tasks > 0 ? Math.round(s.tasksDone / s.tasks * 100) : 0;
    const bTasks = document.getElementById(`dcb-tasks-${key}`);
    if (bTasks) bTasks.style.width = taskPct + '%';
    const vTasks = document.getElementById(`dcv-tasks-${key}`);
    if (vTasks) vTasks.textContent = `${s.tasksDone}/${s.tasks}`;
    const tokenPct = maxTokens > 0 ? Math.round(s.tokens / maxTokens * 100) : 0;
    const bTokens = document.getElementById(`dcb-tokens-${key}`);
    if (bTokens) bTokens.style.width = tokenPct + '%';
    const vTokens = document.getElementById(`dcv-tokens-${key}`);
    if (vTokens) vTokens.textContent = s.tokens > 1000 ? (s.tokens/1000).toFixed(1) + 'k' : s.tokens;
    const errorPct = s.tasks > 0 ? Math.min(100, Math.round(s.errors / s.tasks * 100)) : 0;
    const bErrors = document.getElementById(`dcb-errors-${key}`);
    if (bErrors) bErrors.style.width = errorPct + '%';
    const vErrors = document.getElementById(`dcv-errors-${key}`);
    if (vErrors) vErrors.textContent = s.errors;
    const speech = document.getElementById(`dcs-${key}`);
    if (speech && s.lastSpeech) speech.textContent = s.lastSpeech;
  });
  const summary = document.getElementById('dash-summary');
  if (summary) summary.textContent = `Active: ${activeCount}/${Object.keys(state.agents).length} | Total tokens: ${(state.totalTokens/1000).toFixed(1)}k`;
}

function toggleDashboard() {
  const d = document.getElementById('dashboard');
  const btn = document.getElementById('dash-toggle');
  const isExpanded = d.classList.contains('expanded');
  d.classList.toggle('expanded', !isExpanded);
  d.classList.toggle('collapsed', isExpanded);
  btn.textContent = isExpanded ? 'Expand' : 'Collapse';
}

function changeFontSize(delta) {
  const current = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--msg-font-size'));
  const next = Math.max(10, Math.min(20, current + delta));
  document.documentElement.style.setProperty('--msg-font-size', next + 'px');
}

// ── Crew execution ──
async function runCrew(name, btn) {
  const res = await fetch(`/api/run/${name}`, {method:'POST'});
  const data = await res.json();
  if (data.error) { alert(data.error); return; }
  updateButtons(true);
  btn.classList.add('running');
}

function updateButtons(busy) {
  document.querySelectorAll('#controls button').forEach(b => { b.disabled = busy; if (!busy) b.classList.remove('running'); });
}

// ── Profile modal ──
function openProfile(role) {
  const a = state.agents[role];
  if (!a) return;
  const s = state.agentStats[role] || {};
  const tags = PERSONALITY_TAGS[a.agentId] || [];
  const color = agentColor(role);
  const initials = shortName(role).slice(0, 2);
  const historyHtml = (s.history || []).slice(-10).reverse().map(h => `<div class="pm-history-item">${escHtml(h)}</div>`).join('') || '<div class="pm-history-item" style="color:var(--dim)">No activity yet</div>';

  document.getElementById('profile-modal').innerHTML = `
    <button class="pm-close" onclick="closeModal()">&times;</button>
    <div class="pm-header">
      <div class="pm-avatar" style="background:${color}">${initials}</div>
      <div class="pm-info">
        <h4 style="color:${color}">${escHtml(shortName(role))}</h4>
        <div class="pm-crew">${escHtml(a.crew)} | ${a.status}</div>
      </div>
    </div>
    <div class="pm-section">
      <h5>Role</h5>
      <p>${escHtml(role)}</p>
    </div>
    <div class="pm-section">
      <h5>Tags</h5>
      <div class="pm-tags">${tags.map(t => `<span class="pm-tag">${t}</span>`).join('') || '<span style="color:var(--dim);font-size:11px">None</span>'}</div>
    </div>
    <div class="pm-section">
      <h5>Stats</h5>
      <div class="pm-stat-row">
        <span class="pm-stat">Tasks: <b>${s.tasksDone || 0}/${s.tasks || 0}</b></span>
        <span class="pm-stat">Tokens: <b>${s.tokens > 1000 ? (s.tokens/1000).toFixed(1) + 'k' : s.tokens || 0}</b></span>
        <span class="pm-stat">Errors: <b>${s.errors || 0}</b></span>
      </div>
    </div>
    <div class="pm-section">
      <h5>Recent Activity</h5>
      <div class="pm-history">${historyHtml}</div>
    </div>
  `;
  document.getElementById('modal-overlay').classList.add('visible');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('visible');
}

// ── Tool highlight flash on avatar ──
function flashToolHighlight(a) {
  a.desk_el.classList.add('tool-highlight');
  setTimeout(() => a.desk_el.classList.remove('tool-highlight'), 600);
}

// ── Error vignette ──
function showErrorVignette() {
  const v = document.getElementById('error-vignette');
  v.classList.remove('visible');
  void v.offsetWidth; // reflow to restart animation
  v.classList.add('visible');
  setTimeout(() => v.classList.remove('visible'), 2000);
}

// ── Theme toggle ──
function toggleTheme() {
  const isLight = document.documentElement.classList.toggle('light');
  document.getElementById('theme-btn').textContent = isLight ? 'Dark' : 'Light';
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
}
// Restore saved theme
if (localStorage.getItem('theme') === 'light') {
  document.documentElement.classList.add('light');
  document.addEventListener('DOMContentLoaded', () => { const b = document.getElementById('theme-btn'); if (b) b.textContent = 'Dark'; });
}

init();
