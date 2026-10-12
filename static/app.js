const PITCH_W = 105, PITCH_H = 68;
const svg = document.getElementById('pitch');
const scrubber = document.getElementById('scrubber');
const minuteLabel = document.getElementById('minuteLabel');
const playBtn = document.getElementById('playBtn');
const homeRoster = document.getElementById('homeRoster');
const awayRoster = document.getElementById('awayRoster');
const playerHeader = document.getElementById('playerHeader');
const statLine = document.getElementById('statLine');
const strengthList = document.getElementById('strengthList');
const watchList = document.getElementById('watchList');
const langSelect = document.getElementById('langSelect');

let match = null, selectedPlayerId = null, dossier = null, mode = 'analyst';
let highlightedIds = null, playing = false, playTimer = null;
let minuteById = new Map();

function humanizeCitations(text) {
  // Dossier text cites raw event ids (e.g. "e498") so the backend grounding
  // checker can mechanically verify them against the evidence set. Swap
  // each one for its match minute here, purely for display — the backend
  // text (and the grounding check) is untouched.
  return text.replace(/\be\d+\b/g, id => {
    const minute = minuteById.get(id);
    return minute === undefined ? id : `${minute}'`;
  });
}

function svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function drawPitchLines() {
  svg.replaceChildren();
  svg.appendChild(svgEl('rect', { x: 0.5, y: 0.5, width: PITCH_W - 1, height: PITCH_H - 1, fill: 'none', stroke: '#2f6b45', 'stroke-width': 0.4 }));
  svg.appendChild(svgEl('line', { x1: PITCH_W / 2, y1: 0, x2: PITCH_W / 2, y2: PITCH_H, stroke: '#2f6b45', 'stroke-width': 0.4 }));
  svg.appendChild(svgEl('circle', { cx: PITCH_W / 2, cy: PITCH_H / 2, r: 9.15, fill: 'none', stroke: '#2f6b45', 'stroke-width': 0.4 }));
  for (const side of [0, PITCH_W - 16.5]) {
    svg.appendChild(svgEl('rect', { x: side, y: PITCH_H / 2 - 20.15, width: 16.5, height: 40.3, fill: 'none', stroke: '#2f6b45', 'stroke-width': 0.4 }));
  }
}

function eventColor(ev) {
  if (ev.type === 'shot' || ev.type === 'goal') return '#38bdf8';
  if (ev.type === 'foul') return '#fbbf24';
  if (ev.type === 'tackle' || ev.type === 'interception') return ev.outcome === 'success' ? '#4ade80' : '#f87171';
  return ev.outcome === 'success' ? '#94a3b8' : '#f87171';
}

function renderRoster() {
  homeRoster.innerHTML = '';
  awayRoster.innerHTML = '';
  for (const p of match.players) {
    const btn = document.createElement('button');
    if (selectedPlayerId === p.id) btn.classList.add('selected');
    btn.innerHTML = `<span>${p.name}</span><span class="pos">${p.position}</span>`;
    btn.onclick = () => selectPlayer(p.id);
    (p.team === 'home' ? homeRoster : awayRoster).appendChild(btn);
  }
}

function renderPitch() {
  drawPitchLines();
  if (!selectedPlayerId) return;
  const minute = Number(scrubber.value);
  const events = match.events.filter(e => e.player_id === selectedPlayerId && e.minute <= minute);
  for (const ev of events) {
    const highlighted = highlightedIds && highlightedIds.includes(ev.id);
    const dot = svgEl('circle', {
      cx: ev.x, cy: ev.y, r: highlighted ? 1.6 : 0.9,
      fill: eventColor(ev), class: 'ev-dot' + (highlighted ? ' highlight' : ''),
    });
    svg.appendChild(dot);
  }
}

function statLineText(metrics) {
  const pc = metrics.passes_attempted ? Math.round(100 * metrics.passes_completed / metrics.passes_attempted) : 0;
  const duels = metrics.duels_won + metrics.duels_lost;
  return `${metrics.passes_completed}/${metrics.passes_attempted} passes (${pc}%) &middot; `
    + `${metrics.progressive_passes} progressive &middot; duels ${metrics.duels_won}-${metrics.duels_lost} (${duels} total) &middot; `
    + `${metrics.fouls_committed} fouls &middot; ${metrics.shots_on_target}/${metrics.shots} shots on target, ${metrics.goals} goals &middot; `
    + `~${Math.round(metrics.distance_m)}m covered`;
}

function entryCard(entry) {
  const card = document.createElement('div');
  card.className = `entry-card ${entry.kind}`;
  const rawText = mode === 'analyst' ? entry.narrative.analyst_en : entry.narrative['fan_' + langSelect.value];
  const text = mode === 'analyst' ? humanizeCitations(rawText) : rawText;
  card.innerHTML = `
    <div class="headline">${entry.headline}</div>
    <div class="narrative">${text}</div>
    <div class="meta">${Math.round(entry.confidence * 100)}% confidence &middot; ${entry.evidence.event_ids.length} events &middot; grounded: ${entry.narrative.grounded}</div>
  `;
  card.onclick = () => { highlightedIds = entry.evidence.event_ids; renderPitch(); };
  return card;
}

function renderDossier() {
  if (!dossier) {
    playerHeader.textContent = 'Select a player';
    statLine.innerHTML = '';
    strengthList.innerHTML = '';
    watchList.innerHTML = '';
    return;
  }
  playerHeader.textContent = `${dossier.player.name} · ${dossier.player.position}`;
  statLine.innerHTML = statLineText(dossier.metrics);
  const strengths = dossier.entries.filter(e => e.kind === 'strength');
  const watch = dossier.entries.filter(e => e.kind === 'watch_point');
  strengthList.innerHTML = '';
  watchList.innerHTML = '';
  if (!strengths.length) strengthList.innerHTML = '<div class="empty-note">No strength has cleared the evidence threshold yet.</div>';
  if (!watch.length) watchList.innerHTML = '<div class="empty-note">No watch point has cleared the evidence threshold yet.</div>';
  strengths.forEach(e => strengthList.appendChild(entryCard(e)));
  watch.forEach(e => watchList.appendChild(entryCard(e)));
}

async function loadDossier() {
  if (!selectedPlayerId) return;
  const minute = Number(scrubber.value);
  const res = await fetch(`/api/dossier?player=${selectedPlayerId}&minute=${minute}`);
  dossier = await res.json();
  renderDossier();
  renderPitch();
}

function selectPlayer(playerId) {
  selectedPlayerId = playerId;
  highlightedIds = null;
  renderRoster();
  loadDossier();
}

document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    mode = btn.dataset.mode;
    renderDossier();
  });
});
langSelect.addEventListener('change', renderDossier);

scrubber.addEventListener('input', () => {
  minuteLabel.textContent = scrubber.value + "'";
  highlightedIds = null;
  loadDossier();
});

playBtn.addEventListener('click', () => {
  playing = !playing;
  playBtn.textContent = playing ? '⏸ Pause' : '▶ Play';
  if (playing) {
    playTimer = setInterval(() => {
      let m = Number(scrubber.value) + 1;
      if (m > 90) m = 0;
      scrubber.value = m;
      minuteLabel.textContent = m + "'";
      loadDossier();
    }, 500);
  } else {
    clearInterval(playTimer);
  }
});

async function init() {
  match = await fetch('/api/match').then(r => r.json());
  minuteById = new Map(match.events.map(e => [e.id, e.minute]));
  renderRoster();
  renderPitch();
  selectPlayer(match.players.find(p => p.archetype !== 'balanced')?.id || match.players[0].id);
}

init();
