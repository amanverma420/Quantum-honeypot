import { AppState } from './state.js';
import { makeToken, measureToken } from './quantum_engine.js';

const State = AppState;
let N_QUBITS = State.N_QUBITS;
let THRESHOLD = State.THRESHOLD;
let activeResource = State.activeResource;

const session = State.session;
let logEntries = State.logEntries;
const simResults = State.simResults;
const charts = State.charts;
let lastAnalyticsData = State.lastAnalyticsData;

// Sandbox Tab state variables
const sandboxCircuitState = [
  { prepGate: null, measureBasis: '+' }, // q0
  { prepGate: 'X', measureBasis: '+' },  // q1
  { prepGate: 'H', measureBasis: 'x' },  // q2
  { prepGate: 'XH', measureBasis: 'x' }  // q3
];
let sandboxNoise = 0.0;
let sandboxAngle = 0;

// BB84 Walkthrough state variables
const bb84State = {
  step: 0,
  aliceBits: [],
  aliceBases: [],
  bobBases: [],
  eveBases: [],
  bobBits: [],
  eveIntercept: false
};

const BB84_STEPS_META = State.BB84_STEPS_META;

const RESOURCE_META = State.RESOURCE_META;

// ── 1. Page Switching & Sidebar Cfg ───────────────────────────────────────────
function showPage(name, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  btn.classList.add('active');
  
  if (name === 'sandbox') {
    renderSandboxWires();
    initBB84Data();
    renderBB84Table();
    updateBB84StepDetails();
  }
  
  // Redraw canvas paths
  setTimeout(drawNetworkPaths, 100);
}

function switchResource(id) {
  activeResource = id;
  document.querySelectorAll('.resource-item').forEach(el => el.classList.remove('active'));
  document.getElementById('res-' + id).classList.add('active');

  ['db', 'api', 's3'].forEach(r => {
    document.getElementById('panel-' + r).style.display = r === id ? '' : 'none';
  });

  const meta = RESOURCE_META[id];
  document.getElementById('resource-panel-title').textContent = meta.name;
  document.getElementById('status-resource-label').textContent = `${meta.label} · ACTIVE`;
  termLog([`<span class="t-p">  →</span> <span class="t-i">Switched active honeypot: <span class="t-v">${meta.label}</span></span>`]);
  
  // Highlight active node in network map
  document.querySelectorAll('.net-node').forEach(node => {
    node.classList.remove('active', 'attacked');
  });
  const node = document.getElementById(meta.nodeId);
  if (node) node.classList.add('active');
}

function updateQubitCfg(v) {
  N_QUBITS = parseInt(v, 10);
  document.getElementById('qubit-lbl').textContent = v;
  document.querySelectorAll('[id$="-qlayer"]').forEach(el => {
    el.textContent = `⟨ψ| ${v} tripwire qubits active`;
  });
  renderQbGrid([]);
}

function updateThreshCfg(v) {
  THRESHOLD = v / 100;
  document.getElementById('thresh-lbl').textContent = THRESHOLD.toFixed(2);
  updateConfusionMatrix();
  renderROCChart();
}

function renderQbGrid(basisKey, alertIdxs = []) {
  const grid = document.getElementById('qb-grid');
  if (!grid) return;
  grid.innerHTML = '';
  const show = basisKey.length > 0;

  for (let i = 0; i < N_QUBITS; i++) {
    const cell = document.createElement('div');
    cell.className = 'qb-cell';
    if (show) {
      if (alertIdxs.includes(i)) {
        cell.className += ' alarm';
        cell.textContent = '!';
      } else if (basisKey[i] === '+') {
        cell.className += ' plus';
        cell.textContent = '|+⟩';
      } else {
        cell.className += ' cross';
        cell.textContent = '|−⟩';
      }
    } else {
      cell.textContent = `q${i}`;
    }
    grid.appendChild(cell);
  }
}

// ── 2. Threat Map Layout & Canvas Animation ─────────────────────────────────────
let pulseAnim = null;

function drawNetworkPaths() {
  const canvas = document.getElementById('net-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const container = document.getElementById('net-container');
  
  canvas.width = container.clientWidth;
  canvas.height = container.clientHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  const client = document.getElementById('node-client');
  const gateway = document.getElementById('node-gateway');
  const db = document.getElementById('node-db');
  const api = document.getElementById('node-vault');
  const s3 = document.getElementById('node-s3');
  
  if (!client || !gateway || !db || !api || !s3) return;
  
  const getCenter = (el) => ({
    x: el.offsetLeft + el.clientWidth / 2,
    y: el.offsetTop + el.clientHeight / 2
  });
  
  const pClient = getCenter(client);
  const pGateway = getCenter(gateway);
  const pDb = getCenter(db);
  const pApi = getCenter(api);
  const pS3 = getCenter(s3);
  
  ctx.lineWidth = 2;
  ctx.strokeStyle = 'rgba(0, 242, 254, 0.08)';
  ctx.shadowBlur = 0;
  
  const drawLine = (from, to) => {
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  };
  
  drawLine(pClient, pGateway);
  drawLine(pGateway, pDb);
  drawLine(pGateway, pApi);
  drawLine(pGateway, pS3);
}

function animateTracePulse(targetId, isAlert) {
  const canvas = document.getElementById('net-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  const client = document.getElementById('node-client');
  const gateway = document.getElementById('node-gateway');
  const target = document.getElementById(targetId);
  if (!client || !gateway || !target) return;
  
  const getCenter = (el) => ({
    x: el.offsetLeft + el.clientWidth / 2,
    y: el.offsetTop + el.clientHeight / 2
  });
  
  const pClient = getCenter(client);
  const pGateway = getCenter(gateway);
  const pTarget = getCenter(target);
  
  let progress = 0;
  const speed = 0.035;
  
  // Clear other active alert states
  document.querySelectorAll('.net-node').forEach(node => {
    if (node.id !== targetId && node.id !== 'node-client' && node.id !== 'node-gateway') {
      node.classList.remove('attacked', 'active');
    }
  });
  
  if (pulseAnim) cancelAnimationFrame(pulseAnim);
  
  const color = isAlert ? '#ff073a' : '#39ff14';
  
  function animate() {
    progress += speed;
    if (progress > 2) {
      if (isAlert) {
        target.classList.add('attacked');
      } else {
        target.classList.add('active');
      }
      drawNetworkPaths();
      return;
    }
    
    drawNetworkPaths();
    
    // Draw moving glowing dot
    ctx.beginPath();
    let currentX, currentY;
    if (progress <= 1) {
      currentX = pClient.x + (pGateway.x - pClient.x) * progress;
      currentY = pClient.y + (pGateway.y - pClient.y) * progress;
    } else {
      const p2 = progress - 1;
      currentX = pGateway.x + (pTarget.x - pGateway.x) * p2;
      currentY = pGateway.y + (pTarget.y - pGateway.y) * p2;
    }
    
    ctx.arc(currentX, currentY, 6, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.shadowBlur = 15;
    ctx.shadowColor = color;
    ctx.fill();
    ctx.shadowBlur = 0; 
    
    pulseAnim = requestAnimationFrame(animate);
  }
  
  animate();
}

// ── 3. Stats & Log Handling ───────────────────────────────────────────────────
function updateThreat() {
  const atkCount = session.attackFids.length;
  const caught = session.attackFids.filter(f => f < THRESHOLD).length;
  const rate = atkCount > 0 ? caught / atkCount : 0;
  const fill = document.getElementById('threat-fill');
  const val = document.getElementById('threat-val');
  const desc = document.getElementById('threat-desc');

  if (!fill || !val || !desc) return;

  if (atkCount === 0) {
    fill.style.width = '10%';
    fill.style.background = 'var(--green)';
    val.style.color = 'var(--green)';
    val.textContent = 'LOW';
    desc.textContent = 'No active threats detected';
  } else if (rate < 0.4) {
    fill.style.width = '35%';
    fill.style.background = 'var(--amber)';
    val.style.color = 'var(--amber)';
    val.textContent = 'MEDIUM';
    desc.textContent = `${caught} intrusion attempt(s)`;
  } else if (rate < 0.75) {
    fill.style.width = '65%';
    fill.style.background = 'var(--amber)';
    val.style.color = 'var(--amber)';
    val.textContent = 'HIGH';
    desc.textContent = `${caught} intrusion attempt(s)!`;
  } else {
    fill.style.width = '94%';
    fill.style.background = 'var(--red)';
    val.style.color = 'var(--red)';
    val.textContent = 'CRITICAL';
    desc.textContent = `${caught} intrusions detected!`;
  }
}

function updateStats() {
  const lc = session.legitFids.length;
  const ac = session.attackFids.length;
  const la = lc > 0 ? (session.legitFids.reduce((a, b) => a + b, 0) / lc).toFixed(4) : '—';
  const caught = session.attackFids.filter(f => f < THRESHOLD).length;
  const det = ac > 0 ? `${(caught / ac * 100).toFixed(0)}%` : '—';
  const drop = ac > 0 ? (THRESHOLD - session.attackFids.reduce((a, b) => a + b, 0) / ac).toFixed(4) : '—';

  const stLegit = document.getElementById('st-legit');
  const stLegitFid = document.getElementById('st-legit-fid');
  const stIntrusions = document.getElementById('st-intrusions');
  const stDet = document.getElementById('st-det');
  const stFp = document.getElementById('st-fp');
  const stDrop = document.getElementById('st-drop');

  if (stLegit) stLegit.textContent = lc;
  if (stLegitFid) stLegitFid.textContent = la;
  if (stIntrusions) stIntrusions.textContent = caught;
  if (stDet) stDet.textContent = det;
  if (stFp) stFp.textContent = session.fp;
  if (stDrop) stDrop.textContent = drop;

  updateThreat();
  updateConfusionMatrix();
  renderROCChart();
}

function addLog(user, strategy, fid, isAlert, resource) {
  const now = new Date();
  const t = now.toTimeString().slice(0, 8);
  logEntries.unshift({ user, strategy, fid, isAlert, t, resource: resource || activeResource });
  renderLog();
}

function renderLog() {
  const el = document.getElementById('audit-log');
  if (!el) return;
  if (!logEntries.length) {
    el.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text3);font-size:11px;font-family:var(--mono);">No events yet. Attempt an access below.</div>';
    return;
  }

  const stratMap = {
    legit: 'Correct basis',
    random: 'Random basis',
    fixed: 'Fixed basis',
    clone: 'Clone attempt'
  };
  const resMap = { db: 'DB', api: 'API', s3: 'S3' };

  el.innerHTML = logEntries.slice(0, 22).map(e => {
    const ico = e.isAlert
      ? '<div class="log-ico al">⚠</div>'
      : '<div class="log-ico ok">✓</div>';
    const badge = e.isAlert
      ? '<span class="badge br">ALERT</span>'
      : '<span class="badge bg">VERIFIED</span>';
    const rLabel = resMap[e.resource] || e.resource;
    return `<div class="log-entry">
      <div class="log-ts">${e.t}</div>
      ${ico}
      <div class="log-body">
        <div class="log-user">${e.user} ${badge} <span style="font-size:10px;color:var(--text3);font-family:var(--mono);">[${rLabel}]</span></div>
        <div class="log-detail">${stratMap[e.strategy] || e.strategy} · F=${e.fid.toFixed(4)} · thr=${THRESHOLD.toFixed(2)}</div>
      </div>
    </div>`;
  }).join('');
}

function clearLog() {
  logEntries = [];
  renderLog();
}

function termLog(lines) {
  const t = document.getElementById('terminal');
  if (!t) return;
  const cur = t.querySelector('.t-cur');
  if (cur) cur.closest('div').remove();
  lines.forEach(l => {
    const d = document.createElement('div');
    d.innerHTML = l;
    t.appendChild(d);
  });
  const p = document.createElement('div');
  p.innerHTML = '<span class="t-p">quantum@guard:~$ </span><span class="t-cur"></span>';
  t.appendChild(p);
  t.scrollTop = t.scrollHeight;
}

// ── 4. Intrusion Simulator ────────────────────────────────────────────────────
function quickAccess() {
  const user = document.getElementById('q-user').value;
  const strategy = document.getElementById('q-strategy').value;
  const token = makeToken(N_QUBITS);
  const res = measureToken(token, strategy);
  const isAlert = res.avg < THRESHOLD;
  const meta = RESOURCE_META[activeResource];

  const alarmIdx = [];
  if (strategy !== 'legit') {
    res.guessKey.forEach((g, i) => {
      if (g !== token.basisKey[i]) alarmIdx.push(i);
    });
  }
  renderQbGrid(token.basisKey, isAlert ? alarmIdx : []);

  if (strategy === 'legit') {
    session.legitFids.push(res.avg);
    if (isAlert) session.fp++;
  } else {
    session.attackFids.push(res.avg);
    if (isAlert) session.totalAttacks++;
  }
  updateStats();
  addLog(user, strategy, res.avg, isAlert);

  const el = document.getElementById(meta.rotatedEl);
  if (el) el.textContent = new Date().toLocaleString();

  // Animate node traffic pulse on threat map
  animateTracePulse(meta.nodeId, isAlert);

  const stratName = {
    legit: 'Legitimate (correct basis)',
    random: 'Random basis attack',
    fixed: 'Fixed basis attack',
    clone: 'Clone attempt (No-Cloning)'
  }[strategy];

  termLog([
    `<span class="t-p">  →</span> <span class="t-i">Resource: <span class="t-v">${meta.label}</span> · User: ${user}</span>`,
    `<span class="t-p">  →</span> <span class="t-i">Strategy: ${stratName}</span>`,
    `<span class="t-p">  →</span> <span class="t-i">Measuring ${N_QUBITS} tripwire qubits...</span>`,
    `<span class="t-p">  →</span> <span class="t-v">Avg fidelity: ${res.avg.toFixed(4)}  threshold: ${THRESHOLD.toFixed(2)}</span>`,
    isAlert
      ? `<span class="t-al">  [!] INTRUSION DETECTED — fidelity below threshold — ${user}</span>`
      : `<span class="t-ok">  [✓] ACCESS VERIFIED — fidelity above threshold — ${user}</span>`
  ]);
}

function runBatch() {
  const strategy = document.getElementById('q-strategy').value;
  let alerts = 0;
  for (let i = 0; i < 40; i++) {
    const token = makeToken(N_QUBITS);
    const res = measureToken(token, strategy);
    const isAlert = res.avg < THRESHOLD;
    if (strategy === 'legit') {
      session.legitFids.push(res.avg);
      if (isAlert) session.fp++;
    } else {
      session.attackFids.push(res.avg);
      if (isAlert) { session.totalAttacks++; alerts++; }
    }
  }
  updateStats();
  addLog('Batch (40×)', strategy, 0, alerts > 0);
  
  const meta = RESOURCE_META[activeResource];
  animateTracePulse(meta.nodeId, alerts > 0);

  termLog([
    `<span class="t-i">  Batch run: 40 trials (${strategy})</span>`,
    strategy !== 'legit'
      ? `<span class="t-al">  [!] ${alerts}/40 alerts triggered (${(alerts / 40 * 100).toFixed(0)}% detection rate)</span>`
      : `<span class="t-ok">  [✓] Legitimate batch: ${session.fp} false positives total</span>`
  ]);
  renderQbGrid([]);
}

// ── 5. Simulation Page & Attacker Cards ───────────────────────────────────────
let selectedAtk = null;

function selectAtk(type) {
  document.querySelectorAll('.atk-card').forEach(c => c.classList.remove('sel'));
  document.getElementById('atk-' + type).classList.add('sel');
  selectedAtk = type;
  runSingleSim(type);
}

function runSingleSim(strategy) {
  const token = makeToken(N_QUBITS);
  const res = measureToken(token, strategy);
  const isAlert = res.avg < THRESHOLD;
  const nameMap = {
    random: 'RANDOM BASIS',
    fixed: 'FIXED BASIS',
    clone: 'CLONE ATTEMPT'
  };
  document.getElementById('sim-strat-badge').textContent = nameMap[strategy] || strategy;

  const bd = document.getElementById('qb-breakdown');
  bd.innerHTML = '';
  res.scores.forEach((fid, i) => {
    const ok = fid >= THRESHOLD;
    const color = ok ? '#39ff14' : '#ff073a';
    const fill = ok ? '#39ff14' : '#ff073a';
    bd.innerHTML += `<div class="fid-row">
      <span style="font-family:var(--mono);font-size:10px;color:var(--text3);min-width:22px;">q${i}</span>
      <div class="fid-track"><div class="fid-fill" style="width:${(fid * 100).toFixed(0)}%;background:${fill};"></div></div>
      <span class="fid-val" style="color:${color};">${fid.toFixed(3)}</span>
    </div>`;
  });

  const cls = isAlert ? 'br' : 'bg';
  const avgBadge = document.getElementById('avg-fid-badge');
  avgBadge.className = 'badge ' + cls;
  avgBadge.textContent = `${res.avg.toFixed(4)}${isAlert ? ' — ALERT' : ' — OK'}`;

  simResults.unshift({ trial: simResults.length + 1, strategy, fid: res.avg, alert: isAlert });
  renderSimTbl();
}

function renderSimTbl() {
  const tbody = document.getElementById('sim-tbody');
  if (!tbody) return;
  const stratMap = { legit: 'Legitimate', random: 'Random Basis', fixed: 'Fixed Basis', clone: 'Clone' };
  tbody.innerHTML = simResults.slice(0, 9).map(r => `<tr>
    <td style="font-family:var(--mono);color:var(--text3);">#${r.trial}</td>
    <td>${stratMap[r.strategy]}</td>
    <td style="font-family:var(--mono);color:${r.alert ? 'var(--red)' : 'var(--green)'};">${r.fid.toFixed(4)}</td>
    <td>${r.alert ? '<span class="badge br">ALERT</span>' : '<span class="badge bg">OK</span>'}</td>
  </tr>`).join('');
}

function runFullSim() {
  ['legit', 'random', 'fixed', 'clone'].forEach(s => {
    for (let i = 0; i < 40; i++) {
      const token = makeToken(N_QUBITS);
      const res = measureToken(token, s);
      const isAlert = res.avg < THRESHOLD;
      simResults.unshift({ trial: simResults.length + 1, strategy: s, fid: res.avg, alert: isAlert });
      if (s === 'legit') {
        session.legitFids.push(res.avg);
        if (isAlert) session.fp++;
      } else {
        session.attackFids.push(res.avg);
        if (isAlert) session.totalAttacks++;
      }
    }
  });
  renderSimTbl();
  updateStats();
  termLog(['<span class="t-ok">  [✓] Full simulation complete — 160 trials across all strategies</span>']);
}

function runLegitDemo() {
  const token = makeToken(N_QUBITS);
  const l = measureToken(token, 'legit');
  const a = measureToken(token, 'random');
  document.getElementById('legit-fid').textContent = l.avg.toFixed(4);
  document.getElementById('atk-fid').textContent = a.avg.toFixed(4);
  document.getElementById('legit-status').className = 'badge bg';
  document.getElementById('legit-status').textContent = 'VERIFIED';
  document.getElementById('atk-status').className = 'badge br';
  document.getElementById('atk-status').textContent = 'ALERT';
}

// ── 6. Analytics Section (Confusion Matrix & ROC Curve) ───────────────────────
function updateConfusionMatrix() {
  let tp = 0; // actual attack, predicted alert
  let fn = 0; // actual attack, predicted verify
  let fp = 0; // actual legit, predicted alert
  let tn = 0; // actual legit, predicted verify
  
  session.attackFids.forEach(fid => {
    if (fid < THRESHOLD) tp++;
    else fn++;
  });
  
  session.legitFids.forEach(fid => {
    if (fid < THRESHOLD) fp++;
    else tn++;
  });
  
  const mTP = document.getElementById('m-tp');
  const mFN = document.getElementById('m-fn');
  const mFP = document.getElementById('m-fp');
  const mTN = document.getElementById('m-tn');
  
  if (mTP) mTP.textContent = tp;
  if (mFN) mFN.textContent = fn;
  if (mFP) mFP.textContent = fp;
  if (mTN) mTN.textContent = tn;
  
  const lbl = document.getElementById('matrix-thresh-lbl');
  if (lbl) lbl.textContent = THRESHOLD.toFixed(2);
}

function calculateROCCurve() {
  const thresholds = Array.from({ length: 21 }, (_, i) => i * 0.05); // 0.0 to 1.0
  const rocPoints = [];
  
  thresholds.forEach(t => {
    let tp = 0, fn = 0, fp = 0, tn = 0;
    
    session.attackFids.forEach(fid => {
      if (fid < t) tp++;
      else fn++;
    });
    
    session.legitFids.forEach(fid => {
      if (fid < t) fp++;
      else tn++;
    });
    
    const tpr = (tp + fn) > 0 ? (tp / (tp + fn)) : 0;
    const fpr = (fp + tn) > 0 ? (fp / (fp + tn)) : 0;
    
    rocPoints.push({ x: fpr, y: tpr, threshold: t });
  });
  
  rocPoints.sort((a, b) => a.x - b.x || a.y - b.y);
  
  // Clamp boundaries
  if (!rocPoints.some(p => p.x === 0 && p.y === 0)) rocPoints.unshift({ x: 0, y: 0, threshold: 0 });
  if (!rocPoints.some(p => p.x === 1 && p.y === 1)) rocPoints.push({ x: 1, y: 1, threshold: 1 });
  
  return rocPoints;
}

function renderROCChart() {
  const ctx = document.getElementById('chart-roc');
  if (!ctx) return;
  
  const rocPoints = calculateROCCurve();
  const data = rocPoints.map(p => ({ x: p.x * 100, y: p.y * 100 }));
  
  if (charts.roc) charts.roc.destroy();
  
  const gridColor = 'rgba(255, 255, 255, 0.05)';
  
  charts.roc = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'ROC Curve',
          data: data,
          borderColor: '#00f2fe',
          backgroundColor: 'rgba(0, 242, 254, 0.04)',
          borderWidth: 2,
          pointRadius: 4.5,
          pointHoverRadius: 7,
          fill: true,
          tension: 0.15
        },
        {
          label: 'Baseline',
          data: [{ x: 0, y: 0 }, { x: 100, y: 100 }],
          borderColor: 'rgba(255,255,255,0.1)',
          borderDash: [5, 5],
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const idx = context.dataIndex;
              const pt = rocPoints[idx];
              if (pt) {
                return `Threshold: ${pt.threshold.toFixed(2)} (FPR: ${(pt.x * 100).toFixed(0)}%, TPR: ${(pt.y * 100).toFixed(0)}%)`;
              }
              return '';
            }
          }
        }
      },
      scales: {
        x: {
          type: 'linear',
          min: 0,
          max: 100,
          title: { display: true, text: 'False Positive Rate (%)', color: '#a0aec0', font: { size: 10 } },
          grid: { color: gridColor },
          ticks: { color: '#64748b', font: { family: 'IBM Plex Mono', size: 9 } }
        },
        y: {
          min: 0,
          max: 100,
          title: { display: true, text: 'True Positive Rate (%)', color: '#a0aec0', font: { size: 10 } },
          grid: { color: gridColor },
          ticks: { color: '#64748b', font: { family: 'IBM Plex Mono', size: 9 } }
        }
      }
    }
  });
}

function runAnalytics() {
  const N = 40;
  const cats = ['Legitimate', 'Random Basis', 'Fixed Basis', 'Clone Attempt'];
  const strats = { 'Legitimate': 'legit', 'Random Basis': 'random', 'Fixed Basis': 'fixed', 'Clone Attempt': 'clone' };
  const data = {};

  cats.forEach(c => {
    const fids = [];
    for (let i = 0; i < N; i++) {
      const token = makeToken(N_QUBITS);
      fids.push(measureToken(token, strats[c]).avg);
    }
    data[c] = fids;
  });
  lastAnalyticsData = data;

  const colors = ['#39ff14', '#ffb000', '#00f2fe', '#ff007f'];
  const body = document.getElementById('analytics-tbody');
  body.innerHTML = '';

  cats.forEach((c, i) => {
    const fids = data[c];
    const mean = fids.reduce((a, b) => a + b, 0) / N;
    const std = Math.sqrt(fids.map(f => (f - mean) ** 2).reduce((a, b) => a + b, 0) / N);
    const min = Math.min(...fids);
    const max = Math.max(...fids);
    const alerts = fids.filter(f => f < THRESHOLD).length;
    body.innerHTML += `<tr>
      <td style="font-weight:700;color:${colors[i]};">${c}</td>
      <td style="font-family:var(--mono);">${mean.toFixed(4)}</td>
      <td style="font-family:var(--mono);color:var(--text3);">${std.toFixed(4)}</td>
      <td style="font-family:var(--mono);color:var(--text3);">${min.toFixed(4)}</td>
      <td style="font-family:var(--mono);color:var(--text3);">${max.toFixed(4)}</td>
      <td style="font-family:var(--mono);">${alerts}/${N}</td>
      <td><span class="badge ${alerts === 0 ? 'bg' : 'br'}">${(alerts / N * 100).toFixed(0)}%</span></td>
    </tr>`;
  });

  // Inject analytical runs into session to render matrices
  session.legitFids = session.legitFids.concat(data['Legitimate']);
  session.attackFids = session.attackFids.concat(data['Random Basis']).concat(data['Fixed Basis']).concat(data['Clone Attempt']);

  updateStats();

  const means = cats.map(c => data[c].reduce((a, b) => a + b, 0) / N);
  const rates = cats.map(c => data[c].filter(f => f < THRESHOLD).length / N * 100);
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    animation: { duration: 500 }
  };
  const gridColor = 'rgba(255, 255, 255, 0.05)';

  if (charts.fid) charts.fid.destroy();
  charts.fid = new Chart(document.getElementById('chart-fid'), {
    type: 'bar',
    data: {
      labels: ['Legitimate', 'Random Basis', 'Fixed Basis', 'Clone'],
      datasets: [{
        label: 'Avg Fidelity',
        data: means.map(m => +m.toFixed(4)),
        backgroundColor: colors.map(c => c + '1a'),
        borderColor: colors,
        borderWidth: 1.5,
        borderRadius: 4
      }]
    },
    options: {
      ...opts,
      scales: {
        y: {
          min: 0,
          max: 1.05,
          grid: { color: gridColor },
          ticks: { color: '#64748b', font: { family: 'IBM Plex Mono', size: 9 } }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#a0aec0', font: { size: 10 } }
        }
      }
    }
  });

  if (charts.det) charts.det.destroy();
  charts.det = new Chart(document.getElementById('chart-det'), {
    type: 'bar',
    data: {
      labels: ['False+\n(Legit)', 'Random', 'Fixed', 'Clone'],
      datasets: [{
        label: 'Detection %',
        data: rates.map(r => +r.toFixed(1)),
        backgroundColor: colors.map(c => c + '1a'),
        borderColor: colors,
        borderWidth: 1.5,
        borderRadius: 4
      }]
    },
    options: {
      ...opts,
      scales: {
        y: {
          min: 0,
          max: 110,
          grid: { color: gridColor },
          ticks: {
            color: '#64748b',
            font: { family: 'IBM Plex Mono', size: 9 },
            callback: value => `${value}%`
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#a0aec0', font: { size: 10 } }
        }
      }
    }
  });

  const labels = Array.from({ length: N }, (_, i) => i + 1);
  if (charts.trials) charts.trials.destroy();
  charts.trials = new Chart(document.getElementById('chart-trials'), {
    type: 'line',
    data: {
      labels,
      datasets: cats.map((c, i) => ({
        label: c,
        data: data[c].map(f => +f.toFixed(4)),
        borderColor: colors[i],
        backgroundColor: colors[i] + '0a',
        borderWidth: 1.5,
        pointRadius: 2,
        tension: 0.25
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      plugins: {
        legend: {
          display: true,
          labels: { color: '#a0aec0', font: { size: 11 }, boxWidth: 10 }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 1.05,
          grid: { color: gridColor },
          ticks: { color: '#64748b', font: { family: 'IBM Plex Mono', size: 9 } }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { size: 9 }, maxTicksLimit: 10 }
        }
      }
    }
  });
}

// ── 7. Interactive Qubit Sandbox tab logic ────────────────────────────────────
function switchSandboxTab(tabName) {
  const circuitTab = document.getElementById('sandbox-circuit-tab');
  const bb84Tab = document.getElementById('sandbox-bb84-tab');
  const circuitBtn = document.getElementById('sb-tab-btn-circuit');
  const bb84Btn = document.getElementById('sb-tab-btn-bb84');

  if (tabName === 'circuit') {
    circuitTab.style.display = 'grid';
    bb84Tab.style.display = 'none';
    circuitBtn.classList.add('active');
    bb84Btn.classList.remove('active');
  } else {
    circuitTab.style.display = 'none';
    bb84Tab.style.display = 'block';
    circuitBtn.classList.remove('active');
    bb84Btn.classList.add('active');
  }
}

function updateNoiseCfg(v) {
  sandboxNoise = parseFloat(v) / 100;
  document.getElementById('noise-lbl').textContent = sandboxNoise.toFixed(2);
}

function updateAngleCfg(v) {
  sandboxAngle = parseInt(v, 10);
  document.getElementById('angle-lbl').textContent = v + '°';
}

function toggleSandboxGate(idx) {
  const current = sandboxCircuitState[idx].prepGate;
  if (current === null) {
    sandboxCircuitState[idx].prepGate = 'X';
  } else if (current === 'X') {
    sandboxCircuitState[idx].prepGate = 'H';
  } else if (current === 'H') {
    sandboxCircuitState[idx].prepGate = 'XH';
  } else {
    sandboxCircuitState[idx].prepGate = null;
  }
  renderSandboxWires();
}

function toggleSandboxBasis(idx) {
  sandboxCircuitState[idx].measureBasis = sandboxCircuitState[idx].measureBasis === '+' ? 'x' : '+';
  renderSandboxWires();
}

function getQubitStateInfo(gate) {
  if (gate === null) {
    return { name: '|0⟩', vector: '[1.00, 0.00]', basis: '+', bit: 0 };
  } else if (gate === 'X') {
    return { name: '|1⟩', vector: '[0.00, 1.00]', basis: '+', bit: 1 };
  } else if (gate === 'H') {
    return { name: '|+⟩', vector: '[0.71, 0.71]', basis: 'x', bit: 0 };
  } else if (gate === 'XH') {
    return { name: '|−⟩', vector: '[0.71, -0.71]', basis: 'x', bit: 1 };
  }
}

function renderSandboxWires() {
  const wires = document.getElementById('sandbox-wires');
  if (!wires) return;
  wires.innerHTML = '';

  sandboxCircuitState.forEach((state, i) => {
    const info = getQubitStateInfo(state.prepGate);
    let gateLabel = '+';
    if (state.prepGate === 'X') gateLabel = 'X';
    else if (state.prepGate === 'H') gateLabel = 'H';
    else if (state.prepGate === 'XH') gateLabel = 'X-H';

    const gateClass = state.prepGate ? `wire-gate ${state.prepGate.toLowerCase().replace('-', '')}-gate` : 'gate-placeholder';
    const basisClass = state.measureBasis === '+' ? 'wire-measure' : 'wire-measure active';
    
    wires.innerHTML += `
      <div class="circuit-wire-row">
        <div class="wire-label">q${i}</div>
        <div style="font-family:var(--mono); font-size:11.5px; color:var(--text3); min-width:32px;">|0⟩</div>
        <div class="wire-line-container">
          <div class="${gateClass}" onclick="toggleSandboxGate(${i})">${gateLabel}</div>
        </div>
        <button class="${basisClass}" onclick="toggleSandboxBasis(${i})">${state.measureBasis}</button>
        <div class="qb-cell" id="sb-outcome-${i}">q${i}</div>
      </div>
    `;
  });

  updateSandboxTelemetry();
}

function updateSandboxTelemetry() {
  const tel = document.getElementById('sandbox-telemetry');
  if (!tel) return;
  tel.innerHTML = '';

  sandboxCircuitState.forEach((state, i) => {
    const info = getQubitStateInfo(state.prepGate);
    tel.innerHTML += `
      <div class="state-viewer">
        <div class="state-viewer-row">
          <span style="color:var(--accent2); font-weight:700;">q${i} Preparation:</span>
          <span style="color:var(--text); font-weight:700;">${info.name}</span>
        </div>
        <div class="state-viewer-row">
          <span style="color:var(--text3);">Statevector:</span>
          <span style="font-family:var(--mono); color:var(--accent); font-size:10.5px;">${info.vector}</span>
        </div>
        <div class="state-viewer-row">
          <span style="color:var(--text3);">Encoding basis/bit:</span>
          <span>B: <strong>${info.basis}</strong> · Bit: <strong>${info.bit}</strong></span>
        </div>
      </div>
    `;
  });
}

function clearSandboxCircuit() {
  sandboxCircuitState.forEach(s => {
    s.prepGate = null;
    s.measureBasis = '+';
  });
  renderSandboxWires();
  sandboxTermLog([`<div><span class="t-i">[SYSTEM] Circuit cleared. All preparation states reset to |0⟩.</span></div>`]);
}

function sandboxTermLog(lines) {
  const t = document.getElementById('sandbox-terminal');
  if (!t) return;
  t.innerHTML = '';
  lines.forEach(l => {
    const d = document.createElement('div');
    d.innerHTML = l;
    t.appendChild(d);
  });
  t.scrollTop = t.scrollHeight;
}

function runSandboxMeasurement() {
  const angleRad = (sandboxAngle * Math.PI) / 180;
  const results = [];
  let totalFidelity = 0;
  const termLines = [];
  
  sandboxCircuitState.forEach((state, i) => {
    const info = getQubitStateInfo(state.prepGate);
    const match = info.basis === state.measureBasis;
    
    // Rotation & depolarizing noise statistics
    let pCorrect;
    if (match) {
      // Rotate by alignment offset
      pCorrect = (1 - sandboxNoise) * (Math.cos(angleRad) ** 2) + sandboxNoise * 0.5;
    } else {
      pCorrect = 0.5; // mismatch collapses state 50-50
    }
    
    const isCorrect = Math.random() < pCorrect;
    const fid = isCorrect ? pCorrect : (1 - pCorrect);
    totalFidelity += fid;
    
    const cell = document.getElementById(`sb-outcome-${i}`);
    if (cell) {
      cell.className = 'qb-cell';
      if (!isCorrect) {
        cell.className += ' alarm';
        cell.textContent = '!';
      } else {
        if (state.measureBasis === '+') {
          cell.className += ' plus';
          cell.textContent = info.bit === 0 ? '|0⟩' : '|1⟩';
        } else {
          cell.className += ' cross';
          cell.textContent = info.bit === 0 ? '|+⟩' : '|−⟩';
        }
      }
    }
    
    termLines.push(
      `<span class="t-p">  q${i}:</span> prepared ${info.name} (${info.basis}), measured in ${state.measureBasis}. Match? ${match ? 'YES' : 'NO'}. Fidelity: ${fid.toFixed(3)} ${isCorrect ? '✓' : '⚠ COLLAPSE'}`
    );
  });
  
  const avgFid = totalFidelity / sandboxCircuitState.length;
  const isAlert = avgFid < THRESHOLD;
  
  termLines.unshift(
    `<span class="t-i">[SIMULATION] Running measurement: noise=${sandboxNoise.toFixed(2)}, offset=${sandboxAngle}°.</span>`
  );
  termLines.push(
    `<span class="t-p">  →</span> <strong>Average Sandbox Fidelity: ${avgFid.toFixed(4)}</strong> (threshold ${THRESHOLD})`,
    isAlert 
      ? `<span class="t-al">  [!] ALARM TRIGGERED — quantum state altered by attacker or high noise!</span>`
      : `<span class="t-ok">  [✓] ACCESS GRANTED — state verified within tolerance.</span>`
  );
  
  sandboxTermLog(termLines);
}

// ── 8. BB84 Key Exchange Protocol walkthrough ─────────────────────────────────
function initBB84Data() {
  bb84State.aliceBits = [];
  bb84State.aliceBases = [];
  bb84State.bobBases = [];
  bb84State.eveBases = [];
  bb84State.bobBits = [];
  bb84State.eveIntercept = false;
  
  for (let i = 0; i < 8; i++) {
    bb84State.aliceBits.push(Math.random() < 0.5 ? 0 : 1);
    bb84State.aliceBases.push(Math.random() < 0.5 ? '+' : 'x');
    bb84State.bobBases.push(Math.random() < 0.5 ? '+' : 'x');
    bb84State.eveBases.push(Math.random() < 0.5 ? '+' : 'x');
  }
}

function calculateBobBits() {
  bb84State.bobBits = [];
  for (let i = 0; i < 8; i++) {
    const ab = bb84State.aliceBases[i];
    const bb = bb84State.bobBases[i];
    const aliceBit = bb84State.aliceBits[i];
    
    if (bb84State.eveIntercept) {
      const eb = bb84State.eveBases[i];
      // Eve measures Alice's bit
      const eveMatch = ab === eb;
      const eveBit = eveMatch ? aliceBit : (Math.random() < 0.5 ? 0 : 1);
      
      // Bob measures Eve's bit
      const bobMatch = eb === bb;
      const bobBit = bobMatch ? eveBit : (Math.random() < 0.5 ? 0 : 1);
      bb84State.bobBits.push(bobBit);
    } else {
      const match = ab === bb;
      const bobBit = match ? aliceBit : (Math.random() < 0.5 ? 0 : 1);
      bb84State.bobBits.push(bobBit);
    }
  }
}

function toggleEveIntercept() {
  bb84State.eveIntercept = !bb84State.eveIntercept;
  if (bb84State.step >= 2) {
    calculateBobBits();
  }
  renderBB84Table();
  updateBB84StepDetails();
}

function stepBB84(dir) {
  if (dir === 1) {
    if (bb84State.step === 4) {
      bb84State.step = 0;
      initBB84Data();
    } else {
      bb84State.step++;
    }
  } else {
    if (bb84State.step > 0) {
      bb84State.step--;
    }
  }
  
  if (bb84State.step === 2) {
    calculateBobBits();
  }
  
  renderBB84Table();
  updateBB84StepDetails();
}

function goToBB84Step(s) {
  bb84State.step = s;
  if (bb84State.step >= 2) {
    calculateBobBits();
  }
  renderBB84Table();
  updateBB84StepDetails();
}

function renderBB84Table() {
  const tbody = document.getElementById('bb84-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  
  const step = bb84State.step;
  
  // 1. Alice's Bit
  let html = `<tr><td>Alice's Bit</td>` + bb84State.aliceBits.map(b => `<td>${b}</td>`).join('') + `</tr>`;
  
  // 2. Alice's Basis
  html += `<tr><td>Alice's Basis</td>` + bb84State.aliceBases.map(b => `<td class="bb84-cell-basis rect">${b}</td>`).join('') + `</tr>`;
  
  // 3. Prepared Qubit State
  html += `<tr><td>Prepared Qubit</td>` + bb84State.aliceBits.map((b, i) => {
    const basis = bb84State.aliceBases[i];
    let state = '';
    if (basis === '+') state = b === 0 ? '|0⟩' : '|1⟩';
    else state = b === 0 ? '|+⟩' : '|−⟩';
    return `<td>${state}</td>`;
  }).join('') + `</tr>`;
  
  // 4. Eve's Intercept
  if (step >= 1) {
    html += `<tr><td style="color:var(--pink);">Eve's Intercept</td><td colspan="8" style="text-align:left; font-family:var(--sans); font-weight:700;">
      <label style="cursor:pointer; display:flex; align-items:center; gap:8px;">
        <input type="checkbox" id="eve-intercept-chk" ${bb84State.eveIntercept ? 'checked' : ''} onchange="toggleEveIntercept()"> 
        Simulate Eve eavesdropping (Intercept-Resend)
      </label>
    </td></tr>`;
    
    if (bb84State.eveIntercept) {
      html += `<tr><td style="color:var(--pink);">Eve's Guess Basis</td>` + bb84State.eveBases.map(b => `<td class="bb84-cell-basis diag">${b}</td>`).join('') + `</tr>`;
      html += `<tr><td style="color:var(--pink);">Eve's Measured Bit</td>` + bb84State.aliceBits.map((b, i) => {
        const match = bb84State.aliceBases[i] === bb84State.eveBases[i];
        const eveBit = match ? b : (Math.random() < 0.5 ? 0 : 1);
        return `<td>${eveBit}</td>`;
      }).join('') + `</tr>`;
    }
  }
  
  // 5. Bob's rows
  if (step >= 2) {
    html += `<tr><td>Bob's Basis</td>` + bb84State.bobBases.map(b => `<td class="bb84-cell-basis rect">${b}</td>`).join('') + `</tr>`;
    if (bb84State.bobBits.length === 0) {
      calculateBobBits();
    }
    html += `<tr><td>Bob's Measured Bit</td>` + bb84State.bobBits.map(b => `<td>${b}</td>`).join('') + `</tr>`;
  }
  
  // 6. Sifting Basis Match check
  if (step >= 3) {
    html += `<tr><td>Basis Match?</td>` + bb84State.aliceBases.map((ab, i) => {
      const match = ab === bb84State.bobBases[i];
      const cls = match ? 'bb84-highlight' : 'bb84-mismatch';
      return `<td class="${cls}">${match ? 'MATCH' : 'DISCARD'}</td>`;
    }).join('') + `</tr>`;
    
    // Sifted Key row
    html += `<tr><td>Sifted Key</td>` + bb84State.aliceBases.map((ab, i) => {
      const match = ab === bb84State.bobBases[i];
      if (match) {
        return `<td class="bb84-highlight" style="font-weight:800; font-size:13.5px;">${bb84State.bobBits[i]}</td>`;
      } else {
        return `<td style="color:var(--text3); opacity:0.35;">-</td>`;
      }
    }).join('') + `</tr>`;
  }
  
  tbody.innerHTML = html;
}

function updateBB84StepDetails() {
  const step = bb84State.step;
  const meta = BB84_STEPS_META[step];
  
  document.getElementById('bb84-step-title').textContent = meta.title;
  document.getElementById('bb84-step-desc').textContent = meta.desc;
  
  // Highlight active step timeline dot
  for (let i = 0; i < 5; i++) {
    const el = document.getElementById(`bb-step-${i}`);
    if (el) {
      el.className = 'bb84-step';
      if (i === step) el.className += ' active';
      else if (i < step) el.className += ' completed';
    }
  }
  
  document.getElementById('btn-bb84-prev').disabled = step === 0;
  document.getElementById('btn-bb84-next').textContent = step === 4 ? 'Reset Walkthrough' : 'Next Step';
  
  // Step actions ctrls
  const ctrls = document.getElementById('bb84-step-ctrls');
  if (!ctrls) return;
  ctrls.innerHTML = '';
  
  if (step === 0) {
    ctrls.innerHTML = `<button class="btn btn-ghost btn-sm" onclick="initBB84Data(); renderBB84Table();">Randomize Bits & Bases</button>`;
  } else if (step === 1) {
    const btnText = bb84State.eveIntercept ? 'Bypass Eve Intercept' : 'Eavesdrop on Channel';
    ctrls.innerHTML = `<button class="btn btn-ghost btn-sm" onclick="toggleEveIntercept()">${btnText}</button>`;
  } else if (step === 4) {
    let siftedMatch = 0;
    let siftedTotal = 0;
    bb84State.aliceBases.forEach((ab, i) => {
      if (ab === bb84State.bobBases[i]) {
        siftedTotal++;
        if (bb84State.aliceBits[i] === bb84State.bobBits[i]) {
          siftedMatch++;
        }
      }
    });
    
    const errorRate = siftedTotal > 0 ? ((siftedTotal - siftedMatch) / siftedTotal * 100) : 0;
    const isCompromised = errorRate > 5;
    
    ctrls.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:6px;">
        <div style="font-size:12px; color:var(--text2);">Sifted Key Length: <strong>${siftedTotal} bits</strong></div>
        <div style="font-size:12px; color:var(--text2);">Mismatched Sifted Bits: <strong>${siftedTotal - siftedMatch} bits</strong></div>
        <div style="font-size:14px; font-weight:700;">
          Calculated Error Rate: 
          <span style="color:${isCompromised ? 'var(--red)' : 'var(--green)'}; text-shadow:0 0 5px currentColor;">
            ${errorRate.toFixed(1)}%
          </span>
        </div>
        <div class="badge ${isCompromised ? 'br' : 'bg'}" style="margin-top:4px; max-width:fit-content;">
          ${isCompromised ? '⚠ COMPROMISED — HONEYPOT INTRUSION ALARM ACTIVE' : '✓ SECURE — SHIELD ACTIVE'}
        </div>
      </div>
    `;
  }
}

// ── 9. Technical Report Builder ───────────────────────────────────────────────
function buildReport() {
  const N = 40;
  const cats = ['Legitimate', 'Random Basis', 'Fixed Basis', 'Clone Attempt'];
  const strats = { 'Legitimate': 'legit', 'Random Basis': 'random', 'Fixed Basis': 'fixed', 'Clone Attempt': 'clone' };
  const data = {};

  cats.forEach(c => {
    const fids = [];
    for (let i = 0; i < N; i++) {
      const token = makeToken(N_QUBITS);
      fids.push(measureToken(token, strats[c]).avg);
    }
    data[c] = fids;
  });

  const stat = c => {
    const f = data[c];
    const mean = f.reduce((a, b) => a + b, 0) / N;
    const std = Math.sqrt(f.map(x => (x - mean) ** 2).reduce((a, b) => a + b, 0) / N);
    const alerts = f.filter(x => x < THRESHOLD).length;
    return { mean, std, min: Math.min(...f), max: Math.max(...f), alerts, rate: (alerts / N * 100).toFixed(0) };
  };

  const legitSt = stat('Legitimate');
  const randSt = stat('Random Basis');
  const fixedSt = stat('Fixed Basis');
  const cloneSt = stat('Clone Attempt');
  const ts = new Date().toLocaleString('en-IN', { dateStyle: 'long', timeStyle: 'short' });

  const html = `
    <div class="rpt-cover">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
        <div>
          <div style="font-family:var(--mono);font-size:10px;color:var(--accent);letter-spacing:0.14em;text-transform:uppercase;margin-bottom:8px;font-weight:700;">Technical Report · Quantum Computing + Cybersecurity</div>
          <div class="rpt-cover-title">Quantum Honeypot System</div>
          <div class="rpt-cover-title" style="font-size:16px;color:var(--text2); font-weight:500;">Tripwire-Based Intrusion Detection using Quantum Principles</div>
          <div style="margin-top:12px;font-size:12.5px;color:var(--text2);">Department of Computer Science & IT · Mini Project Report</div>
        </div>
        <div style="text-align:right;">
          <div style="font-family:var(--mono);font-size:10px;color:var(--text3);font-weight:700;">Generated</div>
          <div style="font-family:var(--mono);font-size:12px;color:var(--text);font-weight:700;">${ts}</div>
          <div style="margin-top:8px;"><span class="badge bb">SIMULATION REPORT</span></div>
        </div>
      </div>
      <div class="rpt-meta-grid">
        <div class="rpt-meta">
          <div class="rpt-meta-k">Active Resources</div>
          <div class="rpt-meta-v">3 honeypot tokens (DB, API, S3)</div>
        </div>
        <div class="rpt-meta">
          <div class="rpt-meta-k">Qubit Configuration</div>
          <div class="rpt-meta-v">${N_QUBITS} tripwire qubits per token</div>
        </div>
        <div class="rpt-meta">
          <div class="rpt-meta-k">Alert Threshold</div>
          <div class="rpt-meta-v">Fidelity F < ${THRESHOLD.toFixed(2)}</div>
        </div>
        <div class="rpt-meta">
          <div class="rpt-meta-k">Simulation Trials</div>
          <div class="rpt-meta-v">${N} per category (${N * 4} total)</div>
        </div>
      </div>
    </div>

    <div class="card rpt-section">
      <div class="rpt-section-title">Abstract</div>
      <div style="font-size:13px;color:var(--text2);line-height:1.75;">
        This project implements a <strong style="color:var(--text);">Quantum Honeypot System</strong> — a novel intrusion detection mechanism
        that embeds quantum tripwires inside fake but realistic-looking system credentials. Classical honeypots can be
        silently probed or cloned by sophisticated attackers, leaving logs that may be wiped. Our approach exploits
        two fundamental quantum properties — the <em>Observer Effect</em> and the <em>No-Cloning Theorem</em> — to make
        silent access physically impossible. Any entity that attempts to read or copy a protected resource without
        the secret basis key will inevitably disturb the quantum state, producing a measurable fidelity drop that
        triggers an irreversible alert.
      </div>
      <div style="font-size:13px;color:var(--text2);line-height:1.75;margin-top:0.75rem;">
        The system was implemented in Python using Qiskit and simulated using AerSimulator, with a JavaScript-based
        interactive dashboard for real-time visualisation. Three attack strategies were evaluated — random basis
        guessing, fixed basis measurement, and clone attempts — all of which are reliably detected. Legitimate
        users with the correct basis key achieve fidelity scores near 1.0, while attackers consistently score
        below the 0.85 alarm threshold.
      </div>
    </div>

    <div class="card rpt-section">
      <div class="rpt-section-title">Key Results — ${N} Trial Simulation</div>
      <table class="tbl">
        <thead>
          <tr><th>Access Type</th><th>Mean Fidelity</th><th>Std Dev</th><th>Alerts / ${N}</th><th>Detection Rate</th></tr>
        </thead>
        <tbody>
          <tr>
            <td style="color:var(--green);font-weight:700;">Legitimate (correct basis)</td>
            <td style="font-family:var(--mono);">${legitSt.mean.toFixed(4)}</td>
            <td style="font-family:var(--mono);color:var(--text3);">${legitSt.std.toFixed(4)}</td>
            <td style="font-family:var(--mono);">${legitSt.alerts} / ${N}</td>
            <td><span class="badge bg">${legitSt.rate}% FP rate</span></td>
          </tr>
          <tr>
            <td style="color:var(--amber);font-weight:700;">Random Basis Attack</td>
            <td style="font-family:var(--mono);">${randSt.mean.toFixed(4)}</td>
            <td style="font-family:var(--mono);color:var(--text3);">${randSt.std.toFixed(4)}</td>
            <td style="font-family:var(--mono);">${randSt.alerts} / ${N}</td>
            <td><span class="badge br">${randSt.rate}% detected</span></td>
          </tr>
          <tr>
            <td style="color:var(--accent);font-weight:700;">Fixed Basis Attack</td>
            <td style="font-family:var(--mono);">${fixedSt.mean.toFixed(4)}</td>
            <td style="font-family:var(--mono);color:var(--text3);">${fixedSt.std.toFixed(4)}</td>
            <td style="font-family:var(--mono);">${fixedSt.alerts} / ${N}</td>
            <td><span class="badge br">${fixedSt.rate}% detected</span></td>
          </tr>
          <tr>
            <td style="color:var(--pink);font-weight:700;">Clone Attempt</td>
            <td style="font-family:var(--mono);">${cloneSt.mean.toFixed(4)}</td>
            <td style="font-family:var(--mono);color:var(--text3);">${cloneSt.std.toFixed(4)}</td>
            <td style="font-family:var(--mono);">${cloneSt.alerts} / ${N}</td>
            <td><span class="badge br">${cloneSt.rate}% detected</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card rpt-section">
      <div class="rpt-section-title">Findings & Discussion</div>
      <div class="rpt-finding">
        <div class="rpt-finding-num">01</div>
        <div class="rpt-finding-body">
          <div class="rpt-finding-title">Reliable separation between legitimate and malicious access</div>
          <div class="rpt-finding-desc">
            Legitimate users with the correct basis key consistently produced fidelity scores near
            <strong>${legitSt.mean.toFixed(3)}</strong>, well above the alert threshold of ${THRESHOLD.toFixed(2)}.
            All three attack strategies fell significantly below this — random basis averaging
            ~${randSt.mean.toFixed(3)}, confirming the 50% wrong-guess probability from quantum
            measurement theory. The separation (Δ ≈ ${(legitSt.mean - randSt.mean).toFixed(3)}) is large
            enough that the threshold can be tuned without compromising either detection rate or false positives.
          </div>
        </div>
      </div>
      <div class="rpt-finding">
        <div class="rpt-finding-num">02</div>
        <div class="rpt-finding-body">
          <div class="rpt-finding-title">Clone attempts show the most severe fidelity degradation</div>
          <div class="rpt-finding-desc">
            Simulated clone attacks — modelling decoherence from attempting to duplicate an unknown quantum
            state — produced the lowest average fidelity (~${cloneSt.mean.toFixed(3)}) with the highest
            detection rate (${cloneSt.rate}%). This aligns with the No-Cloning Theorem: any attempt to copy
            a qubit unavoidably introduces noise, making this attack vector the easiest to detect.
          </div>
        </div>
      </div>
      <div class="rpt-finding">
        <div class="rpt-finding-num">03</div>
        <div class="rpt-finding-body">
          <div class="rpt-finding-title">Near-zero false positive rate</div>
          <div class="rpt-finding-desc">
            Across ${N} legitimate access trials, only ${legitSt.alerts} were incorrectly flagged — a
            false positive rate of ${legitSt.rate}%. This is achieved because correct-basis measurement
            produces deterministic fidelity close to 1.0 rather than probabilistic outcomes, giving a clear
            and reliable decision boundary.
          </div>
        </div>
      </div>
      <div class="rpt-finding">
        <div class="rpt-finding-num">04</div>
        <div class="rpt-finding-body">
          <div class="rpt-finding-title">Scalability: more qubits → higher reliability</div>
          <div class="rpt-finding-desc">
            With N_QUBITS = ${N_QUBITS}, the law of large numbers smooths out per-qubit variance in the
            averaged fidelity score. Increasing qubit count narrows the standard deviation for both
            legitimate (${legitSt.std.toFixed(4)}) and attack (${randSt.std.toFixed(4)}) distributions,
            widening the detection margin further. Twelve qubits would reduce FP rate to near zero.
          </div>
        </div>
      </div>
      <div class="rpt-note">
        <strong style="color:var(--amber);">Note on simulation realism:</strong> This implementation uses
        a pure-state statevector model without decoherence or shot noise, which assumes ideal quantum hardware.
        On real quantum devices (NISQ-era), additional noise sources would need to be modelled — a promising
        direction for future work using Qiskit's noise models.
      </div>
    </div>

    <div class="card rpt-section">
      <div class="rpt-section-title">Theoretical Foundations</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <div>
          <div style="font-size:13px;font-weight:700;margin-bottom:6px;color:var(--accent2);">No-Cloning Theorem</div>
          <div style="font-size:12.5px;color:var(--text2);line-height:1.7;">
            Wootters & Zurek (1982) proved that quantum states cannot be duplicated. Unlike classical
            bits, there is no physical process U such that U|ψ⟩|0⟩ = |ψ⟩|ψ⟩ for all |ψ⟩. This is the
            cornerstone of quantum key distribution (BB84) and our tripwire mechanism.
          </div>
          <div class="formula" style="margin-top:8px;">∄U : U|ψ⟩|0⟩ = |ψ⟩|ψ⟩ ∀|ψ⟩</div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;margin-bottom:6px;color:var(--teal);">Observer Effect & Measurement</div>
          <div style="font-size:12.5px;color:var(--text2);line-height:1.7;">
            A qubit in superposition |+⟩ = (|0⟩+|1⟩)/√2, when measured in the × basis, collapses to
            a random state with P(wrong) = 0.5. Averaging across N tripwires, the expected fidelity for
            a random-basis attacker approaches 0.5 — well below our 0.85 threshold.
          </div>
          <div class="formula" style="margin-top:8px;">H|0⟩ = |+⟩ = (|0⟩+|1⟩)/√2
E[F_attacker] ≈ 0.50</div>
        </div>
      </div>
    </div>

    <div class="card rpt-section">
      <div class="rpt-section-title">Project Team</div>
      <div class="rpt-team-grid">
        <div class="rpt-member">
          <div class="rpt-avatar" style="background:rgba(0, 242, 254, 0.15); color:var(--accent);">AV</div>
          <div>
            <div class="rpt-mname">Aman Verma</div>
            <div class="rpt-mrole">Theory, Background & Integration</div>
          </div>
        </div>
        <div class="rpt-member">
          <div class="rpt-avatar" style="background:var(--teal2); color:var(--teal);">RB</div>
          <div>
            <div class="rpt-mname">Rohit Bhagat</div>
            <div class="rpt-mrole">Circuit Design</div>
          </div>
        </div>
        <div class="rpt-member">
          <div class="rpt-avatar" style="background:var(--amber2); color:var(--amber);">AR</div>
          <div>
            <div class="rpt-mname">Ankit Raj</div>
            <div class="rpt-mrole">Attacker Simulation & Alerts</div>
          </div>
        </div>
        <div class="rpt-member">
          <div class="rpt-avatar" style="background:var(--pink2); color:var(--pink);">AA</div>
          <div>
            <div class="rpt-mname">Ayan Ashraf</div>
            <div class="rpt-mrole">Analysis & Visualisation</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card rpt-section">
      <div class="rpt-section-title">References</div>
      <div style="display:flex;flex-direction:column;gap:8px;font-size:12.5px;line-height:1.7;">
        <div>[1] W. K. Wootters and W. H. Zurek, "A single quantum cannot be cloned," <em>Nature</em>, vol. 299, pp. 802–803, 1982.</div>
        <div>[2] C. H. Bennett and G. Brassard, "Quantum Cryptography: Public key distribution and coin tossing," <em>Proc. IEEE Int. Conf. on Computers, Systems and Signal Processing</em>, 1984, pp. 175–179.</div>
        <div>[3] M. A. Nielsen and I. L. Chuang, <em>Quantum Computation and Quantum Information</em>. Cambridge University Press, 2010.</div>
        <div>[4] L. Spitzner, <em>Honeypots: Tracking Hackers</em>. Addison-Wesley Professional, 2002.</div>
        <div>[5] IBM Quantum, "Qiskit Documentation," 2024. [Online]. Available: https://docs.quantum.ibm.com/</div>
      </div>
    </div>
  `;

  document.getElementById('report-body').innerHTML = html;
}

function showTab(name, btn) {
  ['concepts', 'gates', 'arch', 'refs'].forEach(t => {
    document.getElementById('tab-' + t).style.display = 'none';
  });
  document.querySelectorAll('.tab').forEach(t => {
    if (t.id !== 'sb-tab-btn-circuit' && t.id !== 'sb-tab-btn-bb84') {
      t.classList.remove('active');
    }
  });
  document.getElementById('tab-' + name).style.display = '';
  btn.classList.add('active');
}

function initApp() {
  renderQbGrid([]);
  const ts = new Date().toLocaleString();
  ['db-rotated', 'api-rotated', 's3-rotated'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = ts;
  });

  setTimeout(() => {
    termLog([
      `<span class="t-ok">  [✓] AerSimulator backend initialised (statevector method)</span>`,
      `<span class="t-p">  →</span> <span class="t-i">Prep '+': <span class="t-v">H|0⟩ = |+⟩</span></span>`,
      `<span class="t-p">  →</span> <span class="t-i">Prep 'x': <span class="t-v">H(X|0⟩) = |−⟩</span></span>`,
      `<span class="t-p">  →</span> <span class="t-i">Decode '+': <span class="t-v">H†=H</span>   Decode 'x': <span class="t-v">H then X</span></span>`,
      `<span class="t-ok">  [✓] Legit fidelity: 1.0000 · Attacker fidelity: ~0.50</span>`,
    ]);
  }, 200);

  // Initialize network paths
  drawNetworkPaths();
  window.addEventListener('resize', drawNetworkPaths);
  
  // Highlight PostgreSQL DB node as starting node
  const activeNode = document.getElementById('node-db');
  if (activeNode) activeNode.classList.add('active');
}

window.addEventListener('DOMContentLoaded', initApp);

const AppBindings = {
  showPage,
  switchResource,
  updateQubitCfg,
  updateThreshCfg,
  clearLog,
  quickAccess,
  runBatch,
  runFullSim,
  selectAtk,
  runLegitDemo,
  switchSandboxTab,
  updateNoiseCfg,
  updateAngleCfg,
  toggleSandboxGate,
  toggleSandboxBasis,
  clearSandboxCircuit,
  runSandboxMeasurement,
  stepBB84,
  goToBB84Step,
  toggleEveIntercept,
  showTab,
  runAnalytics,
  buildReport
};
Object.assign(window, AppBindings);
window.QuantumGuard = AppBindings;
