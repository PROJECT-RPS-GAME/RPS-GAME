(() => {
'use strict';

const $ = (s) => document.querySelector(s);
const EMOJI = { ROCK: '\u270A', PAPER: '\u270B', SCISSORS: '\u270C\uFE0F', UNKNOWN: '\u2754' };
const NAME = { ROCK: 'ROCK', PAPER: 'PAPER', SCISSORS: 'SCISSORS' };
const TARGETS = [0, 3, 5];
const MARGIN = 0.12;            // camera border that is mapped to the screen edge
const PINCH_ON = 0.32, PINCH_OFF = 0.50, FREEZE_BELOW = 0.55;

const el = {
  splash: $('#splash'), menu: $('#menu'), game: $('#game'), matchover: $('#matchover'),
  setup: $('#setup'), p1Name: $('#p1-name'), p2Name: $('#p2-name'),
  p2Field: $('#p2-field'), computerOpponent: $('#computer-opponent'),
  p1Label: $('#p1-label'), setupError: $('#setup-error'), startMatch: $('#start-match'),
  highlightWinner: $('#highlight-winner'),
  howto: $('#howto'), videoModal: $('#videoModal'), hl: $('#hl'), sfx: $('#sfx-jutsu'),
  cam: $('#cam'), divider: $('#divider'), dividerP1: $('#divider .tag.l'),
  dividerP2: $('#divider .tag.r'), banner: $('#banner'), cursor: $('#cursor'),
  ovReady: $('#ov-ready'), ovCount: $('#ov-count'), ovCapture: $('#ov-capture'), ovResult: $('#ov-result'),
  countNum: $('#count-num'), countSub: $('#count-sub'), goText: $('#go-text'), chips: $('#chips'), locks: $('#locks'),
  flash: $('#jutsu-flash'), bannerResult: $('#banner-result'), msg: $('#msg'), history: $('#history'),
  scoreP1: $('#score-p1'), scoreP2: $('#score-p2'),
  btnNext: $('#btn-next'), btnRematch: $('#btn-rematch'), btnTarget: $('#btn-target'),
  btnAuto: $('#btn-auto'), btnMute: $('#btn-mute'),
};

let state = null, prevPhase = null, prevSeq = null, prevLabel = '';
let menuTarget = 0, autoHighlight = true, muted = false, audioReady = false;
let setupMode = 'cpu';
let startingMatch = false;
let camLoaded = false, serverDown = false, lastData = null, demo = false;
let videoRequest = 0;
let historyKey = null;
const activeAnimations = new WeakMap();
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

/* ---------- helpers ---------- */
function show(node, on) {
  if (node.hidden === !on) return;
  const animation = activeAnimations.get(node);
  if (animation) {
    animation.cancel();
    activeAnimations.delete(node);
  }
  node.hidden = !on;
  if (on && !reducedMotion.matches && typeof node.animate === 'function') {
    const entering = node.animate(
      [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }],
      { duration: 220, easing: 'cubic-bezier(.2,.75,.25,1)' }
    );
    activeAnimations.set(node, entering);
    entering.onfinish = () => {
      if (activeAnimations.get(node) === entering) {
        activeAnimations.delete(node);
        entering.cancel();
      }
    };
  }
}
const setText = (node, t) => { if (node.textContent !== t) node.textContent = t; };
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const targetLabel = (t) => (t === 0 ? 'Free play' : 'First to ' + t);
const isOpen = (node) => !node.hidden;
const names = (s) => s.player_names
  || (s.mode === 'cpu' ? { p1: 'Player 1', p2: 'Computer' } : { p1: 'Player 1', p2: 'Player 2' });

async function api(action, extra) {
  try {
    const r = await fetch('/api/action', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ action }, extra || {})),
    });
    const result = await r.json();
    if (!r.ok) {
      setText(el.setupError, result.error || 'Could not start the match.');
      show(el.setupError, true);
      return null;
    }
    return result;
  } catch (e) {
    serverDown = true; updateBanner();
    return null;
  }
}

/* ---------- audio / video ---------- */
function unlockAudio() {
  if (audioReady) return;
  audioReady = true;
  try {
    el.sfx.volume = 0;
    el.sfx.play().then(() => { el.sfx.pause(); el.sfx.currentTime = 0; el.sfx.volume = 1; })
      .catch(() => { el.sfx.volume = 1; audioReady = false; });
  } catch (e) { el.sfx.volume = 1; audioReady = false; }
}
function playJutsu() {
  if (muted) return;
  try { el.sfx.currentTime = 0; el.sfx.play().catch(() => {}); } catch (e) { /* ignore */ }
}
function openVideo(winnerName = '') {
  if (isOpen(el.videoModal)) return;
  if (winnerName) {
    setText(el.highlightWinner, winnerName + ' WINS!');
    show(el.highlightWinner, true);
  } else {
    setText(el.highlightWinner, '');
    show(el.highlightWinner, false);
  }
  show(el.videoModal, true);
  el.hl.muted = muted; el.hl.currentTime = 0;
  const request = ++videoRequest;
  el.hl.play().catch((error) => {
    if (request !== videoRequest || !isOpen(el.videoModal)) return;
    if (!el.hl.muted) {
      el.hl.muted = true;
      el.hl.play().catch((fallbackError) => {
        if (request === videoRequest && isOpen(el.videoModal)) {
          console.error('Could not play the highlight video:', fallbackError);
        }
      });
      return;
    }
    console.error('Could not play the highlight video:', error);
  });
}
function closeVideo() {
  videoRequest++;
  el.hl.pause(); show(el.videoModal, false);
}
el.hl.addEventListener('ended', closeVideo);

function openSetup(mode) {
  setupMode = mode;
  const cpu = mode === 'cpu';
  show(el.p2Field, !cpu);
  show(el.computerOpponent, cpu);
  setText(el.p1Label, cpu ? 'Your name' : 'Player 1 name');
  el.p1Name.value = 'Player 1';
  el.p2Name.value = 'Player 2';
  show(el.setupError, false);
  show(el.setup, true);
  requestAnimationFrame(() => el.p1Name.focus({ preventScroll: true }));
}

async function startMatch() {
  if (startingMatch) return;
  const p1 = el.p1Name.value.trim();
  const p2 = el.p2Name.value.trim();
  if (!p1) {
    setText(el.setupError, 'Enter a name for Player 1 to continue.');
    show(el.setupError, true);
    el.p1Name.focus();
    return;
  }
  if (setupMode === 'two' && !p2) {
    setText(el.setupError, 'Enter a name for Player 2 to continue.');
    show(el.setupError, true);
    el.p2Name.focus();
    return;
  }
  el.p1Name.value = p1;
  if (setupMode === 'two') el.p2Name.value = p2;
  startingMatch = true;
  el.startMatch.disabled = true;
  try {
    const result = await api('start', {
      mode: setupMode,
      target: menuTarget,
      player_names: { p1, p2: setupMode === 'cpu' ? 'Computer' : p2 },
    });
    if (result) show(el.setup, false);
  } finally {
    startingMatch = false;
    el.startMatch.disabled = false;
  }
}

/* ---------- actions ---------- */
function act(name) {
  switch (name) {
    case 'enter': show(el.splash, false); break;
    case 'play-cpu': openSetup('cpu'); break;
    case 'play-two': openSetup('two'); break;
    case 'start-match': startMatch(); break;
    case 'cancel-setup': show(el.setup, false); break;
    case 'target':
      menuTarget = TARGETS[(TARGETS.indexOf(menuTarget) + 1) % TARGETS.length];
      setText(el.btnTarget, 'Match: ' + targetLabel(menuTarget)); break;
    case 'highlights': openVideo(); break;
    case 'watch':
      openVideo(state && state.match_winner ? names(state)[state.match_winner] : '');
      break;
    case 'howto': show(el.howto, true); break;
    case 'close-howto': show(el.howto, false); break;
    case 'close-video': closeVideo(); break;
    case 'next': api('next'); break;
    case 'rematch': api('rematch'); break;
    case 'menu': closeVideo(); show(el.howto, false); api('menu'); break;
    case 'auto':
      autoHighlight = !autoHighlight;
      setText(el.btnAuto, 'Auto highlights: ' + (autoHighlight ? 'ON' : 'OFF')); break;
    case 'mute':
      muted = !muted; el.hl.muted = muted;
      setText(el.btnMute, muted ? 'Sound OFF' : 'Sound ON'); break;
    case 'quit':
      fetch('/api/quit', { method: 'POST' }).catch(() => {});
      document.body.innerHTML = '<p style="color:#fff;font:24px sans-serif;text-align:center;margin-top:30vh">Game stopped. You can close this tab.</p>';
      break;
    default: break;
  }
}

el.setup.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.matches('input')) {
    e.preventDefault();
    startMatch();
  }
});

document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-act]');
  if (b && !b.disabled) act(b.dataset.act);
});

/* ---------- rendering ---------- */
function roundBanner(s, n) {
  const w = s.round_winner;
  if (w === 'draw') return ['DRAW', 'draw'];
  const winner = w === 'p1' ? n.p1 : n.p2;
  return [winner + ' WINS!', w === 'p1' ? 'win1' : (s.mode === 'cpu' ? 'lose' : 'win2')];
}

function pop(node) { node.classList.remove('pop'); void node.offsetWidth; node.classList.add('pop'); }

function updateChips(container, items) {
  items.forEach(([text, cls, ok], index) => {
    let item = container.children[index];
    if (!item) {
      item = document.createElement('div');
      container.append(item);
    }
    const className = 'chip ' + cls + (ok ? ' ok' : '');
    if (item.className !== className) item.className = className;
    setText(item, text);
  });
  while (container.children.length > items.length) container.lastElementChild.remove();
}

function render(s) {
  const n = names(s), two = s.mode === 'two', phase = s.phase;
  const inMenu = phase === 'MENU';
  show(el.menu, inMenu); show(el.game, !inMenu);

  if (!inMenu && !camLoaded) { camLoaded = true; el.cam.src = '/video?' + Date.now(); }
  if (inMenu && camLoaded) { camLoaded = false; el.cam.removeAttribute('src'); }
  if (inMenu) { setText(el.btnTarget, 'Match: ' + targetLabel(menuTarget)); }

  // Score bar
  setText($('#name-p1'), n.p1); setText($('#name-p2'), n.p2);
  const scoreChanged = el.scoreP1.textContent !== String(s.score.p1)
    || el.scoreP2.textContent !== String(s.score.p2);
  const p1Changed = el.scoreP1.textContent !== String(s.score.p1);
  const p2Changed = el.scoreP2.textContent !== String(s.score.p2);
  setText($('#score-p1'), String(s.score.p1)); setText($('#score-p2'), String(s.score.p2));
  if (scoreChanged) {
    if (p1Changed) pop(el.scoreP1);
    if (p2Changed) pop(el.scoreP2);
  }
  setText($('#draws'), 'Draws ' + s.score.draws);
  setText($('#round-info'), 'Round ' + (s.rounds + (phase === 'COUNTDOWN' || phase === 'CAPTURE' ? 1 : 0) || 1)
    + '  \u00B7  ' + targetLabel(s.target));
  setText(el.dividerP1, n.p1); setText(el.dividerP2, n.p2);
  show(el.divider, two);

  // Overlays
  show(el.ovReady, phase === 'READY');
  show(el.ovCount, phase === 'COUNTDOWN');
  show(el.ovCapture, phase === 'CAPTURE');
  show(el.ovResult, phase === 'RESULT' || phase === 'MATCH_OVER');

  const players = two ? ['p1', 'p2'] : ['p1'];
  if (phase === 'READY') {
    updateChips(el.chips, players.map((p) => {
      const t = !s.present[p] ? 'show your hand' : (s.live && s.live[p] !== 'UNKNOWN'
        ? EMOJI[s.live[p]] + ' ' + NAME[s.live[p]] : 'hand detected');
      return [n[p] + ': ' + t, p, s.present[p]];
    }));
  }
  if (phase === 'COUNTDOWN') {
    setText(el.countNum, s.label);
    setText(el.countSub, two ? 'Players, get ready...' : 'Get ready...');
  }
  if (phase === 'CAPTURE') {
    if (prevPhase !== 'CAPTURE') pop(el.goText);
    updateChips(el.locks, players.map((p) => {
      const t = s.locked[p] ? '\u2714 locked' : (s.present[p] ? 'hold still...' : 'show your hand');
      return [n[p] + ': ' + t, p, s.locked[p]];
    }));
  }
  if (s.label !== prevLabel && phase === 'COUNTDOWN') pop(el.countNum);
  prevLabel = s.label;

  if ((phase === 'RESULT' || phase === 'MATCH_OVER') && s.moves) {
    setText($('#who-p1'), n.p1); setText($('#who-p2'), n.p2);
    setText($('#mv-p1'), EMOJI[s.moves.p1]); setText($('#mv-p2'), EMOJI[s.moves.p2]);
    setText($('#mn-p1'), NAME[s.moves.p1]); setText($('#mn-p2'), NAME[s.moves.p2]);
    const [t, cls] = roundBanner(s, n);
    setText(el.bannerResult, t); el.bannerResult.className = cls;
  }

  // Buttons / messages
  const canNext = phase === 'READY' || (phase === 'RESULT' && !s.match_winner);
  show(el.btnNext, canNext);
  setText(el.btnNext, phase === 'READY' ? 'Start round' : 'Next round');
  show(el.btnRematch, (phase === 'READY' && s.rounds > 0) || phase === 'RESULT');
  setText(el.msg, s.message || '');
  const nextHistoryKey = s.history.map((h) => h.p1 + ':' + h.p2 + ':' + h.winner).join('|');
  if (nextHistoryKey !== historyKey) {
    historyKey = nextHistoryKey;
    el.history.replaceChildren(...s.history.map((h) => {
      const d = document.createElement('div');
      d.className = 'hrow ' + (h.winner === 'p1' ? 'w1' : h.winner === 'p2' ? 'w2' : 'd');
      d.textContent = EMOJI[h.p1] + ' vs ' + EMOJI[h.p2];
      return d;
    }));
  }

  // Match over
  show(el.matchover, phase === 'MATCH_OVER');
  if (phase === 'MATCH_OVER') {
    const w = s.match_winner;
    setText($('#mo-title'), names(s)[w].toUpperCase() + ' WINS THE MATCH!');
    setText($('#mo-score'), n.p1 + ' ' + s.score.p1 + '  -  ' + s.score.p2 + ' ' + n.p2
      + '   (draws: ' + s.score.draws + ')');
  }
}

function effects(s) {
  // New finished round -> ninjutsu sound + flash
  if (prevSeq === null) prevSeq = s.seq;
  if (s.seq !== prevSeq) {
    prevSeq = s.seq;
    if (s.round_winner && s.round_winner !== 'draw') {
      playJutsu();
      el.flash.classList.remove('fire'); void el.flash.offsetWidth; el.flash.classList.add('fire');
    }
    pop(el.bannerResult);
  }
  // Match just ended -> highlight video
  if (s.phase === 'MATCH_OVER' && prevPhase !== 'MATCH_OVER' && autoHighlight) {
    setTimeout(() => {
      if (autoHighlight && state && state.phase === 'MATCH_OVER' && state.match_winner) {
        openVideo(names(state)[state.match_winner]);
      }
    }, 1500);
  }
  prevPhase = s.phase;
}

function updateBanner() {
  let msg = '';
  if (serverDown) msg = 'Lost connection to the game server. Is "python app.py" still running?';
  else if (lastData && !lastData.camera_ok) msg = lastData.error || 'Camera not available';
  show(el.banner, !!msg); setText(el.banner, msg);
}

/* ---------- hand pointer (smooth, 60 fps) ---------- */
// Python already filters the hand (One Euro). Here the cursor glides toward the newest
// position every display frame, so it stays smooth between the ~30 camera updates.
const TAU_MS = 42;            // smooths gaps between camera updates without feeling sluggish
const LOST_MS = 250;          // keep the cursor this long if a frame drops the hand
const HIT_TARGET_PX = 16;     // small forgiving edge target without reaching nearby buttons
const STICKY_PX = 14;         // ignore small tracking jitter, but release focus when leaving
const FOCUS_SETTLE_MS = 180;
const DWELL_MOVE_PX = 9;
const cur = { x: innerWidth / 2, y: innerHeight / 2, shown: false, pinching: false };
let latest = null, latestAt = 0, lastTs = 0;
let hoverBtn = null, focusSince = 0, focusX = 0, focusY = 0, lastFire = 0;

function setPointer(p) { if (p) { latest = p; latestAt = performance.now(); } else { latest = null; } }

function pointerAllowed() {
  if (isOpen(el.splash) || isOpen(el.setup) || isOpen(el.videoModal) || isOpen(el.howto)) return true;
  return !!state && ['MENU', 'READY', 'RESULT', 'MATCH_OVER'].includes(state.phase);
}

function hideCursor() {
  el.cursor.style.display = 'none'; cur.shown = false; cur.pinching = false;
  if (hoverBtn) hoverBtn.classList.remove('hover');
  hoverBtn = null;
}

function fire(btn) {
  const now = performance.now();
  if (btn !== hoverBtn || btn.disabled || !document.contains(btn) || now - lastFire < 500) return;
  lastFire = now;
  el.cursor.classList.remove('click'); void el.cursor.offsetWidth; el.cursor.classList.add('click');
  btn.click();
}

function pickButton(x, y) {
  const hit = document.elementFromPoint(x, y);
  const direct = hit && hit.closest('[data-act]');
  if (direct) return direct.disabled ? null : direct;

  if (hoverBtn && document.contains(hoverBtn) && !hoverBtn.hidden && !hoverBtn.disabled) {
    const r = hoverBtn.getBoundingClientRect();
    if (x > r.left - STICKY_PX && x < r.right + STICKY_PX
      && y > r.top - STICKY_PX && y < r.bottom + STICKY_PX) return hoverBtn;
  }

  const candidates = [];
  for (const btn of document.querySelectorAll('[data-act]')) {
    if (btn.hidden || btn.disabled || btn.getClientRects().length === 0) continue;
    const r = btn.getBoundingClientRect();
    const dx = Math.max(r.left - x, 0, x - r.right);
    const dy = Math.max(r.top - y, 0, y - r.bottom);
    const distance = dx * dx + dy * dy;
    if (distance <= HIT_TARGET_PX * HIT_TARGET_PX) candidates.push({ btn, distance });
  }
  candidates.sort((a, b) => a.distance - b.distance);
  if (!candidates.length) return null;
  if (candidates.length > 1
    && Math.sqrt(candidates[1].distance) - Math.sqrt(candidates[0].distance) < 8) return null;
  return candidates[0].btn;
}

function cursorFrame(ts) {
  requestAnimationFrame(cursorFrame);
  const dt = lastTs ? Math.min(ts - lastTs, 100) : 16;
  lastTs = ts;
  const p = latest;
  if (!p || performance.now() - latestAt > LOST_MS || !pointerAllowed()) { if (cur.shown) hideCursor(); return; }

  const tx = clamp((p.x - MARGIN) / (1 - 2 * MARGIN), 0, 1) * innerWidth;
  const ty = clamp((p.y - MARGIN) / (1 - 2 * MARGIN), 0, 1) * innerHeight;
  if (!cur.shown) { cur.x = tx; cur.y = ty; cur.shown = true; }
  else {
    const a = 1 - Math.exp(-dt / TAU_MS);        // frame-rate independent easing
    cur.x += (tx - cur.x) * a; cur.y += (ty - cur.y) * a;
  }
  const pinching = cur.pinching ? p.ratio < PINCH_OFF : p.ratio < PINCH_ON;

  el.cursor.style.display = 'block';
  el.cursor.style.transform = 'translate(' + cur.x.toFixed(1) + 'px,' + cur.y.toFixed(1) + 'px)' + (pinching ? ' scale(.72)' : '');
  el.cursor.classList.toggle('pinch', pinching);

  const btn = pickButton(cur.x, cur.y);
  const now = performance.now();
  if (btn !== hoverBtn) {
    if (hoverBtn) hoverBtn.classList.remove('hover');
    hoverBtn = btn; focusSince = now; focusX = cur.x; focusY = cur.y;
    if (btn) btn.classList.add('hover');
  } else if (btn && Math.hypot(cur.x - focusX, cur.y - focusY) > DWELL_MOVE_PX) {
    focusSince = now; focusX = cur.x; focusY = cur.y;
  }
  const focusedLongEnough = btn && now - focusSince >= FOCUS_SETTLE_MS;
  if (pinching && !cur.pinching && focusedLongEnough) fire(btn);
  cur.pinching = pinching;
}
requestAnimationFrame(cursorFrame);

/* ---------- live data ---------- */
function onFrame(data) {
  lastData = data; serverDown = false; demo = !!data.demo;
  updateBanner();
  if (data.state) {
    state = data.state;
    render(state); effects(state);
  }
  setPointer(data.pointer);
}

function connect() {
  const es = new EventSource('/events');
  es.onmessage = (e) => { try { onFrame(JSON.parse(e.data)); } catch (err) { console.error(err); } };
  es.onerror = () => { serverDown = true; updateBanner(); };
  es.onopen = () => { serverDown = false; updateBanner(); };
}
el.cam.addEventListener('error', () => {
  setTimeout(() => { if (camLoaded) el.cam.src = '/video?' + Date.now(); }, 1000);
});

/* ---------- keyboard / mouse fallbacks ---------- */
const DEMO_KEYS = { q: ['p1', 'ROCK'], w: ['p1', 'PAPER'], e: ['p1', 'SCISSORS'],
                    i: ['p2', 'ROCK'], o: ['p2', 'PAPER'], p: ['p2', 'SCISSORS'] };

document.addEventListener('pointerdown', (e) => { if (e.isTrusted) unlockAudio(); });
document.addEventListener('keydown', (e) => {
  if (e.isTrusted) unlockAudio();
  if (isOpen(el.splash)) { act('enter'); return; }
  const k = e.key.toLowerCase();
  if (e.key === 'Escape') {
    if (isOpen(el.videoModal)) closeVideo();
    else if (isOpen(el.howto)) show(el.howto, false);
    else if (isOpen(el.setup)) show(el.setup, false);
    else act('menu');
  } else if (e.key === ' ' || e.key === 'Enter') {
    if (state && (state.phase === 'READY' || (state.phase === 'RESULT' && !state.match_winner))) { e.preventDefault(); act('next'); }
  } else if (k === 'm') { act('mute'); }
  else if (demo && DEMO_KEYS[k]) {
    fetch('/api/demo_input', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player: DEMO_KEYS[k][0], gesture: DEMO_KEYS[k][1] }) }).catch(() => {});
  }
});

connect();
})();
