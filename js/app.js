/**
 * QuantumGuard Enterprise Web Application
 * Real-time SOC Dashboard, Threat Telemetry, and Interactive Quantum Lab.
 */

// Global State
let currentToken = localStorage.getItem('qg_token') || null;
let currentUser = JSON.parse(localStorage.getItem('qg_user') || 'null');
let sseConnection = null;
let activeDemoRunId = null;
let cachedThreatEvents = [];
let qubitTheta = 1.5707963;
let qubitPhi = 0.0;

const API_BASE = window.location.origin;

function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (currentToken) {
    headers['Authorization'] = `Bearer ${currentToken}`;
  }
  return headers;
}

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[character]);
}

// ── 1. Page Navigation ──
function navigateTo(viewName) {
  document.querySelectorAll('.view-panel').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));

  const panel = document.getElementById(`view-${viewName}`);
  if (panel) panel.style.display = 'block';

  const navBtn = Array.from(document.querySelectorAll('.nav-link')).find(btn => 
    btn.getAttribute('onclick')?.includes(viewName)
  );
  if (navBtn) navBtn.classList.add('active');

  // Load relevant data on view change
  if (viewName === 'dashboard') {
    refreshDashboard();
  } else if (viewName === 'threats') {
    loadThreatEvents();
    loadIncidents();
  } else if (viewName === 'decoys') {
    loadDecoys();
  } else if (viewName === 'lab') {
    applyQubitGate('I');
  } else if (viewName === 'reports') {
    const mdContent = document.getElementById('markdown-viewer-content');
    if (mdContent && mdContent.querySelector('[style*="Select"]')) {
      loadMarkdownDoc('README');
    }
  }
}

// ── 2. Authentication ──
function openLoginModal() {
  const modal = document.getElementById('login-modal');
  if (modal) modal.classList.add('open');
}

function closeLoginModal() {
  const modal = document.getElementById('login-modal');
  if (modal) modal.classList.remove('open');
  const err = document.getElementById('login-error');
  if (err) err.style.display = 'none';
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errBox = document.getElementById('login-error');
  const btn = document.getElementById('btn-login-submit');

  try {
    btn.textContent = 'Verifying...';
    btn.disabled = true;

    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Invalid username or password');
    }

    const data = await res.json();
    currentToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem('qg_token', currentToken);
    localStorage.setItem('qg_user', JSON.stringify(currentUser));

    closeLoginModal();
    renderAuthStatus();
    refreshDashboard();
    connectSSE();
  } catch (err) {
    if (errBox) {
      errBox.textContent = err.message;
      errBox.style.display = 'block';
    }
  } finally {
    btn.textContent = 'Sign In';
    btn.disabled = false;
  }
}

function handleLogout() {
  if (sseConnection) {
    sseConnection.abort();
    sseConnection = null;
  }
  currentToken = null;
  currentUser = null;
  localStorage.removeItem('qg_token');
  localStorage.removeItem('qg_user');
  cachedThreatEvents = [];
  for (const id of ['stat-total-events', 'stat-critical-alerts', 'stat-open-incidents', 'stat-active-decoys']) {
    const node = document.getElementById(id);
    if (node) node.textContent = '—';
  }
  for (const id of ['threat-table-body', 'decoys-table-body']) {
    const node = document.getElementById(id);
    if (node) node.replaceChildren();
  }
  const incidents = document.getElementById('incidents-list');
  if (incidents) incidents.replaceChildren();
  renderAuthStatus();
  connectSSE();
  navigateTo('dashboard');
}

function renderAuthStatus() {
  const container = document.getElementById('auth-container');
  if (!container) return;

  if (currentUser) {
    container.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;font-size:13px;">
        <span class="badge ${currentUser.role === 'admin' ? 'badge-critical' : 'badge-info'}">
          ${escapeHTML(currentUser.role.toUpperCase())}
        </span>
        <span style="font-weight:600;">${escapeHTML(currentUser.username)}</span>
        <button class="btn btn-secondary btn-sm" onclick="handleLogout()">Sign Out</button>
      </div>
    `;
  } else {
    container.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="openLoginModal()">Sign In</button>
    `;
  }
}

// ── 3. Dashboard Overview & Real Telemetry ──
async function refreshDashboard() {
  if (!currentToken) {
    const body = document.getElementById('overview-events-body');
    if (body) body.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;">Sign in to view operational telemetry.</td></tr>';
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/overview`, { headers: getAuthHeaders() });
    if (res.status === 401) throw new Error('Sign in to view operational telemetry.');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-total-events').textContent = data.total_events;
    document.getElementById('stat-critical-alerts').textContent = data.critical_alerts;
    document.getElementById('stat-open-incidents').textContent = data.open_incidents;
    document.getElementById('stat-active-decoys').textContent = data.active_decoys;

    // Load recent events preview
    const evRes = await fetch(`${API_BASE}/api/v1/soc/events?limit=8`, { headers: getAuthHeaders() });
    if (!evRes.ok) return;
    const evData = await evRes.json();
    renderOverviewEvents(evData.events || []);
  } catch (err) {
    console.error('Failed to refresh dashboard stats:', err);
  }
}

function renderOverviewEvents(events) {
  const tbody = document.getElementById('overview-events-body');
  if (!tbody) return;

  if (events.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted);">No security events recorded yet. Trigger a drill to simulate an attack.</td></tr>`;
    return;
  }

  tbody.innerHTML = events.map(e => {
    const sevBadge = e.severity === 'CRITICAL' ? 'badge-critical' : (e.severity === 'HIGH' ? 'badge-high' : 'badge-info');
    const time = new Date(e.timestamp).toLocaleTimeString();
    return `
      <tr>
        <td style="color:var(--text-muted);">${time}</td>
        <td><span class="badge badge-info">${escapeHTML(e.event_type)}</span></td>
        <td><span class="badge ${sevBadge}">${escapeHTML(e.severity)}</span></td>
        <td style="color:var(--text-main);font-weight:600;">${escapeHTML(e.source_ip)}</td>
        <td style="color:var(--text-secondary);font-size:11px;">${escapeHTML(e.mitre_technique_id)}</td>
        <td style="color:var(--text-main);max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHTML(e.message)}">${escapeHTML(e.message)}</td>
      </tr>
    `;
  }).join('');
}

// ── 4. Threats & Incidents ──
async function loadThreatEvents() {
  const tbody = document.getElementById('threat-table-body');
  const countBadge = document.getElementById('threat-event-count');
  if (!tbody) return;
  if (!currentToken) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;">Sign in to view security events.</td></tr>';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/events?limit=100`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error('API request failed');
    const data = await res.json();
    cachedThreatEvents = data.events || [];
    if (countBadge) countBadge.textContent = `${data.total} Total Events`;
    renderThreatTable(cachedThreatEvents);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--danger);">Error loading events: ${err.message}</td></tr>`;
  }
}

function renderThreatTable(events) {
  const tbody = document.getElementById('threat-table-body');
  if (!tbody) return;

  if (events.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted);">No security events recorded.</td></tr>`;
    return;
  }

  tbody.innerHTML = events.map(e => {
    const sevBadge = e.severity === 'CRITICAL' ? 'badge-critical' : (e.severity === 'HIGH' ? 'badge-high' : 'badge-info');
    const time = new Date(e.timestamp).toLocaleTimeString();
    return `
      <tr>
        <td style="color:var(--text-muted);">${time}</td>
        <td><span class="badge ${sevBadge}">${escapeHTML(e.severity)}</span></td>
        <td style="color:var(--accent);font-weight:600;">${escapeHTML(e.source_ip)}</td>
        <td style="font-size:11px;color:var(--text-secondary);">${escapeHTML(e.mitre_technique_id)}</td>
        <td style="color:var(--text-main);">${escapeHTML(e.message)}</td>
      </tr>
    `;
  }).join('');
}

function filterThreats(query) {
  if (!query) {
    renderThreatTable(cachedThreatEvents);
    return;
  }
  const q = query.toLowerCase();
  const filtered = cachedThreatEvents.filter(e =>
    (e.source_ip && e.source_ip.toLowerCase().includes(q)) ||
    (e.message && e.message.toLowerCase().includes(q)) ||
    (e.event_type && e.event_type.toLowerCase().includes(q))
  );
  renderThreatTable(filtered);
}

async function loadIncidents() {
  const container = document.getElementById('incidents-list');
  if (!container) return;
  if (!currentToken) {
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:2rem;">Sign in to view incidents.</div>';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/incidents`, { headers: getAuthHeaders() });
    if (!res.ok) return;
    const incidents = await res.json();

    if (incidents.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:2rem;color:var(--text-muted);font-size:13px;">No active incidents open.</div>`;
      return;
    }

    container.innerHTML = incidents.map(inc => {
      const isResolved = inc.status === 'RESOLVED' || inc.status === 'CLOSED';
      const statusBadge = isResolved ? 'badge-success' : 'badge-high';
      return `
        <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span class="badge ${statusBadge}">${escapeHTML(inc.status)}</span>
            <span style="font-size:11px;color:var(--text-muted);">${new Date(inc.created_at).toLocaleTimeString()}</span>
          </div>
          <div style="font-weight:600;font-size:13px;margin-bottom:4px;color:var(--text-main);">${escapeHTML(inc.title)}</div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:10px;">${escapeHTML(inc.summary)}</div>
          <div style="display:flex;gap:8px;">
            ${!isResolved ? `
              <button class="btn btn-secondary btn-sm" onclick="setIncidentStatus('${inc.id}', 'INVESTIGATING')">Investigate</button>
              <button class="btn btn-primary btn-sm" onclick="setIncidentStatus('${inc.id}', 'RESOLVED')">Resolve</button>
            ` : `<span style="font-size:12px;color:var(--success);font-weight:600;">✓ Resolved by Analyst</span>`}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:var(--danger);font-size:12px;">Error: ${err.message}</div>`;
  }
}

async function setIncidentStatus(id, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/incidents/${id}/status`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: newStatus, resolution_note: `Analyst marked as ${newStatus}` })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Operation failed. Please sign in with an Analyst/Admin account.');
    }
    loadIncidents();
    refreshDashboard();
  } catch (err) {
    alert(err.message);
  }
}

// ── 5. Decoys & Traps ──
async function loadDecoys() {
  const tbody = document.getElementById('decoys-table-body');
  if (!tbody) return;
  if (!currentToken) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;">Sign in to view deception assets.</td></tr>';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/decoys`, { headers: getAuthHeaders() });
    if (!res.ok) return;
    const decoys = await res.json();

    tbody.innerHTML = decoys.map(d => `
      <tr>
        <td style="color:var(--text-main);font-weight:600;">${escapeHTML(d.name)}</td>
        <td><span class="badge badge-info">${escapeHTML(d.decoy_type)}</span></td>
        <td style="color:var(--text-secondary);">${escapeHTML(d.target_service)}</td>
        <td style="color:var(--accent);font-family:var(--font-mono);">${escapeHTML(d.token_id)}</td>
        <td><span class="badge badge-success">${escapeHTML(d.status)}</span></td>
        <td style="color:${d.access_count > 0 ? 'var(--danger)' : 'var(--text-muted)'};font-weight:700;">${d.access_count}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--danger);padding:2rem;">Error: ${err.message}</td></tr>`;
  }
}

async function triggerDrill() {
  executeDrill('qtok_stripe_live_prod', '198.51.100.42');
}

async function executeCustomDrill() {
  const token = document.getElementById('drill-target').value;
  const ip = document.getElementById('drill-source-ip').value.trim() || '198.51.100.77';
  executeDrill(token, ip);
}

async function executeDrill(tokenId, sourceIp) {
  const box = document.getElementById('drill-output');
  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/decoys/simulate-breach?token_id=${tokenId}&source_ip=${sourceIp}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Drill failed. Please sign in as Analyst or Admin.');
    }

    const data = await res.json();
    if (box) {
      box.style.display = 'block';
      box.style.color = 'var(--success)';
      box.innerHTML = `
        <strong>[DRILL SUCCESS]</strong> Breach Event Emitted!<br>
        Event ID: ${data.event_id}<br>
        Alert: ${data.alert_generated}<br>
        Incident Assigned: ${data.incident_id}
      `;
    }

    refreshDashboard();
    loadDecoys();
  } catch (err) {
    if (box) {
      box.style.display = 'block';
      box.style.color = 'var(--danger)';
      box.textContent = `[ERROR] ${err.message}`;
    } else {
      alert(err.message);
    }
  }
}

async function runDemoScenario() {
  const startButton = document.getElementById('demo-start');
  const resetButton = document.getElementById('demo-reset');
  const status = document.getElementById('demo-status');
  const timeline = document.getElementById('demo-timeline');
  if (!currentToken) {
    status.textContent = 'Sign in with an Analyst or Admin account before running a demo.';
    return;
  }
  if (activeDemoRunId) {
    status.textContent = 'Reset the current demo run before starting another scenario.';
    return;
  }

  const scenario = document.getElementById('demo-scenario').value;
  const sourceIp = document.getElementById('demo-source-ip').value.trim();
  const requestedRunId = crypto.randomUUID();
  const params = new URLSearchParams({ scenario, source_ip: sourceIp, demo_run_id: requestedRunId });
  startButton.disabled = true;
  status.textContent = 'Submitting the synthetic event to the SOC ingestion pipeline...';
  timeline.replaceChildren();
  try {
    const response = await fetch(`${API_BASE}/api/v1/soc/decoys/simulate-breach?${params}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Demo failed (${response.status})`);
    activeDemoRunId = data.demo_run_id;
    resetButton.disabled = false;
    status.textContent = `Completed synthetic run ${data.demo_run_id}. Detection: ${data.alert_generated || 'no matching rule'}.`;
    const stages = [
      ['Scenario submitted', `Synthetic scenario: ${data.scenario}`],
      ['Event persisted', `Event ID ${data.event_id}`],
      ['Detection evaluated', data.alert_generated ? `Alert: ${data.alert_generated}` : 'No detection rule matched'],
      ['Incident correlated', data.incident_id ? `Incident ID ${data.incident_id}` : 'No incident created'],
      ['Audit recorded', 'The operator action and run identifier are retained in the audit log']
    ];
    for (const [title, detail] of stages) {
      const item = document.createElement('div');
      item.className = 'demo-timeline-item';
      const heading = document.createElement('strong');
      heading.textContent = title;
      const description = document.createElement('span');
      description.textContent = detail;
      item.append(heading, description);
      timeline.append(item);
    }
    refreshDashboard();
    loadThreatEvents();
    loadIncidents();
    loadDecoys();
  } catch (error) {
    status.textContent = `Demo error: ${error.message}`;
  } finally {
    startButton.disabled = Boolean(activeDemoRunId);
  }
}

async function resetDemoScenario() {
  if (!activeDemoRunId) return;
  if (!window.confirm('Remove this run’s synthetic events, alerts, and only its empty demo-owned incident?')) return;
  const resetButton = document.getElementById('demo-reset');
  const status = document.getElementById('demo-status');
  const timeline = document.getElementById('demo-timeline');
  resetButton.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/api/v1/soc/demo/runs/${encodeURIComponent(activeDemoRunId)}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Reset failed (${response.status})`);
    status.textContent = `Run reset. Removed ${data.events_removed} event(s) and ${data.alerts_removed} alert(s); audit record preserved.`;
    activeDemoRunId = null;
    timeline.replaceChildren();
    document.getElementById('demo-start').disabled = false;
    refreshDashboard();
    loadThreatEvents();
    loadIncidents();
    loadDecoys();
  } catch (error) {
    status.textContent = `Reset error: ${error.message}`;
    resetButton.disabled = false;
  }
}

function openDemoResearch() {
  navigateTo('lab');
  runBB84Test();
  runNoiseExperiment();
}

// ── 6. Quantum Laboratory Interactivity ──
async function applyQubitGate(gate) {
  const box = document.getElementById('bloch-result');
  try {
    const res = await fetch(`${API_BASE}/api/v1/quantum/bloch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theta: qubitTheta, phi: qubitPhi, apply_gate: gate === 'I' ? null : gate })
    });
    const data = await res.json();
    if (box) {
      box.innerHTML = `
        Gate Applied: <span style="color:var(--accent);font-weight:700;">${gate}</span><br>
        Statevector: [${data.statevector[0].real.toFixed(4)} + ${data.statevector[0].imag.toFixed(4)}i, ${data.statevector[1].real.toFixed(4)} + ${data.statevector[1].imag.toFixed(4)}i]<br>
        Measurement: P(|0⟩) = ${(data.probabilities['|0>'] * 100).toFixed(1)}% | P(|1⟩) = ${(data.probabilities['|1>'] * 100).toFixed(1)}%<br>
        Bloch Vector: (x=${data.bloch_coordinates.x.toFixed(3)}, y=${data.bloch_coordinates.y.toFixed(3)}, z=${data.bloch_coordinates.z.toFixed(3)})
      `;
    }
  } catch (err) {
    if (box) box.textContent = `Error: ${err.message}`;
  }
}

async function runBellTest() {
  const box = document.getElementById('chsh-result');
  try {
    box.textContent = 'Measuring 1000 entangled Bell pairs...';
    const res = await fetch(`${API_BASE}/api/v1/quantum/bell-chsh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trials: 1000 })
    });
    const data = await res.json();
    box.innerHTML = `
      CHSH Parameter S: <span style="color:var(--success);font-weight:700;font-size:14px;">${data.chsh_parameter_S}</span><br>
      Classical Local Bound: ≤ ${data.classical_bound.toFixed(1)}<br>
      Quantum Tsirelson Bound: ${data.tsirelson_quantum_bound.toFixed(4)}<br>
      Status: <span class="badge badge-success">VIOLATES CLASSICAL BOUND (Non-Local)</span><br>
      <span style="color:var(--text-secondary);font-size:11px;">Correlations: E(a1,b1)=${data.correlations['E(a1, b1)']} | E(a1,b2)=${data.correlations['E(a1, b2)']}</span>
    `;
  } catch (err) {
    box.textContent = `Error: ${err.message}`;
  }
}

async function runBellState() {
  const box = document.getElementById('bell-state-result');
  try {
    const response = await fetch(`${API_BASE}/api/v1/quantum/bell-state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shots: 1024, seed: 42 })
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Bell-state request failed (${response.status})`);
    }
    const data = await response.json();
    box.innerHTML = `${data.state}<br>
      Sample counts (|00⟩, |01⟩, |10⟩, |11⟩): ${data.sample_counts['00']}, ${data.sample_counts['01']}, ${data.sample_counts['10']}, ${data.sample_counts['11']}<br>
      Reduced-state purity: ${data.reduced_state_purity.toFixed(3)} · Concurrence: ${data.concurrence.toFixed(1)} · Entangled: ${data.entangled ? 'yes' : 'no'}<br>
      ${data.scientific_note}`;
  } catch (error) {
    box.textContent = `Error: ${error.message}`;
  }
}

async function runBB84Test() {
  const box = document.getElementById('bb84-result');
  const eveCheck = document.getElementById('bb84-eve-check');
  const eveIntercept = eveCheck ? eveCheck.checked : false;
  const numBits = Number(document.getElementById('bb84-bits')?.value || 512);
  const seed = Number(document.getElementById('bb84-seed')?.value || 84);
  const eveProbability = Number(document.getElementById('bb84-eve-probability')?.value || 0);
  const noiseRate = Number(document.getElementById('bb84-noise')?.value || 0);

  try {
    box.textContent = 'Running seeded BB84 transmission and basis sifting...';
    const res = await fetch(`${API_BASE}/api/v1/quantum/bb84`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        num_bits: numBits,
        eve_intercept: eveIntercept,
        eve_probability: eveIntercept ? eveProbability : 0,
        noise_rate: noiseRate,
        seed
      })
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `BB84 request failed (${res.status})`);
    }
    const data = await res.json();
    const qberPercent = (data.qber * 100).toFixed(1);
    const preview = (data.preview_table || []).map(row =>
      `<tr><td>${row.index}</td><td>${row.alice_bit} (${row.alice_basis})</td><td>${row.bob_bit} (${row.bob_basis})</td><td>${row.sifted ? 'yes' : 'no'}</td></tr>`
    ).join('');
    box.innerHTML = `
      Raw transmissions: ${data.total_raw_bits} · Matching-basis sifted bits: ${data.sifted_key_length} · Seed: ${seed}<br>
      Alice raw key: ${data.alice_raw_key}<br>
      Eve interception: ${data.eve_intercepted ? `${(data.eve_interception_probability * 100).toFixed(0)}%` : 'disabled'}<br>
      QBER: <strong style="color:${data.experiment_accepted ? 'var(--success)' : 'var(--danger)'};">${qberPercent}%</strong>
      (95% Wilson interval ${(data.qber_95_confidence_interval[0] * 100).toFixed(1)}–${(data.qber_95_confidence_interval[1] * 100).toFixed(1)}%; threshold ${(data.qber_threshold * 100).toFixed(0)}%)<br>
      Decision: <span class="badge ${data.experiment_accepted ? 'badge-success' : 'badge-critical'}">${data.experiment_accepted ? 'ACCEPTED IN SIMULATOR' : 'KEY DISCARDED'}</span><br>
      Alice/Bob sifted keys: ${data.alice_sifted_key || '(empty)'} / ${data.bob_sifted_key || '(empty)'}<br>
      Candidate key material: ${data.candidate_key_material || '(discarded)'}<br>
      Final key: not produced by this simulator (${data.key_status})
      <details><summary>First transmitted signals (raw key data is shown for this educational simulation)</summary>
      <table class="data-table"><thead><tr><th>Index</th><th>Alice bit/basis</th><th>Bob bit/basis</th><th>Sifted</th></tr></thead><tbody>${preview}</tbody></table></details>
      <p class="lab-note">${data.scientific_note}</p>
    `;
  } catch (err) {
    if (box) box.textContent = `Error: ${err.message}`;
  }
}

async function runGroverTest() {
  const box = document.getElementById('grover-result');
  const numQubits = Number(document.getElementById('grover-qubits')?.value || 3);
  const target = parseInt(document.getElementById('grover-target')?.value || '5', 10);
  const trials = Number(document.getElementById('grover-trials')?.value || 1000);
  const targetInput = document.getElementById('grover-target');
  const size = 2 ** numQubits;
  if (targetInput) {
    targetInput.max = String(size - 1);
  }
  if (!Number.isInteger(target) || target < 0 || target >= size) {
    box.textContent = `Choose a marked item from 0 to ${size - 1}.`;
    return;
  }

  try {
    box.textContent = `Benchmarking a ${size}-item search over ${trials} seeded trials...`;
    const res = await fetch(`${API_BASE}/api/v1/quantum/grover/benchmark`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_qubits: numQubits, marked_states: [target], trials, seed: 2026 })
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Grover request failed (${res.status})`);
    }
    const data = await res.json();
    const theory = (data.theoretical_success_probability * 100).toFixed(1);
    const observed = (data.empirical_success_probability * 100).toFixed(1);
    box.innerHTML = `
      Search space: ${data.search_space_size} · Marked items: ${data.marked_item_count} · Grover oracle queries: ${data.quantum_oracle_queries}<br>
      Theoretical success: <strong>${theory}%</strong> · Empirical (${data.trials} trials): <strong>${observed}%</strong><br>
      Classical expected queries under stated model: ${data.classical_expected_queries.toFixed(2)} · Simulator sampling time: ${(data.simulation_seconds * 1000).toFixed(2)} ms<br>
      <progress max="1" value="${data.empirical_success_probability}" aria-label="Observed Grover success probability"></progress>
      <p class="lab-note">${data.classical_query_assumption} ${data.query_complexity_note}</p>
    `;
  } catch (err) {
    box.textContent = `Error: ${err.message}`;
  }
}

function blochGraphic(vector, label) {
  const x = 60 + vector.x * 36;
  const y = 52 - vector.z * 36;
  return `<svg viewBox="0 0 120 104" role="img" aria-label="${label} Bloch vector x ${vector.x.toFixed(2)}, y ${vector.y.toFixed(2)}, z ${vector.z.toFixed(2)}">
    <circle cx="60" cy="52" r="36" fill="none" stroke="currentColor" opacity=".35"/>
    <path d="M20 52h80M60 10v84" stroke="currentColor" opacity=".25"/>
    <path d="M60 52L${x.toFixed(1)} ${y.toFixed(1)}" stroke="var(--accent)" stroke-width="2"/>
    <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="var(--accent)"/>
    <text x="60" y="101" text-anchor="middle" fill="currentColor" font-size="8">x/z projection · y=${vector.y.toFixed(2)}</text>
  </svg>`;
}

function selectedNoiseAngles() {
  const values = {
    zero: [0, 0],
    one: [Math.PI, 0],
    plus: [Math.PI / 2, 0],
    minus: [Math.PI / 2, Math.PI]
  };
  return values[document.getElementById('noise-state')?.value || 'plus'];
}

async function runNoiseExperiment() {
  const box = document.getElementById('noise-result');
  const [theta, phi] = selectedNoiseAngles();
  const probability = Number(document.getElementById('noise-strength')?.value || 0);
  const channel = document.getElementById('noise-channel')?.value || 'bit_flip';
  try {
    box.textContent = 'Calculating channel output...';
    const res = await fetch(`${API_BASE}/api/v1/quantum/noise`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel, probability, theta, phi })
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Noise request failed (${res.status})`);
    }
    const data = await res.json();
    box.innerHTML = `
      <div class="bloch-pair">${blochGraphic(data.bloch_before, 'Before noise')}${blochGraphic(data.bloch_after, 'After noise')}</div>
      Channel: ${data.channel} · Strength: ${data.probability.toFixed(2)} · Fidelity: ${data.fidelity.toFixed(4)} · Purity: ${data.purity.toFixed(4)}<br>
      Trace: ${data.trace.toFixed(6)} · Minimum density-matrix eigenvalue: ${data.minimum_eigenvalue.toExponential(2)}<br>
      Bloch vector before: (${data.bloch_before.x.toFixed(3)}, ${data.bloch_before.y.toFixed(3)}, ${data.bloch_before.z.toFixed(3)})<br>
      Bloch vector after: (${data.bloch_after.x.toFixed(3)}, ${data.bloch_after.y.toFixed(3)}, ${data.bloch_after.z.toFixed(3)})<br>
      ${data.scientific_note}
    `;
  } catch (error) {
    box.textContent = `Error: ${error.message}`;
  }
}

async function runRepetitionCode() {
  const box = document.getElementById('noise-result');
  const code = document.getElementById('code-type')?.value || 'bit_flip';
  const errorQubit = Number(document.getElementById('code-error-qubit')?.value || 1);
  try {
    const res = await fetch(`${API_BASE}/api/v1/quantum/repetition-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, logical_bit: 1, error_qubit: errorQubit })
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Repetition-code request failed (${res.status})`);
    }
    const data = await res.json();
    box.innerHTML = `
      <strong>${data.code.replace('_', '-')} code</strong> · Injected error: q${data.error_qubit}<br>
      Encoded logical state: ${data.encoded_logical_state} · Stabilizers: ${data.stabilizers}<br>
      Measured syndrome: (${data.syndrome.join(', ')}) · Apply ${data.correction_gate} to: ${data.correction_qubit === null ? 'none' : `q${data.correction_qubit}`}<br>
      Recovered logical bit: ${data.recovered_logical_bit ?? 'not measured'} · ${data.recovered ? 'single matching error corrected' : 'recovery unsuccessful'}<br>
      ${data.limitation}
    `;
  } catch (error) {
    box.textContent = `Error: ${error.message}`;
  }
}

async function runTeleportation() {
  const box = document.getElementById('teleport-result');
  const theta = Number(document.getElementById('teleport-theta')?.value || 0);
  const phi = Number(document.getElementById('teleport-phi')?.value || 0);
  try {
    box.textContent = 'Executing three-qubit teleportation circuit...';
    const res = await fetch(`${API_BASE}/api/v1/quantum/teleportation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theta, phi })
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Teleportation request failed (${res.status})`);
    }
    const data = await res.json();
    const outcomes = data.measurement_outcomes.map(item =>
      `${item.classical_bits}: ${(item.probability * 100).toFixed(1)}%`
    ).join(' · ');
    box.innerHTML = `
      Bell measurement outcomes: ${outcomes}<br>
      Classical communication: ${data.classical_bits_sent}<br>
      State fidelity after conditional correction: <strong>${data.fidelity.toFixed(8)}</strong><br>
      Input Bloch vector: (${data.bloch_input.x.toFixed(3)}, ${data.bloch_input.y.toFixed(3)}, ${data.bloch_input.z.toFixed(3)})<br>
      Reconstructed Bloch vector: (${data.bloch_reconstructed.x.toFixed(3)}, ${data.bloch_reconstructed.y.toFixed(3)}, ${data.bloch_reconstructed.z.toFixed(3)})<br>
      ${data.scientific_note}
    `;
  } catch (error) {
    box.textContent = `Error: ${error.message}`;
  }
}

// ── 7. Reports Export ──
async function exportData(format) {
  const btn = document.getElementById(`btn-export-${format}`);
  const statusEl = document.getElementById('export-status');

  if (!currentToken) {
    if (statusEl) {
      statusEl.style.color = 'var(--danger)';
      statusEl.textContent = '⚠ Please sign in to export data. Click "Sign In" in the top-right corner.';
      statusEl.style.display = 'block';
    } else {
      alert('Please sign in to download reports.');
    }
    return;
  }

  try {
    if (btn) { btn.disabled = true; btn.textContent = 'Preparing...'; }
    if (statusEl) { statusEl.textContent = `Generating ${format.toUpperCase()} export...`; statusEl.style.color = 'var(--text-secondary)'; statusEl.style.display = 'block'; }

    const res = await fetch(`${API_BASE}/api/v1/soc/reports/export?format=${format}`, {
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Export failed (${res.status})`);
    }

    const blob = await res.blob();
    const filename = format === 'csv' ? 'quantumguard_security_export.csv' : 'quantumguard_security_export.json';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    if (statusEl) {
      statusEl.style.color = 'var(--success)';
      statusEl.textContent = `✓ ${filename} downloaded successfully.`;
    }
  } catch (err) {
    if (statusEl) {
      statusEl.style.color = 'var(--danger)';
      statusEl.textContent = `✗ Export failed: ${err.message}`;
    } else {
      alert(`Export error: ${err.message}`);
    }
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = format === 'csv' ? 'Download CSV Export' : 'Download JSON Export'; }
  }
}

// ── 7b. Enhanced Markdown & Scientific Documentation Viewer ──
async function loadMarkdownDoc(docName) {
  const container = document.getElementById('markdown-viewer-content');
  const title = document.getElementById('markdown-viewer-title');
  if (!container) return;

  // Update active tab
  document.querySelectorAll('.doc-tab').forEach(t => t.classList.remove('active'));
  const activeTab = document.querySelector(`.doc-tab[data-doc="${docName}"]`);
  if (activeTab) activeTab.classList.add('active');

  container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-muted);"><span class="pulse"></span> Loading document...</div>';
  if (title) title.textContent = docName.replace(/_/g, ' ');

  try {
    const res = await fetch(`${API_BASE}/api/v1/soc/docs/${docName}`);
    if (!res.ok) throw new Error(`Document not found (${res.status})`);
    const md = await res.text();

    const renderedHTML = renderRichMarkdown(md);
    container.innerHTML = `<div class="md-body">${renderedHTML}</div>`;

    // Render Math with KaTeX if available
    if (window.renderMathInElement) {
      try {
        window.renderMathInElement(container, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
            { left: '\\[', right: '\\]', display: true },
            { left: '\\(', right: '\\)', display: false }
          ],
          throwOnError: false
        });
      } catch (mathErr) {
        console.warn('KaTeX auto-render error:', mathErr);
      }
    }

    // Attach copy button listeners
    container.querySelectorAll('.md-copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const code = btn.closest('.md-code-wrapper')?.querySelector('code')?.innerText || '';
        navigator.clipboard.writeText(code).then(() => {
          const orig = btn.textContent;
          btn.textContent = 'Copied!';
          setTimeout(() => btn.textContent = orig, 1800);
        });
      });
    });

  } catch (err) {
    container.innerHTML = `<div style="color:var(--danger);padding:2rem;">Error loading document: ${err.message}</div>`;
  }
}

function renderRichMarkdown(rawMd) {
  if (!rawMd) return '';
  let md = rawMd;

  // 1. Process GitHub Admonitions / Callouts (> [!NOTE], etc.)
  md = md.replace(/^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n((?:>.*(?:\n|$))*)/gim, (match, type, content) => {
    const cleanContent = content.split('\n').map(l => l.replace(/^>\s?/, '')).join('\n').trim();
    const t = type.toUpperCase();
    const icons = { NOTE: 'ℹ️ Note', TIP: '💡 Tip', IMPORTANT: '⚡ Important', WARNING: '⚠️ Warning', CAUTION: '🛑 Caution' };
    const classes = { NOTE: 'md-callout-note', TIP: 'md-callout-tip', IMPORTANT: 'md-callout-important', WARNING: 'md-callout-warning', CAUTION: 'md-callout-warning' };
    return `<div class="md-callout ${classes[t] || 'md-callout-note'}"><div class="md-callout-title">${icons[t] || t}</div><p>${cleanContent}</p></div>\n\n`;
  });

  // 2. Protect and Pre-format Math Blocks if KaTeX is not loaded
  const hasKatex = typeof window !== 'undefined' && Boolean(window.renderMathInElement || window.katex);
  const mathPlaceholders = [];

  // Protect display math $$...$$
  md = md.replace(/\$\$([\s\S]*?)\$\$/g, (match, eq) => {
    const idx = mathPlaceholders.length;
    if (hasKatex) {
      mathPlaceholders.push(`$$${eq}$$`);
    } else {
      mathPlaceholders.push(`<div class="md-math-display">${formatUnicodeMath(eq)}</div>`);
    }
    return `@@MATH_BLOCK_${idx}@@`;
  });

  // Protect inline math $...$
  md = md.replace(/\$([^\$\n\r]+?)\$/g, (match, eq) => {
    const idx = mathPlaceholders.length;
    if (hasKatex) {
      mathPlaceholders.push(`$${eq}$`);
    } else {
      mathPlaceholders.push(`<span class="md-math-inline">${formatUnicodeMath(eq)}</span>`);
    }
    return `@@MATH_INLINE_${idx}@@`;
  });

  // 3. Render Markdown through marked or robust fallback
  let html = '';
  if (window.marked && typeof window.marked.parse === 'function') {
    html = window.marked.parse(md);
  } else {
    html = renderMarkdownFallback(md);
  }

  // 4. Restore Math Placeholders
  mathPlaceholders.forEach((mathHtml, idx) => {
    html = html.replace(`@@MATH_BLOCK_${idx}@@`, mathHtml);
    html = html.replace(`@@MATH_INLINE_${idx}@@`, mathHtml);
    // Also handle if marked wrapped in <p> tags
    html = html.replace(`<p>@@MATH_BLOCK_${idx}@@</p>`, mathHtml);
    html = html.replace(`<p>@@MATH_INLINE_${idx}@@</p>`, mathHtml);
  });

  // 5. Enhance Code Blocks with Language Badges and Copy Buttons
  html = html.replace(/<pre><code(?:\s+class="language-([a-zA-Z0-9_-]+)")?>([\s\S]*?)<\/code><\/pre>/gi, (match, lang, code) => {
    const label = (lang || 'code').toUpperCase();
    return `<div class="md-code-wrapper"><div class="md-code-header"><span>${label}</span><button class="md-copy-btn">Copy</button></div><pre><code>${code}</code></pre></div>`;
  });

  // 6. Ensure all <table> elements are wrapped in responsive containers
  html = html.replace(/(<table[\s\S]*?<\/table>)/gi, '<div class="table-responsive">$1</div>');

  return html;
}

function formatUnicodeMath(latex) {
  let s = latex.trim();
  // Bra-ket notation
  s = s.replace(/\\langle\s*([0-9a-zA-Z\+\-\*]+)\s*\|/g, '⟨$1|');
  s = s.replace(/\|\s*([0-9a-zA-Z\+\-\*]+)\s*\\rangle/g, '|$1⟩');
  s = s.replace(/\\vert\s*([0-9a-zA-Z\+\-\*]+)\s*\\rangle/g, '|$1⟩');
  s = s.replace(/\\langle\s*([0-9a-zA-Z\+\-\*]+)\s*\\rangle/g, '⟨$1⟩');
  s = s.replace(/\\langle\s*\\sigma_([xyz])\s*\\rangle/g, '⟨σ_$1⟩');
  s = s.replace(/\\|0\\rangle/g, '|0⟩').replace(/\\|1\\rangle/g, '|1⟩');
  s = s.replace(/\\|\\psi\\rangle/g, '|ψ⟩').replace(/\\|\\Phi\^\\+\\rangle/g, '|Φ⁺⟩');
  s = s.replace(/\\|\\Phi\\^\\+\\rangle/g, '|Φ⁺⟩');

  // Greek letters
  s = s.replace(/\\alpha/g, 'α').replace(/\\beta/g, 'β')
       .replace(/\\theta/g, 'θ').replace(/\\phi/g, 'φ')
       .replace(/\\sigma/g, 'σ').replace(/\\pi/g, 'π')
       .replace(/\\psi/g, 'ψ').replace(/\\Phi/g, 'Φ')
       .replace(/\\rho/g, 'ρ').replace(/\\epsilon/g, 'ε');

  // Operators & symbols
  s = s.replace(/\\otimes/g, ' ⊗ ')
       .replace(/\\dagger/g, '†')
       .replace(/\\le/g, ' ≤ ')
       .replace(/\\ge/g, ' ≥ ')
       .replace(/\\approx/g, ' ≈ ')
       .replace(/\\neq/g, ' ≠ ')
       .replace(/\\in/g, ' ∈ ')
       .replace(/\\cdot/g, ' · ')
       .replace(/\\times/g, ' × ')
       .replace(/\\pm/g, ' ± ')
       .replace(/\\to/g, ' → ')
       .replace(/\\leftrightarrow/g, ' ↔ ');

  // Functions & fractions
  s = s.replace(/\\frac\{1\}\{\\sqrt\{2\}\}/g, '1/√2');
  s = s.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '($1 / $2)');
  s = s.replace(/\\sqrt\{2\}/g, '√2');
  s = s.replace(/\\sqrt\{([^}]+)\}/g, '√($1)');
  s = s.replace(/\\cos\\left\(\\frac\{([^}]+)\}\{([^}]+)\}\\right\)/g, 'cos($1/$2)');
  s = s.replace(/\\sin\\left\(\\frac\{([^}]+)\}\{([^}]+)\}\\right\)/g, 'sin($1/$2)');
  s = s.replace(/\\cos/g, 'cos').replace(/\\sin/g, 'sin');
  s = s.replace(/\\text\{([^}]+)\}/g, '$1').replace(/\\mathrm\{([^}]+)\}/g, '$1');
  s = s.replace(/\\left\(/g, '(').replace(/\\right\)/g, ')');
  s = s.replace(/\\begin\{pmatrix\}/g, '[').replace(/\\end\{pmatrix\}/g, ']');
  s = s.replace(/\\\\/g, '; ');
  s = s.replace(/&/g, ', ');

  return s;
}

function renderMarkdownFallback(md) {
  // Comprehensive standalone markdown fallback parser (tables, lists, headers, blocks)
  const lines = md.split('\n');
  let html = '';
  let inCodeBlock = false;
  let codeBlockLang = '';
  let codeBuffer = [];
  let inTable = false;
  let tableHeaderParsed = false;
  let inList = false;
  let listType = 'ul';

  function closeList() {
    if (inList) {
      html += `</${listType}>\n`;
      inList = false;
    }
  }

  function closeTable() {
    if (inTable) {
      html += `</tbody></table></div>\n`;
      inTable = false;
      tableHeaderParsed = false;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    // Code blocks
    if (line.startsWith('```')) {
      closeList();
      closeTable();
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockLang = line.replace(/^```/, '').trim();
        codeBuffer = [];
      } else {
        inCodeBlock = false;
        const codeContent = escapeHTML(codeBuffer.join('\n'));
        const label = (codeBlockLang || 'code').toUpperCase();
        html += `<div class="md-code-wrapper"><div class="md-code-header"><span>${label}</span><button class="md-copy-btn">Copy</button></div><pre><code>${codeContent}</code></pre></div>\n`;
      }
      continue;
    }
    if (inCodeBlock) {
      codeBuffer.push(rawLine);
      continue;
    }

    // Horizontal Rule
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(line)) {
      closeList();
      closeTable();
      html += `<hr>\n`;
      continue;
    }

    // Headings
    if (/^#+\s/.test(line)) {
      closeList();
      closeTable();
      const level = line.match(/^#+/)[0].length;
      const text = parseInlineMarkdown(line.replace(/^#+\s*/, ''));
      const tag = `h${Math.min(level, 6)}`;
      html += `<${tag}>${text}</${tag}>\n`;
      continue;
    }

    // Markdown Table
    if (line.startsWith('|') && line.endsWith('|')) {
      closeList();
      const cells = line.slice(1, -1).split('|').map(c => parseInlineMarkdown(c.trim()));
      
      // Separator row (|---|---|)
      if (cells.every(c => /^:?-+:?$/.test(c.replace(/<[^>]+>/g, '')))) {
        tableHeaderParsed = true;
        continue;
      }

      if (!inTable) {
        inTable = true;
        tableHeaderParsed = false;
        html += `<div class="table-responsive"><table class="data-table"><thead><tr>`;
        cells.forEach(c => html += `<th>${c}</th>`);
        html += `</tr></thead><tbody>\n`;
      } else {
        html += `<tr>`;
        cells.forEach(c => html += `<td>${c}</td>`);
        html += `</tr>\n`;
      }
      continue;
    } else {
      closeTable();
    }

    // Lists
    const ulMatch = line.match(/^[\*\-]\s+(.+)/);
    const olMatch = line.match(/^(\d+)\.\s+(.+)/);
    if (ulMatch || olMatch) {
      const isOl = Boolean(olMatch);
      const text = parseInlineMarkdown(isOl ? olMatch[2] : ulMatch[1]);
      if (!inList || (isOl && listType !== 'ol') || (!isOl && listType !== 'ul')) {
        closeList();
        listType = isOl ? 'ol' : 'ul';
        html += `<${listType}>\n`;
        inList = true;
      }
      html += `  <li>${text}</li>\n`;
      continue;
    } else {
      closeList();
    }

    // Blockquotes
    if (line.startsWith('>')) {
      const bqText = parseInlineMarkdown(line.replace(/^>\s?/, ''));
      html += `<blockquote>${bqText}</blockquote>\n`;
      continue;
    }

    // Blank line
    if (line === '') {
      continue;
    }

    // Paragraph
    html += `<p>${parseInlineMarkdown(line)}</p>\n`;
  }

  closeList();
  closeTable();
  return html;
}

function parseInlineMarkdown(text) {
  if (!text) return '';
  let s = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Bold & Italic
  s = s.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
  s = s.replace(/___(.+?)___/g, '<strong><em>$1</em></strong>');
  s = s.replace(/__(.+?)__/g, '<strong>$1</strong>');
  s = s.replace(/_(.+?)_/g, '<em>$1</em>');

  // Inline code
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Links
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Restore protected tags
  s = s.replace(/&lt;span class="md-math-inline"&gt;([\s\S]*?)&lt;\/span&gt;/g, '<span class="md-math-inline">$1</span>');
  s = s.replace(/&lt;div class="md-math-display"&gt;([\s\S]*?)&lt;\/div&gt;/g, '<div class="md-math-display">$1</div>');

  return s;
}

// ── 8. Real-time Server-Sent Events (SSE) ──
async function connectSSE() {
  if (sseConnection) sseConnection.abort();
  const sseBadge = document.getElementById('sse-badge');
  const sseLabel = document.getElementById('sse-label');
  if (!currentToken) {
    if (sseLabel) sseLabel.textContent = 'SIGN IN FOR LIVE STREAM';
    return;
  }

  const controller = new AbortController();
  sseConnection = controller;
  try {
    const response = await fetch(`${API_BASE}/api/v1/soc/stream`, {
      headers: getAuthHeaders(),
      signal: controller.signal
    });
    if (response.status === 401) {
      handleLogout();
      openLoginModal();
      const errBox = document.getElementById('login-error');
      if (errBox) {
        errBox.textContent = 'Your saved sign-in has expired. Please sign in again.';
        errBox.style.display = 'block';
      }
      return;
    }
    if (!response.ok || !response.body) {
      throw new Error(`SSE connection failed (${response.status})`);
    }
    if (sseBadge) sseBadge.className = 'live-badge';
    if (sseLabel) sseLabel.textContent = 'SSE LIVE';
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const messages = buffer.split('\n\n');
      buffer = messages.pop() || '';
      for (const message of messages) {
        const line = message.split('\n').find(part => part.startsWith('data: '));
        if (!line) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'NEW_SECURITY_EVENT') {
            cachedThreatEvents.unshift(data.event);
            renderThreatTable(cachedThreatEvents);
            refreshDashboard();
            loadIncidents();
          }
        } catch (error) {
          console.warn('Ignoring malformed SSE message:', error);
        }
      }
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      if (sseLabel) sseLabel.textContent = 'STREAM UNAVAILABLE';
      console.warn('SSE connection ended:', error);
      if (currentToken) window.setTimeout(connectSSE, 3000);
    }
  }
}

// ── 9. Initialization ──
async function init() {
  if (currentToken) {
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: getAuthHeaders()
      });
      if (response.status === 401) {
        handleLogout();
        openLoginModal();
        const errBox = document.getElementById('login-error');
        if (errBox) {
          errBox.textContent = 'Your saved sign-in has expired. Please sign in again.';
          errBox.style.display = 'block';
        }
        return;
      }
      if (response.ok) {
        currentUser = await response.json();
        localStorage.setItem('qg_user', JSON.stringify(currentUser));
      }
    } catch (error) {
      console.warn('Could not validate the saved sign-in:', error);
    }
  }
  renderAuthStatus();
  refreshDashboard();
  connectSSE();
}

// Expose methods to global window scope for inline HTML handlers
window.navigateTo = navigateTo;
window.openLoginModal = openLoginModal;
window.closeLoginModal = closeLoginModal;
window.handleLogin = handleLogin;
window.handleLogout = handleLogout;
window.refreshDashboard = refreshDashboard;
window.loadThreatEvents = loadThreatEvents;
window.filterThreats = filterThreats;
window.loadIncidents = loadIncidents;
window.setIncidentStatus = setIncidentStatus;
window.loadDecoys = loadDecoys;
window.triggerDrill = triggerDrill;
window.executeCustomDrill = executeCustomDrill;
window.runDemoScenario = runDemoScenario;
window.resetDemoScenario = resetDemoScenario;
window.openDemoResearch = openDemoResearch;
window.applyQubitGate = applyQubitGate;
window.runBellTest = runBellTest;
window.runBellState = runBellState;
window.runBB84Test = runBB84Test;
window.runGroverTest = runGroverTest;
window.runNoiseExperiment = runNoiseExperiment;
window.runRepetitionCode = runRepetitionCode;
window.runTeleportation = runTeleportation;
window.exportData = exportData;
window.loadMarkdownDoc = loadMarkdownDoc;

document.addEventListener('DOMContentLoaded', () => {
  const strength = document.getElementById('noise-strength');
  const strengthValue = document.getElementById('noise-strength-value');
  strength?.addEventListener('input', () => {
    if (strengthValue) strengthValue.value = Number(strength.value).toFixed(2);
  });
  document.getElementById('grover-qubits')?.addEventListener('change', event => {
    const target = document.getElementById('grover-target');
    const maxTarget = 2 ** Number(event.target.value) - 1;
    if (target) {
      target.max = String(maxTarget);
      if (Number(target.value) > maxTarget) target.value = String(maxTarget);
    }
  });
  for (const [sliderId, outputId, digits] of [
    ['bb84-eve-probability', 'bb84-eve-value', 2],
    ['bb84-noise', 'bb84-noise-value', 2]
  ]) {
    const slider = document.getElementById(sliderId);
    const output = document.getElementById(outputId);
    slider?.addEventListener('input', () => {
      if (output) output.value = Number(slider.value).toFixed(digits);
    });
  }
  init();
});
