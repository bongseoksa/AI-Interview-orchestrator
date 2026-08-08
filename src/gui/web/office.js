const WS_URL = `ws://${location.host}/ws/office`;

// ── Agent color map ──
// 랜덤 HSL(채도 60/명도 65)은 형광 초록·분홍을 뽑아내 따뜻한 뉴트럴 팔레트와 충돌했다.
// 채도를 낮춘 고정 팔레트에서 해시로 고른다 — 색은 구분용이지 장식이 아니다.
const AGENT_PALETTE = [
  '#C2704F', '#8B7355', '#6E8B74', '#7A7FA6', '#A86B7E',
  '#5F8A8B', '#A88A4A', '#7C6B94', '#96745C', '#5E7F9E',
  '#8E7B4F', '#6B8E7B', '#9C6F6F',
];
const AGENT_COLORS = {};
function agentColor(role) {
  if (!role) return 'var(--dim)';
  if (AGENT_COLORS[role]) return AGENT_COLORS[role];
  let hash = 0;
  for (let i = 0; i < role.length; i++) hash = role.charCodeAt(i) + ((hash << 5) - hash);
  AGENT_COLORS[role] = AGENT_PALETTE[Math.abs(hash) % AGENT_PALETTE.length];
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

// ── Floor plan ──
// 방 3개가 복도 하나로 이어진 한 층. 좌표는 층 전체를 100×100으로 본 비율이고,
// 방·문·복도 DOM 위치와 이동 경로가 전부 여기서 나온다 — 두 벌로 두면 반드시 어긋난다.
//
//   ┌──────────┐ ┌──────────┐
//   │ Work     │ │ Meeting  │     문: 워크룸 우하단 / 미팅룸 좌하단 / 라운지 좌상단
//   └──────█───┘ └─█────────┘
//   ━━━━━━━━━━━━━━━━━━━━━━━━━      ← 복도 (LANE_Y)
//   ┌─█──────────────────────┐
//   │ Lounge                 │
//   └────────────────────────┘
const LANE_Y = 59;  // 복도 중앙선 — 모든 이동은 이 선을 타고 지나간다
const ZONES = {
  work:    { x: 3,  y: 4,  w: 44, h: 48, label: 'Work Room',    door: { x: 41, y: 52 }, inside: 47, padY: 11 },
  meeting: { x: 53, y: 4,  w: 44, h: 48, label: 'Meeting Room', door: { x: 59, y: 52 }, inside: 47, padY: 16 },
  lounge:  { x: 3,  y: 66, w: 94, h: 30, label: 'Lounge',       door: { x: 9,  y: 66 }, inside: 71, padY: 11 },
};
const CORRIDORS = [
  { x: 3,  y: 52, w: 94, h: 14 },  // 메인 복도 (가로) — 세 문이 모두 여기로 열린다
  { x: 47, y: 4,  w: 6,  h: 48 },  // 워크룸-미팅룸 사이 (세로)
];
// colStep은 방 하나가 전원(13명)을 수용할 수 있게 잡는다 — 다 몰려도 자리가 방 밖으로 나가면 안 된다.
const SEAT = { padX: 5, colStep: 7.8, rowStep: 12 };
const seatsTaken = { work: new Set(), meeting: new Set(), lounge: new Set() };

function renderFloorplan() {
  const fp = document.getElementById('floorplan');
  CORRIDORS.forEach(c => fp.appendChild(styledBox('corridor', c)));
  for (const [key, z] of Object.entries(ZONES)) {
    const room = styledBox('room', z);
    room.id = `room-${key}`;
    room.innerHTML = `<span class="room-label">${z.label}</span>`;
    fp.appendChild(room);
    const door = document.createElement('div');
    door.className = 'door';
    door.id = `door-${key}`;
    door.style.left = z.door.x + '%';
    door.style.top = z.door.y + '%';
    fp.appendChild(door);
  }
  document.getElementById('room-meeting').appendChild(document.getElementById('meeting-info'));
}

function styledBox(cls, r) {
  const el = document.createElement('div');
  el.className = cls;
  Object.assign(el.style, { left: r.x + '%', top: r.y + '%', width: r.w + '%', height: r.h + '%' });
  return el;
}

// 자리는 방마다 격자로 나눠 쓴다. 같은 칸에 두 명이 겹치지 않게 빈 번호를 집어간다.
function seatPos(zone, idx) {
  const z = ZONES[zone];
  const cols = Math.max(1, Math.floor((z.w - SEAT.padX) / SEAT.colStep));
  return {
    x: z.x + SEAT.padX + (idx % cols) * SEAT.colStep,
    y: z.y + z.padY + Math.floor(idx / cols) * SEAT.rowStep,
  };
}

function takeSeat(a, zone) {
  const used = seatsTaken[zone];
  let i = 0;
  while (used.has(i)) i++;
  used.add(i);
  a.seat = { zone, idx: i };
  return seatPos(zone, i);
}

function releaseSeat(a) {
  if (!a.seat) return;
  seatsTaken[a.seat.zone].delete(a.seat.idx);
  a.seat = null;
}

function setPos(a, p) {
  a.pos = p;
  a.desk_el.style.left = p.x + '%';
  a.desk_el.style.top = p.y + '%';
}

// 첫 배치는 걷지 않는다 — 출근해 있는 상태로 시작한다.
function placeInZone(a, zone) {
  a.zone = a.placed = zone;
  a.desk_el.style.transition = 'none';
  setPos(a, takeSeat(a, zone));
  requestAnimationFrame(() => { a.desk_el.style.transition = ''; });
}

// 경로는 전부 직각으로 꺾인다 — 사람은 벽을 뚫고 대각선으로 가지 않는다.
function buildPath(a, to, seat) {
  const pts = [];
  const from = a.placed;
  if (from) {                                             // 방 안 → 문 앞 → 문 통과
    const f = ZONES[from];
    pts.push({ x: f.door.x, y: a.pos.y });
    pts.push({ x: f.door.x, y: f.inside });
    pts.push({ x: f.door.x, y: f.door.y, door: from });
  }
  if (!from) {
    // 걷던 중 지시가 바뀐 경우 — 어느 방에도 속해 있지 않다. 방금 넘은 문의 열로 돌아가야
    // 벽을 뚫지 않는다 (그냥 제자리에서 복도로 내려가면 벽을 통과한다).
    const back = a.viaDoor ? ZONES[a.viaDoor].door.x : a.pos.x;
    pts.push({ x: back, y: a.pos.y });
    pts.push({ x: back, y: a.lane });
  } else {
    pts.push({ x: ZONES[from].door.x, y: a.lane });                 // 복도 진입
  }
  const t = ZONES[to];
  pts.push({ x: t.door.x, y: a.lane });                   // 복도 이동 (각자 다른 폭으로 지나간다)
  pts.push({ x: t.door.x, y: t.door.y, door: to });       // 문 통과
  pts.push({ x: t.door.x, y: t.inside });                 // 방 진입
  pts.push({ x: t.door.x, y: seat.y });                   // 자리 줄로
  pts.push(seat);
  return pts;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function walk(a, to, seat, token) {
  const path = buildPath(a, to, seat);
  a.desk_el.classList.add('walking');
  for (const p of path) {
    if (a.walkToken !== token) return;                    // 걷는 중 새 지시가 오면 이 경로는 버린다
    // 문을 넘는 순간부터는 어느 방에도 속하지 않는다. 되돌아 나갈 때 쓸 문은 기억해 둔다.
    if (p.door) { a.placed = null; a.viaDoor = p.door; pulseDoor(p.door); }
    // a.pos는 "직전에 지시한 지점"이라 이동 중 재지시를 받으면 실제 위치와 조금 다르다.
    // 거리는 소요 시간 계산에만 쓰여서 오차는 걸음 속도로만 나타난다.
    const d = Math.hypot(p.x - a.pos.x, p.y - a.pos.y);
    if (d < 0.3) { setPos(a, p); continue; }              // 이미 그 자리면 걸을 것도 없다
    const ms = Math.max(140, d * 26 * a.pace);            // 전이 시간은 좌표를 바꾸기 전에 걸어야 한다
    a.desk_el.style.transition = `left ${ms}ms linear, top ${ms}ms linear, transform 0.15s ease`;
    setPos(a, p);
    await sleep(ms);
  }
  if (a.walkToken !== token) return;
  a.placed = to;
  a.desk_el.classList.remove('walking');
}

// 좌표를 손대면 조용히 깨지는 것만 본다: 대각선 이동, 문이 아닌 곳으로 벽 통과, 방 밖으로 나간 자리.
// ?selftest 를 붙여 열면 콘솔에 결과가 찍힌다.
function selfCheck() {
  const fail = [];
  const zones = Object.keys(ZONES);
  // 세로 이동이 어떤 방의 벽선을 넘는다면 그 x는 반드시 그 방의 문이어야 한다.
  const wallHit = (prev, p) => {
    if (Math.abs(p.x - prev.x) > 0.01) return null;
    const [lo, hi] = [Math.min(prev.y, p.y), Math.max(prev.y, p.y)];
    for (const [k, z] of Object.entries(ZONES)) {
      if (p.x < z.x || p.x > z.x + z.w) continue;
      for (const wall of [z.y, z.y + z.h])
        if (wall > lo + 0.01 && wall < hi - 0.01 && Math.abs(p.x - z.door.x) > 0.01) return k;
    }
    return null;
  };
  for (const to of zones) {
    // from: 방에서 출발 / null: 걷던 중 재지시(문을 갓 넘은 상태, 방 안에서 끊긴 상태)
    const cases = zones.map(z => ({ placed: z, pos: seatPos(z, 5) }));
    cases.push({ placed: null, viaDoor: to, pos: { x: 30, y: LANE_Y } });
    zones.forEach(z => cases.push({ placed: null, viaDoor: z, pos: seatPos(z, 4) }));
    for (const c of cases) {
      const a = { ...c, lane: LANE_Y + 2.4 };
      const path = buildPath(a, to, seatPos(to, 0));
      let prev = a.pos;
      for (const p of path) {
        if (Math.abs(p.x - prev.x) > 0.01 && Math.abs(p.y - prev.y) > 0.01)
          fail.push(`대각선 이동 ${c.placed || 'corridor'}→${to}: (${prev.x},${prev.y})→(${p.x},${p.y})`);
        const hit = wallHit(prev, p);
        if (hit) fail.push(`벽 통과 ${c.placed || 'corridor'}→${to}: ${hit} 벽을 x=${p.x}에서 넘음`);
        prev = p;
      }
    }
    const z = ZONES[to];
    for (let i = 0; i < 13; i++) {
      const s = seatPos(to, i);
      if (s.x < z.x || s.x > z.x + z.w || s.y < z.y || s.y > z.y + z.h)
        fail.push(`자리 ${to}#${i}가 방 밖: (${s.x.toFixed(1)},${s.y.toFixed(1)})`);
    }
    if (Math.abs(z.door.y - z.y) > 0.01 && Math.abs(z.door.y - (z.y + z.h)) > 0.01)
      fail.push(`${to} 문이 벽 위에 없음`);
  }
  console[fail.length ? 'error' : 'log']('floorplan selfCheck:', fail.length ? fail : 'ok');
  return fail;
}
if (location.search.includes('selftest')) selfCheck();

function pulseDoor(zone) {
  const el = document.getElementById(`door-${zone}`);
  if (!el) return;
  el.classList.add('open');
  setTimeout(() => el.classList.remove('open'), 600);
}

// ── State ──
const state = {
  agents: {},
  roster: [],   // /api/agents 원본 — @멘션 자동완성용
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

  state.roster = agents.filter(a => a.agent_id);
  renderFloorplan();
  const layerEl = document.getElementById('agent-layer');
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
    layerEl.appendChild(el);
    // pace(걸음 속도) · lane(복도에서 걷는 폭)은 사람마다 다르게 고정한다.
    // 같은 지시를 받은 무리가 줄 맞춰 겹쳐 미끄러지면 사람으로 안 보인다.
    const agent = { role, crew, status: 'idle', speech: '', desk_el: el, icon_el: el.querySelector('.av-status'), speech_el: el.querySelector('.av-speech'), agentId: id, zone: 'lounge', placed: 'lounge', pos: { x: 0, y: 0 }, seat: null, walkToken: 0, pace: 0.85 + Math.random() * 0.35, lane: LANE_Y + (Math.random() - 0.5) * 5 };
    state.agents[role] = agent;
    placeInZone(agent, 'lounge');
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

  initComposer();
  restorePendingReviews();
  refreshQueue();
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

  if (cat === 'review' && action === 'pending') refreshReviewBadge();
  if (cat === 'router' || (cat === 'crew' && action !== 'started')) refreshQueue();

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
  document.getElementById('msg-empty')?.remove();

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
  } else if (cat === 'user') {
    list.appendChild(createUserBubble(ev.payload?.text || ''));
  } else if (cat === 'router') {
    list.appendChild(createRouterMsg(ev.payload?.text || ''));
  } else if (cat === 'review') {
    if (action === 'pending') {
      let p = {};
      try { p = JSON.parse(ev.payload?.text || '{}'); } catch (_) {}
      list.appendChild(createReviewCard(ev.run_id, p.agenda || '', p.docs || []));
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
// 발언은 500자에서 잘려 회의 내용을 화면에서 읽을 수 없었다. 접어두고 펼치게 한다.
const CLAMP_AT = 400;

function createSpeechBubble(agent, text) {
  const el = document.createElement('div');
  el.className = 'msg speech';
  el.innerHTML = `<div class="name" style="color:${agentColor(agent)}">${escHtml(shortName(agent))}</div>
    <div class="bubble${text.length > CLAMP_AT ? ' clamped' : ''}"><div class="bubble-body">${escHtml(text)}</div>${
      text.length > CLAMP_AT ? `<button class="bubble-more" onclick="toggleClamp(this)">전문 보기 (${text.length.toLocaleString()}자)</button>` : ''
    }</div>`;
  return el;
}

function toggleClamp(btn) {
  const bubble = btn.parentElement;
  const clamped = bubble.classList.toggle('clamped');
  btn.textContent = clamped
    ? `전문 보기 (${bubble.querySelector('.bubble-body').textContent.length.toLocaleString()}자)`
    : '접기';
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
  releaseSeat(a);
  const seat = takeSeat(a, zone);
  const token = ++a.walkToken;
  // 여럿이 같이 불려가도 출발 시각이 제각각이어야 문 앞에서 뭉치지 않는다.
  setTimeout(() => { if (a.walkToken === token) walk(a, zone, seat, token); }, Math.random() * 1400);
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

// ── Crew execution ── (큐가 열려 있으므로 실행 중에도 버튼을 막지 않는다 — 07 §3)
async function runCrew(name, btn) {
  const res = await fetch(`/api/run/${name}`, {method:'POST'});
  const data = await res.json();
  if (data.error) { alert(data.error); return; }
  btn.classList.add('running');
}

function updateButtons(busy) {
  if (!busy) document.querySelectorAll('#controls button.running').forEach(b => b.classList.remove('running'));
}

// ── 지시 채팅 (07 §10) ──
async function sendMessage() {
  const input = document.getElementById('composer-input');
  const btn = document.getElementById('composer-send');
  const text = input.value.trim();
  if (!text) return;

  input.value = ''; input.style.height = 'auto';
  btn.disabled = true; btn.textContent = '라우팅...';
  try {
    const res = await fetch('/api/message', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text}),
    });
    const data = await res.json();
    // 성공/되묻기 모두 WS(user.message / router.decided)로 화면에 찍힌다.
    if (!res.ok) alert(`전송 실패: ${res.status}`);
    else if (data.ask) input.value = text;  // 되물었으면 원문을 되돌려 수정하게 둔다
  } catch (e) {
    alert(`전송 실패: ${e}`);
    input.value = text;
  } finally {
    btn.disabled = false; btn.textContent = '보내기';
    input.focus();
  }
}

function initComposer() {
  const input = document.getElementById('composer-input');
  input.addEventListener('keydown', e => {
    if (mention.open && handleMentionKey(e)) return;
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage(); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 132) + 'px';
    updateMentionPopup();
  });
  input.addEventListener('blur', () => setTimeout(closeMention, 150));
}

// ── @멘션 자동완성 ──
// agent_id를 외워야 @멘션을 쓸 수 있었다. 로스터가 이미 /api/agents로 오므로 그걸 쓴다.
const mention = { open: false, items: [], sel: 0, start: -1 };
const MENTION_RE = /@([a-zA-Z0-9-]*)$/;

function updateMentionPopup() {
  const input = document.getElementById('composer-input');
  const m = MENTION_RE.exec(input.value.slice(0, input.selectionStart));
  if (!m) return closeMention();

  const q = m[1].toLowerCase();
  mention.items = state.roster.filter(a =>
    !q || a.agent_id.toLowerCase().includes(q) || (a.role || '').toLowerCase().includes(q));
  if (!mention.items.length) return closeMention();

  mention.open = true;
  mention.sel = 0;
  mention.start = input.selectionStart - m[0].length;
  renderMentionPopup();
}

function renderMentionPopup() {
  const pop = document.getElementById('mention-pop');
  pop.innerHTML = mention.items.map((a, i) => {
    const color = agentColor(a.role || a.agent_id);
    return `<div class="mp-item${i === mention.sel ? ' sel' : ''}" onmousedown="event.preventDefault();pickMention(${i})">
      <div class="mp-dot" style="background:${color}">${escHtml(shortName(a.role || a.agent_id).slice(0,2))}</div>
      <div class="mp-text"><div class="mp-role">${escHtml(shortName(a.role || a.agent_id))}</div><div class="mp-id">@${escHtml(a.agent_id)}</div></div>
      ${a.writer ? '<span class="mp-writer">쓰기</span>' : ''}
    </div>`;
  }).join('');
  pop.classList.add('visible');
  pop.querySelector('.mp-item.sel')?.scrollIntoView({block: 'nearest'});
}

function handleMentionKey(e) {
  if (e.key === 'ArrowDown') { mention.sel = (mention.sel + 1) % mention.items.length; renderMentionPopup(); }
  else if (e.key === 'ArrowUp') { mention.sel = (mention.sel - 1 + mention.items.length) % mention.items.length; renderMentionPopup(); }
  else if (e.key === 'Enter' || e.key === 'Tab') { pickMention(mention.sel); }
  else if (e.key === 'Escape') { closeMention(); }
  else return false;
  e.preventDefault();
  return true;
}

function pickMention(i) {
  const a = mention.items[i];
  if (!a) return;
  const input = document.getElementById('composer-input');
  const before = input.value.slice(0, mention.start);
  const after = input.value.slice(input.selectionStart);
  const insert = `@${a.agent_id} `;
  input.value = before + insert + after;
  const pos = before.length + insert.length;
  input.setSelectionRange(pos, pos);
  closeMention();
  input.focus();
}

function closeMention() {
  mention.open = false;
  document.getElementById('mention-pop').classList.remove('visible');
}

// ── 확인함 (07 §7) ──
function createUserBubble(text) {
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
  return el;
}

// 라우터 판정문은 "[회의] 안건 — id, id" 형식. 모드를 배지로 떼어내 색으로 구분한다.
function createRouterMsg(text) {
  const el = document.createElement('div');
  const m = /^\[(회의|작업)\]\s*(.*)$/s.exec(text);
  const kind = m ? (m[1] === '회의' ? 'meeting' : 'task') : 'ask';
  el.className = `msg router ${kind}`;
  el.innerHTML = `<div class="bubble">${
    m ? `<span class="rt-badge">${m[1]}</span>${escHtml(m[2])}` : escHtml(text)
  }</div>`;
  return el;
}

function createReviewCard(runId, agenda, docs) {
  const el = document.createElement('div');
  el.className = 'msg review-card';
  el.id = `rc-${runId}`;
  el.innerHTML = `
    <div class="rc-title">회의 종료 — 보고서 초안 준비됨</div>
    <div class="rc-docs">${docs.map(d => escHtml(d.title)).join('<br>')}</div>
    <div class="rc-actions">
      <button onclick="previewReview('${runId}')">미리보기</button>
      <button class="primary" onclick="resolveReview('${runId}','approve')">노션 반영</button>
      <button class="danger" onclick="resolveReview('${runId}','reject')">반려</button>
    </div>`;
  return el;
}

async function previewReview(runId) {
  const data = await fetch(`/api/review/${runId}`).then(r => r.json());
  if (data.error) { alert(data.error); return; }
  document.getElementById('profile-modal').id = 'preview-modal';
  document.getElementById('preview-modal').innerHTML = `
    <button class="pm-close" onclick="closePreview()">&times;</button>
    <h4>${escHtml(data.agenda)}</h4>
    ${data.docs.map(d => `<h5>${escHtml(d.title)}</h5><pre>${escHtml(d.content || '')}</pre>`).join('')}`;
  document.getElementById('modal-overlay').classList.add('visible');
}

function closePreview() {
  document.getElementById('modal-overlay').classList.remove('visible');
  const m = document.getElementById('preview-modal');
  if (m) m.id = 'profile-modal';
}

async function resolveReview(runId, action) {
  const card = document.getElementById(`rc-${runId}`);
  if (action === 'reject' && !confirm('초안을 삭제합니다. 계속할까요?')) return;
  card?.querySelectorAll('button').forEach(b => b.disabled = true);
  const data = await fetch(`/api/review/${runId}/${action}`, {method:'POST'}).then(r => r.json());
  if (data.ok) {
    card.querySelector('.rc-actions').innerHTML =
      `<span style="color:var(--dim);font-size:11px">${action === 'approve' ? '노션 반영 완료' : '반려됨'}</span>`;
  } else {
    alert(`실패: ${JSON.stringify(data.results || data.error)}`);
    card?.querySelectorAll('button').forEach(b => b.disabled = false);
  }
  refreshReviewBadge();
}

async function refreshQueue() {
  const s = await fetch('/api/status').then(r => r.json()).catch(() => null);
  const el = document.getElementById('queue');
  if (el && s) el.textContent = s.queued ? `대기 ${s.queued}건` : '';
}

async function refreshReviewBadge() {
  const items = await fetch('/api/review').then(r => r.json()).catch(() => []);
  const h = document.querySelector('#messenger-header h3');
  if (h) h.textContent = items.length ? `Office Messenger (확인함 ${items.length})` : 'Office Messenger';
  return items;
}

// 승인 카드는 review.pending WS 이벤트로만 그려져, 새로고침하면 사라졌다.
// 대기 항목은 서버(파일 큐)에 남아 있는데 승인할 UI가 없어지는 상태 — 접속 시 복원한다.
async function restorePendingReviews() {
  const items = await refreshReviewBadge();
  if (!items.length) return;
  const list = document.getElementById('msg-list');
  document.getElementById('msg-empty')?.remove();
  items.forEach(it => {
    if (document.getElementById(`rc-${it.run_id}`)) return;
    list.appendChild(createSystemMsg(`승인 대기 — ${it.date}`));
    list.appendChild(createReviewCard(it.run_id, it.agenda, it.docs || []));
  });
  scrollToBottom();
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
