/**
 * QuantumGuard API Client
 * Centralized asynchronous interface for FastAPI backend & Server-Sent Events (SSE).
 */

const API_BASE = window.location.origin;

class QuantumGuardAPI {
  constructor() {
    this.token = localStorage.getItem('quantumguard_token') || null;
    this.currentUser = JSON.parse(localStorage.getItem('quantumguard_user') || 'null');
    this.sseSource = null;
  }

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async login(username, password) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Authentication failed');
    }
    const data = await res.json();
    this.token = data.access_token;
    this.currentUser = data.user;
    localStorage.setItem('quantumguard_token', this.token);
    localStorage.setItem('quantumguard_user', JSON.stringify(this.currentUser));
    return data;
  }

  logout() {
    this.token = null;
    this.currentUser = null;
    localStorage.removeItem('quantumguard_token');
    localStorage.removeItem('quantumguard_user');
  }

  async getMe() {
    if (!this.token) return null;
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, { headers: this.getHeaders() });
    if (!res.ok) {
      this.logout();
      return null;
    }
    return await res.json();
  }

  async getOverview() {
    const res = await fetch(`${API_BASE}/api/v1/soc/overview`);
    if (!res.ok) throw new Error('Failed to fetch SOC overview');
    return await res.json();
  }

  async getEvents(limit = 50, offset = 0, search = '') {
    let url = `${API_BASE}/api/v1/soc/events?limit=${limit}&offset=${offset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch security events');
    return await res.json();
  }

  async getAlerts() {
    const res = await fetch(`${API_BASE}/api/v1/soc/alerts`);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return await res.json();
  }

  async ackAlert(alertId) {
    const res = await fetch(`${API_BASE}/api/v1/soc/alerts/${alertId}/ack`, {
      method: 'POST',
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Failed to acknowledge alert');
    return await res.json();
  }

  async getIncidents() {
    const res = await fetch(`${API_BASE}/api/v1/soc/incidents`);
    if (!res.ok) throw new Error('Failed to fetch incidents');
    return await res.json();
  }

  async updateIncidentStatus(incidentId, status, resolutionNote = '') {
    const res = await fetch(`${API_BASE}/api/v1/soc/incidents/${incidentId}/status`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify({ status, resolution_note: resolutionNote })
    });
    if (!res.ok) throw new Error('Failed to update incident status');
    return await res.json();
  }

  async addIncidentNote(incidentId, content) {
    const res = await fetch(`${API_BASE}/api/v1/soc/incidents/${incidentId}/notes`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error('Failed to add note');
    return await res.json();
  }

  async getDecoys() {
    const res = await fetch(`${API_BASE}/api/v1/soc/decoys`);
    if (!res.ok) throw new Error('Failed to fetch decoys');
    return await res.json();
  }

  async simulateBreach(tokenId = 'qtok_stripe_live_prod', sourceIp = '198.51.100.77') {
    const res = await fetch(`${API_BASE}/api/v1/soc/decoys/simulate-breach?token_id=${tokenId}&source_ip=${sourceIp}`, {
      method: 'POST',
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Failed to trigger breach drill');
    return await res.json();
  }

  connectSSE(onEvent, onStatusChange) {
    if (this.sseSource) {
      this.sseSource.close();
    }
    if (onStatusChange) onStatusChange('CONNECTING');
    
    this.sseSource = new EventSource(`${API_BASE}/api/v1/soc/stream`);
    
    this.sseSource.onopen = () => {
      if (onStatusChange) onStatusChange('ONLINE');
    };
    
    this.sseSource.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (onEvent) onEvent(payload);
      } catch (err) {
        // Heartbeat or malformed
      }
    };
    
    this.sseSource.onerror = () => {
      if (onStatusChange) onStatusChange('RECONNECTING');
    };
  }

  // Quantum Endpoints
  async quantumBloch(theta, phi, applyGate = null) {
    const res = await fetch(`${API_BASE}/api/v1/quantum/bloch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theta, phi, apply_gate: applyGate })
    });
    return await res.json();
  }

  async quantumCircuit(qubits, gates, shots = 1024) {
    const res = await fetch(`${API_BASE}/api/v1/quantum/circuit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qubits, gates, shots })
    });
    return await res.json();
  }

  async quantumBellCHSH(trials = 1000) {
    const res = await fetch(`${API_BASE}/api/v1/quantum/bell-chsh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trials })
    });
    return await res.json();
  }

  async quantumBB84(numBits = 32, eveIntercept = false, noiseRate = 0.0) {
    const res = await fetch(`${API_BASE}/api/v1/quantum/bb84`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_bits: numBits, eve_intercept: eveIntercept, noise_rate: noiseRate })
    });
    return await res.json();
  }

  async quantumGrover(numQubits = 3, targetState = 5) {
    const res = await fetch(`${API_BASE}/api/v1/quantum/grover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_qubits: numQubits, target_state: targetState })
    });
    return await res.json();
  }

  async quantumNoCloning() {
    const res = await fetch(`${API_BASE}/api/v1/quantum/no-cloning`);
    return await res.json();
  }
}

export const API = new QuantumGuardAPI();
