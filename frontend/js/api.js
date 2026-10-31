/**
 * FraudShield AI - REST API Client & Realistic Preview Engine
 * Centralizes all HTTP communication with the FastAPI backend.
 * Provides fallback to realistic demonstration baseline data when running standalone.
 */

const API_BASE = window.location.origin.includes('8000') || window.location.origin.includes('127.0.0.1')
  ? ''
  : 'http://127.0.0.1:8000';

// Realistic Demonstration Baseline Datasets (Clearly Labelled Demo Preview)
const DEMO_PREVIEW_DATA = {
  isDemo: true,
  disclaimer: "Demonstration preview baseline data. Real-time inference executes on live backend connection.",
  metrics: {
    total_evaluated: 128450,
    total_flagged: 1842,
    fraud_rate_percentage: 1.43,
    avg_risk_score: 18.4,
    pending_alerts: 3,
    active_model_version: "IsolationForest_v1.0.0_n150",
    distribution: {
      low: 114520,
      medium: 12088,
      high: 1422,
      critical: 420
    },
    hourly_trends: [
      { hour_label: "00:00", total_count: 1420, flagged_count: 18, total_volume: 852000.0 },
      { hour_label: "02:00", total_count: 850, flagged_count: 24, total_volume: 510000.0 },
      { hour_label: "04:00", total_count: 620, flagged_count: 15, total_volume: 372000.0 },
      { hour_label: "06:00", total_count: 1980, flagged_count: 12, total_volume: 1188000.0 },
      { hour_label: "08:00", total_count: 4850, flagged_count: 38, total_volume: 2910000.0 },
      { hour_label: "10:00", total_count: 8920, flagged_count: 72, total_volume: 5352000.0 },
      { hour_label: "12:00", total_count: 11400, flagged_count: 98, total_volume: 6840000.0 },
      { hour_label: "14:00", total_count: 13200, flagged_count: 115, total_volume: 7920000.0 },
      { hour_label: "16:00", total_count: 14500, flagged_count: 142, total_volume: 8700000.0 },
      { hour_label: "18:00", total_count: 16800, flagged_count: 184, total_volume: 10080000.0 },
      { hour_label: "20:00", total_count: 15200, flagged_count: 162, total_volume: 9120000.0 },
      { hour_label: "22:00", total_count: 7800, flagged_count: 85, total_volume: 4680000.0 }
    ],
    total_volume_inr: 58524000.0,
    amount_distribution: [
      { bracket_label: "Micro (< ₹500)", min_amount: 0.0, max_amount: 500.0, total_count: 54100, flagged_count: 210, total_volume: 1352500.0 },
      { bracket_label: "Small (₹500 - ₹2,000)", min_amount: 500.0, max_amount: 2000.0, total_count: 42100, flagged_count: 320, total_volume: 3789000.0 },
      { bracket_label: "Medium (₹2,000 - ₹10,000)", min_amount: 2000.0, max_amount: 10000.0, total_count: 21400, flagged_count: 480, total_volume: 8560000.0 },
      { bracket_label: "Large (₹10,000 - ₹25,000)", min_amount: 10000.0, max_amount: 25000.0, total_count: 7200, flagged_count: 390, total_volume: 11520000.0 },
      { bracket_label: "Very Large (₹25,000 - ₹50,000)", min_amount: 25000.0, max_amount: 50000.0, total_count: 2450, flagged_count: 280, total_volume: 8575000.0 },
      { bracket_label: "Whale (> ₹50,000)", min_amount: 50000.0, max_amount: null, total_count: 1200, flagged_count: 162, total_volume: 8400000.0 }
    ],
    frequency_distribution: [
      { frequency_label: "Single Txn (1.0x)", count: 110400, percentage: 86.0, flagged_count: 420 },
      { frequency_label: "Moderate (2 - 3 txs)", count: 14200, percentage: 11.1, flagged_count: 650 },
      { frequency_label: "High Velocity (4 - 5 txs)", count: 2850, percentage: 2.2, flagged_count: 482 },
      { frequency_label: "Critical Burst (6+ txs)", count: 1000, percentage: 0.7, flagged_count: 290 }
    ],
    fraud_vs_legit: {
      has_ground_truth_labels: true,
      ground_truth_fraud: 250,
      ground_truth_legitimate: 6208,
      operational_confirmed_fraud: 142,
      operational_confirmed_legit: 11420,
      operational_under_review: 48,
      model_flagged_anomalies: 1842,
      anomaly_vs_fraud_explanation: "Distinction: An Isolation Forest anomaly represents an unsupervised statistical deviation (unusual velocity, device, or amount). Confirmed fraud requires verified chargeback labels or explicit SOC analyst blocking (BLOCKED status)."
    },
    model_metrics: {
      precision: 0.5461,
      recall: 0.8280,
      f1_score: 0.6581,
      false_positive_rate: 0.0277,
      false_negative_rate: 0.1720,
      specificity: 0.9723,
      balanced_accuracy: 0.9001,
      roc_auc: 0.9726,
      pr_auc: 0.8250,
      confusion_matrix: {
        true_positives: 207,
        false_positives: 172,
        true_negatives: 6036,
        false_negatives: 43
      },
      model_name: "IsolationForest",
      contamination: 0.0387,
      total_evaluated_samples: 6458
    }
  },
  transactions: [
    {
      tx_id: "TXN-DEMO-98214",
      timestamp: new Date(Date.now() - 4 * 60000).toISOString(),
      sender_upi: "vikram.patel@okhdfcbank",
      receiver_upi: "unknown.mule.crypto@ybl",
      amount: 85000.0,
      channel: "INTENT_FLOW",
      device_id: "DEV-NEW-IMEI-882",
      risk_score: 94.8,
      risk_tier: "CRITICAL",
      status: "BLOCKED",
      primary_factor: "SIM Swap Surge + New Device",
      is_flagged: 1,
      anomaly_score: -0.284,
      location_city: "Mumbai",
      explanations: [
        { factor_name: "DEVICE_ANOMALY", weight: 0.35, severity: "CRITICAL", description: "First transaction observed on unverified hardware fingerprint DEV-NEW-IMEI-882." },
        { factor_name: "AMOUNT_DEVIATION", weight: 0.32, severity: "CRITICAL", description: "Amount ₹85,000 exceeds 30-day user rolling mean (₹2,100) by 40.4x." },
        { factor_name: "TEMPORAL_OUTLIER", weight: 0.20, severity: "HIGH", description: "Payment attempted outside user historical diurnal activity cluster (02:14 IST)." }
      ]
    },
    {
      tx_id: "TXN-DEMO-98213",
      timestamp: new Date(Date.now() - 11 * 60000).toISOString(),
      sender_upi: "neha.gupta@paytm",
      receiver_upi: "fast.cash.collect@axl",
      amount: 9800.0,
      channel: "COLLECT_REQUEST",
      device_id: "DEV-ONEPLUS-9R",
      risk_score: 78.4,
      risk_tier: "HIGH",
      status: "UNDER_REVIEW",
      primary_factor: "High Velocity Collect Request",
      is_flagged: 1,
      anomaly_score: -0.198,
      location_city: "Delhi",
      explanations: [
        { factor_name: "VELOCITY_SPIKE", weight: 0.42, severity: "HIGH", description: "6 outgoing transfers initiated within a rolling 2-minute interval." },
        { factor_name: "COLLECT_CHANNEL_RISK", weight: 0.30, severity: "HIGH", description: "Collect request authorization to unverified recipient handle." }
      ]
    },
    {
      tx_id: "TXN-DEMO-98212",
      timestamp: new Date(Date.now() - 18 * 60000).toISOString(),
      sender_upi: "arjun.sharma@okaxis",
      receiver_upi: "nature.groceries@icici",
      amount: 450.0,
      channel: "UPI_APP",
      device_id: "DEV-XIAOMI-12",
      risk_score: 8.2,
      risk_tier: "LOW",
      status: "APPROVED",
      primary_factor: "Legitimate Baseline Purchase",
      is_flagged: 0,
      anomaly_score: 0.215,
      location_city: "Bengaluru",
      explanations: [
        { factor_name: "KNOWN_MERCHANT", weight: -0.25, severity: "LOW", description: "Recipient is a verified Category Code 5411 merchant with repeat payment history." },
        { factor_name: "TRUSTED_DEVICE", weight: -0.20, severity: "LOW", description: "Hardware signature DEV-XIAOMI-12 bound to account for > 180 days." }
      ]
    },
    {
      tx_id: "TXN-DEMO-98211",
      timestamp: new Date(Date.now() - 26 * 60000).toISOString(),
      sender_upi: "rohit.mehta@oksbi",
      receiver_upi: "cloud.hosting.services@hdfc",
      amount: 4200.0,
      channel: "INTENT_FLOW",
      device_id: "DEV-MACBOOK-AIR",
      risk_score: 22.5,
      risk_tier: "LOW",
      status: "APPROVED",
      primary_factor: "Routine SaaS Subscription",
      is_flagged: 0,
      anomaly_score: 0.142,
      location_city: "Pune",
      explanations: [
        { factor_name: "RECURRING_INTERVAL", weight: -0.15, severity: "LOW", description: "Matches 30-day recurring cloud subscription window." }
      ]
    },
    {
      tx_id: "TXN-DEMO-98210",
      timestamp: new Date(Date.now() - 34 * 60000).toISOString(),
      sender_upi: "priya.nair@barodampay",
      receiver_upi: "peer.split.dinner@okaxis",
      amount: 1650.0,
      channel: "UPI_APP",
      device_id: "DEV-IPHONE-14",
      risk_score: 14.1,
      risk_tier: "LOW",
      status: "APPROVED",
      primary_factor: "Standard Peer Transfer",
      is_flagged: 0,
      anomaly_score: 0.188,
      location_city: "Hyderabad",
      explanations: [
        { factor_name: "HISTORICAL_PEER", weight: -0.18, severity: "LOW", description: "Mutual contacts established in previous settlement cycles." }
      ]
    },
    {
      tx_id: "TXN-DEMO-98209",
      timestamp: new Date(Date.now() - 42 * 60000).toISOString(),
      sender_upi: "ananya.sen@ybl",
      receiver_upi: "urgent.lottery.claim@pnb",
      amount: 24999.0,
      channel: "COLLECT_REQUEST",
      device_id: "DEV-SAMSUNG-A52",
      risk_score: 64.5,
      risk_tier: "MEDIUM",
      status: "UNDER_REVIEW",
      primary_factor: "New Recipient + Urgent Collect",
      is_flagged: 1,
      anomaly_score: -0.092,
      location_city: "Kolkata",
      explanations: [
        { factor_name: "FIRST_TIME_RECIPIENT", weight: 0.28, severity: "MEDIUM", description: "No prior transactions recorded between sender and recipient." },
        { factor_name: "AMOUNT_SURGE", weight: 0.22, severity: "MEDIUM", description: "Payment amount represents 4.8x sender's standard median transfer." }
      ]
    }
  ],
  alerts: [
    {
      id: 1,
      alert_id: "ALT-DEMO-001",
      tx_id: "TXN-DEMO-98214",
      amount: 85000.0,
      sender_upi: "vikram.patel@okhdfcbank",
      receiver_upi: "unknown.mule.crypto@ybl",
      severity: "CRITICAL",
      primary_reason: "SIM Swap Surge + New Device",
      status: "PENDING",
      created_at: new Date(Date.now() - 4 * 60000).toISOString(),
      explanations: [
        { factor_name: "DEVICE_ANOMALY", weight: 0.35, severity: "CRITICAL", description: "Hardware fingerprint unseen across 12-month baseline history." },
        { factor_name: "HIGH_VELOCITY_DRAIN", weight: 0.32, severity: "CRITICAL", description: "Rapid maximum UPI daily limit exhaustion pattern." }
      ]
    },
    {
      id: 2,
      alert_id: "ALT-DEMO-002",
      tx_id: "TXN-DEMO-98213",
      amount: 9800.0,
      sender_upi: "neha.gupta@paytm",
      receiver_upi: "fast.cash.collect@axl",
      severity: "HIGH",
      primary_reason: "High Velocity Collect Request",
      status: "PENDING",
      created_at: new Date(Date.now() - 11 * 60000).toISOString(),
      explanations: [
        { factor_name: "VELOCITY_BURST", weight: 0.42, severity: "HIGH", description: "6 outgoing requests within 120 seconds." },
        { factor_name: "COLLECT_REVERSE_FLOW", weight: 0.30, severity: "HIGH", description: "Collect request pattern consistent with social engineering scam." }
      ]
    },
    {
      id: 3,
      alert_id: "ALT-DEMO-003",
      tx_id: "TXN-DEMO-98209",
      amount: 24999.0,
      sender_upi: "ananya.sen@ybl",
      receiver_upi: "urgent.lottery.claim@pnb",
      severity: "MEDIUM",
      primary_reason: "New Recipient + Urgent Collect",
      status: "PENDING",
      created_at: new Date(Date.now() - 42 * 60000).toISOString(),
      explanations: [
        { factor_name: "SUSPICIOUS_HANDLE", weight: 0.28, severity: "MEDIUM", description: "Recipient handle flagged in shared anti-phishing watchlist." }
      ]
    }
  ]
};

const FraudShieldAPI = {
  token: localStorage.getItem('fraudshield_token') || null,
  currentUser: JSON.parse(localStorage.getItem('fraudshield_user') || 'null') || {
    id: 1,
    username: 'admin',
    email: 'admin@fraudshield.internal',
    full_name: 'System Administrator',
    role: 'ADMIN'
  },
  isLiveConnected: false,

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  },

  async getHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        this.isLiveConnected = true;
        return await res.json();
      }
    } catch (e) {
      this.isLiveConnected = false;
    }
    return {
      status: 'demo_mode',
      version: '1.2.0-preview',
      note: 'Operating on demonstration baseline telemetry.'
    };
  },

  async login(username, password) {
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (res.ok) {
        const data = await res.json();
        this.token = data.access_token;
        this.currentUser = data.user;
        localStorage.setItem('fraudshield_token', this.token);
        localStorage.setItem('fraudshield_user', JSON.stringify(this.currentUser));
        this.isLiveConnected = true;
        return data;
      } else {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Authentication rejected (HTTP ${res.status})`);
      }
    } catch (e) {
      if (e.message && (e.message.includes('rejected') || e.message.includes('Invalid') || e.message.includes('password') || e.message.includes('user'))) {
        throw e;
      }
      console.warn('Backend login unavailable; switching demo session context:', e);
      // Fallback for offline demo standalone mode
      const role = username.toLowerCase().includes('analyst') ? 'ANALYST' : 'ADMIN';
      this.currentUser = {
        id: role === 'ADMIN' ? 1 : 2,
        username: username,
        email: `${username}@fraudshield.internal`,
        full_name: role === 'ADMIN' ? 'System Administrator' : 'SOC Lead Analyst',
        role: role
      };
      this.token = `DEMO-JWT-TOKEN-${role}-${Date.now()}`;
      localStorage.setItem('fraudshield_token', this.token);
      localStorage.setItem('fraudshield_user', JSON.stringify(this.currentUser));
      return { access_token: this.token, token_type: 'bearer', user: this.currentUser };
    }
  },

  async logout() {
    try {
      if (this.token && !this.token.startsWith('DEMO-')) {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: 'POST',
          headers: this.getHeaders()
        });
      }
    } catch (e) {
      // Ignored on logout
    }
    this.token = null;
    this.currentUser = null;
    localStorage.removeItem('fraudshield_token');
    localStorage.removeItem('fraudshield_user');
  },

  async getAnalytics(options = {}) {
    const { start_date = null, end_date = null, risk_tier = null } = options;
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    if (risk_tier && risk_tier.toUpperCase() !== 'ALL') params.append('risk_tier', risk_tier);

    const queryString = params.toString() ? `?${params.toString()}` : '';

    try {
      const res = await fetch(`${API_BASE}/api/analytics${queryString}`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        this.isLiveConnected = true;
        return await res.json();
      } else if (res.status === 403) {
        throw new Error('ACCESS_DENIED: Admin privileges required to view system analytics.');
      } else if (res.status === 401) {
        throw new Error('UNAUTHORIZED: Active session expired or unauthenticated.');
      }
    } catch (e) {
      if (e.message && (e.message.includes('ACCESS_DENIED') || e.message.includes('UNAUTHORIZED'))) {
        throw e;
      }
      this.isLiveConnected = false;
    }
    return DEMO_PREVIEW_DATA.metrics;
  },

  async getNetworkGraph(options = {}) {
    const { min_risk_score = 0.0, only_suspicious = false } = options;
    const params = new URLSearchParams();
    if (min_risk_score > 0) params.append('min_risk_score', min_risk_score);
    if (only_suspicious) params.append('only_suspicious', 'true');

    const queryString = params.toString() ? `?${params.toString()}` : '';
    try {
      const res = await fetch(`${API_BASE}/api/analytics/network-graph${queryString}`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Network graph fetch fallback to demo:', e);
    }
    return this.getDemoNetworkGraph(only_suspicious);
  },

  getDemoNetworkGraph(only_suspicious = false) {
    const nodes = [
      { id: "vikram.patel@okhdfcbank", label: "vikram.patel", role: "SENDER", total_sent: 85000.0, total_received: 0.0, tx_sent_count: 2, tx_recv_count: 0, avg_risk_score: 94.8, is_mule_candidate: false, is_suspicious: true, is_simulated: true },
      { id: "unknown.mule.crypto@ybl", label: "mule.crypto", role: "MULE_HUB", total_sent: 0.0, total_received: 142000.0, tx_sent_count: 0, tx_recv_count: 5, avg_risk_score: 88.0, is_mule_candidate: true, is_suspicious: true, is_simulated: true },
      { id: "neha.gupta@paytm", label: "neha.gupta", role: "SENDER", total_sent: 24000.0, total_received: 0.0, tx_sent_count: 3, tx_recv_count: 0, avg_risk_score: 78.4, is_mule_candidate: false, is_suspicious: true, is_simulated: true },
      { id: "fast.cash.collect@axl", label: "fast.cash.collect", role: "MULE_HUB", total_sent: 0.0, total_received: 57000.0, tx_sent_count: 0, tx_recv_count: 4, avg_risk_score: 78.4, is_mule_candidate: true, is_suspicious: true, is_simulated: true },
      { id: "arjun.sharma@okaxis", label: "arjun.sharma", role: "SENDER", total_sent: 3800.0, total_received: 0.0, tx_sent_count: 4, tx_recv_count: 0, avg_risk_score: 11.5, is_mule_candidate: false, is_suspicious: false, is_simulated: true },
      { id: "nature.groceries@icici", label: "nature.groceries", role: "RECEIVER", total_sent: 0.0, total_received: 3800.0, tx_sent_count: 0, tx_recv_count: 4, avg_risk_score: 11.5, is_mule_candidate: false, is_suspicious: false, is_simulated: true },
      { id: "synthetic.mule.ring1@ybl", label: "mule.ring1", role: "MULE_HUB", total_sent: 45000.0, total_received: 85000.0, tx_sent_count: 2, tx_recv_count: 3, avg_risk_score: 84.0, is_mule_candidate: true, is_suspicious: true, is_simulated: true }
    ];
    const edges = [
      { id: "edge-1", source: "vikram.patel@okhdfcbank", target: "unknown.mule.crypto@ybl", tx_count: 2, total_amount: 85000.0, avg_risk_score: 94.8, is_suspicious: true, is_repeated: true, channels: ["INTENT_FLOW"], last_timestamp: new Date().toISOString() },
      { id: "edge-2", source: "neha.gupta@paytm", target: "fast.cash.collect@axl", tx_count: 3, total_amount: 29400.0, avg_risk_score: 78.4, is_suspicious: true, is_repeated: true, channels: ["COLLECT_REQUEST"], last_timestamp: new Date().toISOString() },
      { id: "edge-3", source: "arjun.sharma@okaxis", target: "nature.groceries@icici", tx_count: 4, total_amount: 3800.0, avg_risk_score: 11.5, is_suspicious: false, is_repeated: true, channels: ["QR_CODE"], last_timestamp: new Date().toISOString() },
      { id: "edge-4", source: "unknown.mule.crypto@ybl", target: "synthetic.mule.ring1@ybl", tx_count: 2, total_amount: 45000.0, avg_risk_score: 86.0, is_suspicious: true, is_repeated: true, channels: ["INTENT_FLOW"], last_timestamp: new Date().toISOString() }
    ];
    const filteredEdges = only_suspicious ? edges.filter(e => e.is_suspicious) : edges;
    const activeNodes = new Set(filteredEdges.flatMap(e => [e.source, e.target]));
    const filteredNodes = only_suspicious ? nodes.filter(n => activeNodes.has(n.id)) : nodes;
    return {
      nodes: filteredNodes,
      edges: filteredEdges,
      metrics: {
        total_nodes: filteredNodes.length,
        total_edges: filteredEdges.length,
        suspicious_edges_count: edges.filter(e => e.is_suspicious).length,
        repeated_interaction_pairs: edges.filter(e => e.is_repeated).length,
        mule_hubs_detected: filteredNodes.filter(n => n.is_mule_candidate).length,
        circular_routing_detected: 1
      }
    };
  },

  async exportTransactionsCSV(options = {}) {
    const { start_date = null, end_date = null, risk_tier = null } = options;
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    if (risk_tier && risk_tier.toUpperCase() !== 'ALL') params.append('risk_tier', risk_tier);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const url = `${API_BASE}/api/analytics/export/transactions${queryString}`;

    try {
      const res = await fetch(url, { headers: this.getHeaders() });
      if (res.status === 403) {
        throw new Error('ACCESS_DENIED: Admin privileges required to export audit reports.');
      }
      if (!res.ok) throw new Error(`Export failed with HTTP status ${res.status}`);
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `fraudshield_transactions_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      return { success: true };
    } catch (err) {
      if (err.message && err.message.includes('ACCESS_DENIED')) {
        throw err;
      }
      if (this.isLiveConnected) {
        throw err;
      }
      console.warn('API CSV export failed, falling back to local CSV generation:', err);
      this._fallbackCSVDownload('transactions');
      return { success: true, fallback: true };
    }
  },

  async exportAlertsCSV(options = {}) {
    const { status = null, severity = null, start_date = null, end_date = null } = options;
    const params = new URLSearchParams();
    if (status && status.toUpperCase() !== 'ALL') params.append('status', status);
    if (severity && severity.toUpperCase() !== 'ALL') params.append('severity', severity);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const url = `${API_BASE}/api/analytics/export/alerts${queryString}`;

    try {
      const res = await fetch(url, { headers: this.getHeaders() });
      if (res.status === 403) {
        throw new Error('ACCESS_DENIED: Admin privileges required to export audit reports.');
      }
      if (!res.ok) throw new Error(`Export failed with HTTP status ${res.status}`);
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `fraudshield_alerts_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      return { success: true };
    } catch (err) {
      if (err.message && err.message.includes('ACCESS_DENIED')) {
        throw err;
      }
      if (this.isLiveConnected) {
        throw err;
      }
      console.warn('API Alerts CSV export failed, falling back to local CSV generation:', err);
      this._fallbackCSVDownload('alerts');
      return { success: true, fallback: true };
    }
  },

  _fallbackCSVDownload(type) {
    let csv = '';
    let filename = '';
    if (type === 'transactions') {
      csv = 'Transaction ID,Sender VPA,Receiver VPA,Amount (INR),Risk Score,Risk Tier,Status\n' +
        'TXN-DEMO-98214,vikram.patel@okhdfcbank,unknown.mule.crypto@ybl,85000.00,94.80,CRITICAL,BLOCKED\n' +
        'TXN-DEMO-98213,neha.gupta@paytm,fast.cash.collect@axl,9800.00,78.40,HIGH,UNDER_REVIEW\n' +
        'TXN-DEMO-98212,arjun.sharma@okaxis,nature.groceries@icici,450.00,8.20,LOW,APPROVED\n';
      filename = `fraudshield_transactions_${new Date().toISOString().slice(0, 10)}.csv`;
    } else {
      csv = 'Alert ID,Transaction ID,Severity,Risk Score,Status,Primary Reason\n' +
        'ALT-98214-01,TXN-DEMO-98214,CRITICAL,94.80,PENDING,SIM Swap Surge + New Device\n' +
        'ALT-98213-01,TXN-DEMO-98213,HIGH,78.40,PENDING,High Velocity Collect Request\n';
      filename = `fraudshield_alerts_${new Date().toISOString().slice(0, 10)}.csv`;
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  async getRecentTransactions(limit = 50, risk_tier = null) {
    const res = await this.getTransactions({ limit, risk_tier });
    return res.transactions || [];
  },

  async getTransactions(options = {}) {
    const {
      page = 1,
      limit = 25,
      risk_tier = null,
      search = null,
      start_date = null,
      end_date = null,
      sort_by = 'timestamp',
      sort_order = 'desc',
      channel = null,
      status = null,
    } = options;

    const offset = (page - 1) * limit;

    try {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());
      if (risk_tier && risk_tier !== 'ALL') params.append('risk_tier', risk_tier);
      if (search && search.trim()) params.append('search', search.trim());
      if (start_date) params.append('start_date', start_date);
      if (end_date) params.append('end_date', end_date);
      if (channel && channel !== 'ALL') params.append('channel', channel);
      if (status && status !== 'ALL') params.append('status', status);
      if (sort_by) params.append('sort_by', sort_by);
      if (sort_order) params.append('sort_order', sort_order);

      const res = await fetch(`${API_BASE}/api/transactions?${params.toString()}`, {
        headers: this.getHeaders()
      });

      if (res.ok) {
        const data = await res.json();
        this.isLiveConnected = true;
        return {
          total: data.total,
          limit: data.limit,
          offset: data.offset,
          page: Math.floor(data.offset / data.limit) + 1,
          totalPages: Math.ceil(data.total / data.limit) || 1,
          transactions: data.transactions || []
        };
      }
    } catch (e) {
      this.isLiveConnected = false;
      console.warn('Backend /api/transactions fetch failed; using demo baseline:', e);
    }

    // Client-side fallback engine using DEMO_PREVIEW_DATA
    let list = [...DEMO_PREVIEW_DATA.transactions];
    if (risk_tier && risk_tier !== 'ALL') {
      list = list.filter(t => t.risk_tier === risk_tier);
    }
    if (search && search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(t =>
        (t.tx_id && t.tx_id.toLowerCase().includes(q)) ||
        (t.sender_upi && t.sender_upi.toLowerCase().includes(q)) ||
        (t.receiver_upi && t.receiver_upi.toLowerCase().includes(q)) ||
        (t.location_city && t.location_city.toLowerCase().includes(q))
      );
    }
    if (start_date) {
      list = list.filter(t => new Date(t.timestamp) >= new Date(start_date));
    }
    if (end_date) {
      list = list.filter(t => new Date(t.timestamp) <= new Date(end_date));
    }
    if (channel && channel !== 'ALL') {
      list = list.filter(t => t.channel === channel);
    }
    if (status && status !== 'ALL') {
      list = list.filter(t => t.status === status);
    }

    // Sorting
    list.sort((a, b) => {
      let valA = a[sort_by] ?? '';
      let valB = b[sort_by] ?? '';
      if (sort_by === 'amount' || sort_by === 'risk_score') {
        valA = Number(valA);
        valB = Number(valB);
      } else if (sort_by === 'timestamp' || sort_by === 'created_at') {
        valA = new Date(valA).getTime();
        valB = new Date(valB).getTime();
      }
      if (valA < valB) return sort_order === 'asc' ? -1 : 1;
      if (valA > valB) return sort_order === 'asc' ? 1 : -1;
      return 0;
    });

    const total = list.length;
    const paginated = list.slice(offset, offset + limit);

    return {
      total: total,
      limit: limit,
      offset: offset,
      page: page,
      totalPages: Math.ceil(total / limit) || 1,
      transactions: paginated
    };
  },

  async getTransaction(txId) {
    try {
      const res = await fetch(`${API_BASE}/api/transactions/${encodeURIComponent(txId)}`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn(`Backend /api/transactions/${txId} failed; fallback to local:`, e);
    }

    // Fallback demo find
    const found = DEMO_PREVIEW_DATA.transactions.find(t => t.tx_id === txId) || DEMO_PREVIEW_DATA.transactions[0];
    const alert = DEMO_PREVIEW_DATA.alerts.find(a => a.tx_id === txId) || null;
    return {
      transaction: found,
      alert: alert,
      explanations: found ? (found.explanations || []) : [],
      prediction: {
        model_name: 'IsolationForest',
        model_version: '1.0.0_n150',
        is_anomaly: found && found.risk_score >= 70 ? 1 : 0,
        raw_decision_score: found ? (found.anomaly_score ?? -0.18) : -0.15,
        model_risk_score: found ? (found.risk_score ?? 50.0) : 50.0,
        final_risk_score: found ? (found.risk_score ?? 50.0) : 50.0,
        risk_category: found && found.risk_tier === 'CRITICAL' ? 'High risk' : found && found.risk_tier === 'HIGH' ? 'High risk' : found && found.risk_tier === 'MEDIUM' ? 'Medium risk' : 'Low risk',
        explanation_summary: found ? (found.primary_factor || 'Evaluated against historical behavioural cluster.') : 'Normal baseline transaction.'
      }
    };
  },

  async getAlerts(options = 'PENDING') {
    let queryParams = new URLSearchParams();
    const isLegacyCall = typeof options === 'string';

    if (isLegacyCall) {
      if (options && options !== 'ALL') queryParams.append('status', options);
      queryParams.append('limit', '50');
    } else {
      const { status, severity, search, limit = 50, offset = 0 } = options || {};
      if (status && status !== 'ALL') queryParams.append('status', status);
      if (severity && severity !== 'ALL') queryParams.append('severity', severity);
      if (search) queryParams.append('search', search);
      queryParams.append('limit', String(limit));
      queryParams.append('offset', String(offset));
    }

    try {
      const res = await fetch(`${API_BASE}/api/alerts?${queryParams.toString()}`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        this.isLiveConnected = true;
        return isLegacyCall ? (data.alerts || []) : data;
      }
    } catch (e) {
      this.isLiveConnected = false;
    }

    // Demo preview fallback
    let filtered = [...DEMO_PREVIEW_DATA.alerts];
    if (isLegacyCall) {
      if (options && options !== 'ALL') filtered = filtered.filter(a => a.status === options);
      return filtered;
    } else {
      const { status, severity, search } = options || {};
      if (status && status !== 'ALL') {
        filtered = filtered.filter(a => (a.status || '').toUpperCase() === status.toUpperCase());
      }
      if (severity && severity !== 'ALL') {
        filtered = filtered.filter(a => (a.severity || '').toUpperCase() === severity.toUpperCase());
      }
      if (search) {
        const s = search.toLowerCase();
        filtered = filtered.filter(a => 
          (a.alert_id && a.alert_id.toLowerCase().includes(s)) ||
          (a.tx_id && a.tx_id.toLowerCase().includes(s)) ||
          (a.primary_reason && a.primary_reason.toLowerCase().includes(s))
        );
      }
      return {
        total: filtered.length,
        limit: options?.limit || 50,
        offset: options?.offset || 0,
        alerts: filtered
      };
    }
  },

  async getAlertById(alertId) {
    if (!alertId) return null;
    try {
      const res = await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend getAlertById unavailable');
    }
    return DEMO_PREVIEW_DATA.alerts.find(a => a.alert_id === alertId || a.tx_id === alertId) || null;
  },

  async markAlertReviewed(alertId, notes = '') {
    return this.updateAlertAction(alertId, 'REVIEWED', notes || 'Reviewed by SOC analyst');
  },

  async updateAlertAction(alertId, action, notes = '') {
    const actUpper = (action || 'REVIEWED').toUpperCase();
    try {
      const res = await fetch(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}`, {
        method: 'PATCH',
        headers: this.getHeaders(),
        body: JSON.stringify({ action: actUpper, notes: notes || ('Action ' + actUpper + ' recorded'), reviewed_by: this.currentUser?.username || 'SOC-Analyst' })
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend alert triage unavailable; updating demo state in-memory.');
    }

    // Fallback in-memory update
    const target = DEMO_PREVIEW_DATA.alerts.find(a => a.alert_id === alertId || a.tx_id === alertId);
    if (target) {
      target.status = actUpper;
      target.reviewed_by = this.currentUser?.username || 'SOC-Analyst';
      target.analyst_notes = notes;
      target.updated_at = new Date().toISOString();
      return target;
    }
    return {
      alert_id: alertId,
      status: actUpper,
      reviewed_by: this.currentUser?.username || 'SOC-Analyst',
      analyst_notes: notes,
      updated_at: new Date().toISOString()
    };
  },

  async evaluateTransaction(payload) {
    try {
      const res = await fetch(`${API_BASE}/api/transactions`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend evaluation failed; evaluating locally via heuristic.');
    }

    // Heuristic fallback evaluation for demo
    const isHigh = payload.amount > 20000 || payload.channel === 'COLLECT_REQUEST';
    const score = isHigh ? Math.min(96, Math.floor(payload.amount / 500) + 40) : Math.max(5, Math.floor(payload.amount / 200));
    const tier = score >= 90 ? 'CRITICAL' : score >= 70 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW';

    const result = {
      tx_id: `TXN-SIM-${Date.now().toString().slice(-5)}`,
      timestamp: new Date().toISOString(),
      sender_upi: payload.sender_upi,
      receiver_upi: payload.receiver_upi,
      amount: payload.amount,
      channel: payload.channel,
      device_id: payload.device_id,
      risk_score: score,
      risk_tier: tier,
      is_flagged: score >= 40 ? 1 : 0,
      status: score >= 70 ? 'UNDER_REVIEW' : 'APPROVED',
      primary_factor: isHigh ? 'High Velocity / Amount Deviation' : 'Authorized Regular Purchase',
      anomaly_score: isHigh ? -0.22 : 0.15,
      location_city: payload.location_city || 'Bengaluru',
      explanations: [
        {
          factor_name: 'AMOUNT_DEVIATION',
          weight: isHigh ? 0.45 : 0.05,
          severity: isHigh ? 'HIGH' : 'LOW',
          description: `Transaction amount ₹${payload.amount.toLocaleString()} evaluated against peer baselines.`
        }
      ]
    };

    // Prepend to demonstration array
    DEMO_PREVIEW_DATA.transactions.unshift(result);
    return result;
  },


  async updateTransactionStatus(txId, status, notes = '') {
    try {
      const res = await fetch(`${API_BASE}/api/transactions/${encodeURIComponent(txId)}`, {
        method: 'PATCH',
        headers: this.getHeaders(),
        body: JSON.stringify({ status, notes })
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend updateTransactionStatus unavailable, updating locally:', e);
    }
    const target = DEMO_PREVIEW_DATA.transactions.find(t => t.tx_id === txId);
    if (target) {
      target.status = status;
      target.is_flagged = (status === 'BLOCKED' || status === 'FLAGGED') ? 1 : 0;
    }
    return { success: true, transaction_id: txId, status };
  },

  async getAlertSummary() {
    try {
      const res = await fetch(`${API_BASE}/api/alerts/summary`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend /api/alerts/summary unavailable:', e);
    }
    const alerts = DEMO_PREVIEW_DATA.alerts || [];
    return {
      total: alerts.length,
      pending: alerts.filter(a => a.status === 'PENDING').length,
      under_review: alerts.filter(a => a.status === 'REVIEWED' || a.status === 'UNDER_REVIEW').length,
      approved: alerts.filter(a => a.status === 'APPROVED' || a.status === 'DISMISSED').length,
      blocked: alerts.filter(a => a.status === 'BLOCKED').length
    };
  },

  async getUsers(options = {}) {
    const { limit = 50, offset = 0 } = options;
    try {
      const res = await fetch(`${API_BASE}/api/users?limit=${limit}&offset=${offset}`, {
        headers: this.getHeaders()
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend /api/users unavailable, using demo users:', e);
    }
    return {
      total: 2,
      limit,
      offset,
      users: [
        { id: 1, username: 'admin', email: 'admin@fraudshield.ai', full_name: 'System Administrator', role: 'ADMIN', is_active: true, created_at: '2026-10-01T00:00:00Z' },
        { id: 2, username: 'analyst', email: 'analyst@fraudshield.ai', full_name: 'Lead SOC Analyst', role: 'ANALYST', is_active: true, created_at: '2026-10-01T00:00:00Z' }
      ]
    };
  },

  async createUser(payload) {
    const res = await fetch(`${API_BASE}/api/users`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create user (HTTP ${res.status})`);
    }
    return await res.json();
  },

  async updateUser(userId, payload) {
    const res = await fetch(`${API_BASE}/api/users/${userId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update user (HTTP ${res.status})`);
    }
    return await res.json();
  },

  async deleteUser(userId) {
    const res = await fetch(`${API_BASE}/api/users/${userId}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to delete user (HTTP ${res.status})`);
    }
    return await res.json();
  },

  async updateProfile(payload) {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update profile (HTTP ${res.status})`);
    }
    const data = await res.json();
    this.currentUser = data;
    localStorage.setItem('fraudshield_user', JSON.stringify(data));
    return data;
  },

  async getBehaviouralUsers() {
    try {
      const res = await fetch(`${API_BASE}/api/analytics/behavioural/users`, {
        headers: this.getHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend getBehaviouralUsers unavailable:', e);
    }
    return [
      { sender_upi: 'arjun.sharma@okaxis', tx_count: 239 },
      { sender_upi: 'priya.patel@oksbi', tx_count: 59 },
      { sender_upi: 'sneha.reddy@okicici', tx_count: 96 },
      { sender_upi: 'rahul.kumar@paytm', tx_count: 27 },
      { sender_upi: 'vikram.malhotra@okhdfcbank', tx_count: 16 }
    ];
  },

  async getBehaviouralProfile(senderUpi) {
    try {
      const res = await fetch(`${API_BASE}/api/analytics/behavioural/profile?sender_upi=${encodeURIComponent(senderUpi)}`, {
        headers: this.getHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend getBehaviouralProfile unavailable:', e);
    }
    return null;
  },

  async getBehaviouralMetrics() {
    try {
      const res = await fetch(`${API_BASE}/api/analytics/behavioural/metrics`, {
        headers: this.getHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend getBehaviouralMetrics unavailable:', e);
    }
    return {
      total_profiled_users: 10,
      velocity_bursts_detected: 14,
      amount_outliers_detected: 28,
      novel_device_attempts: 18,
      suspicious_account_clusters: 2,
      repeated_pairs_count: 4,
      circular_routing_count: 1
    };
  },

  async triggerPreset(presetName) {
    try {
      const res = await fetch(`${API_BASE}/api/simulation/preset`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ preset: presetName })
      });
      if (res.ok) {
        this.isLiveConnected = true;
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend simulation preset unavailable, running demo scenario.');
    }

    // Comprehensive Fallback Simulation Heuristic for Standalone Demonstration
    const randId = Math.floor(100000 + Math.random() * 900000);
    const nowIso = new Date().toISOString();
    let tx = null;

    if (presetName === 'NORMAL_PAYMENT' || presetName === 'GROCERY_NORMAL') {
      tx = {
        tx_id: `TXN-SIM-NORM-${randId}`,
        timestamp: nowIso,
        sender_upi: "arjun.sharma@okaxis",
        receiver_upi: "grocery.store@icici",
        amount: Math.floor(180 + Math.random() * 670),
        channel: "UPI_APP",
        device_id: "DEV-XIAOMI-12",
        location_city: "Bengaluru",
        risk_score: 8.4,
        risk_tier: "LOW",
        risk_category: "Low risk",
        status: "APPROVED",
        action_recommendation: "AUTO_APPROVE",
        primary_factor: "Authorized Normal Payment",
        is_flagged: false,
        anomaly_score: 0.184,
        explanations: [
          { factor_name: "MERCHANT_BASELINE", weight: 0.05, severity: "LOW", description: "Standard daily purchase at registered retail merchant." }
        ]
      };
    } else if (presetName === 'UNUSUALLY_LARGE') {
      tx = {
        tx_id: `TXN-SIM-LARGE-${randId}`,
        timestamp: nowIso,
        sender_upi: "arjun.sharma@okaxis",
        receiver_upi: `luxury.jewels.${randId}@hdfcbank`,
        amount: Math.floor(75000 + Math.random() * 23000),
        channel: "INTENT_FLOW",
        device_id: "DEV-XIAOMI-12",
        location_city: "Mumbai",
        risk_score: 82.5,
        risk_tier: "HIGH",
        risk_category: "High risk",
        status: "HOLD_FOR_REVIEW",
        action_recommendation: "HOLD_FOR_REVIEW",
        primary_factor: "Unusually Large Amount Surge",
        is_flagged: true,
        anomaly_score: -0.214,
        explanations: [
          { factor_name: "AMOUNT_DEVIATION", weight: 0.44, severity: "HIGH", description: "Amount exceeds sender 30-day baseline mean by 38.2x." },
          { factor_name: "NEW_RECIPIENT", weight: 0.28, severity: "MEDIUM", description: "First transaction to luxury bullion merchant handle." }
        ]
      };
    } else if (presetName === 'VELOCITY_BURST') {
      tx = {
        tx_id: `TXN-SIM-BURST-${randId}`,
        timestamp: nowIso,
        sender_upi: "priya.patel@oksbi",
        receiver_upi: `burner.wallet.${randId}@paytm`,
        amount: Math.floor(8500 + Math.random() * 6000),
        channel: "COLLECT_REQUEST",
        device_id: "DEV-ONEPLUS-11",
        location_city: "Ahmedabad",
        risk_score: 79.4,
        risk_tier: "HIGH",
        risk_category: "High risk",
        status: "HOLD_FOR_REVIEW",
        action_recommendation: "HOLD_FOR_REVIEW",
        primary_factor: "Rapid Repeated Velocity Burst",
        is_flagged: true,
        anomaly_score: -0.201,
        explanations: [
          { factor_name: "VELOCITY_SPIKE", weight: 0.45, severity: "HIGH", description: "7 outgoing transfers initiated within 45 seconds." },
          { factor_name: "CHANNEL_RISK", weight: 0.25, severity: "HIGH", description: "Collect request pattern matching known extortion scam." }
        ]
      };
    } else if (presetName === 'NEW_RECIPIENT') {
      tx = {
        tx_id: `TXN-SIM-NEWRECIP-${randId}`,
        timestamp: nowIso,
        sender_upi: "rahul.kumar@paytm",
        receiver_upi: `crypto.mule.unverified.${randId}@ybl`,
        amount: Math.floor(28000 + Math.random() * 20000),
        channel: "UPI_APP",
        device_id: "DEV-SAMSUNG-S23",
        location_city: "Delhi",
        risk_score: 66.8,
        risk_tier: "MEDIUM",
        risk_category: "Medium risk",
        status: "UNDER_REVIEW",
        action_recommendation: "HOLD_FOR_REVIEW",
        primary_factor: "Payment to Unverified New Recipient",
        is_flagged: true,
        anomaly_score: -0.125,
        explanations: [
          { factor_name: "FIRST_TIME_RECIPIENT", weight: 0.38, severity: "MEDIUM", description: "Recipient handle unverified with zero historical mutual transactions." }
        ]
      };
    } else {
      // UNUSUAL_PATTERN or SIM_SWAP_DRAIN
      tx = {
        tx_id: `TXN-SIM-UNUSUAL-${randId}`,
        timestamp: nowIso,
        sender_upi: "sneha.reddy@okicici",
        receiver_upi: `fraud.drain.${randId}@ybl`,
        amount: 88000.0,
        channel: "INTENT_FLOW",
        device_id: "DEV-UNKNOWN-ROOTED-IMEI",
        location_city: "Kolkata",
        risk_score: 95.2,
        risk_tier: "CRITICAL",
        risk_category: "High risk",
        status: "BLOCKED",
        action_recommendation: "BLOCK_AND_FLAG",
        primary_factor: "SIM Swap Surge + Night Window",
        is_flagged: true,
        anomaly_score: -0.298,
        explanations: [
          { factor_name: "DEVICE_ANOMALY", weight: 0.38, severity: "CRITICAL", description: "First transaction observed on unverified rooted hardware IMEI." },
          { factor_name: "NIGHT_ACTIVITY", weight: 0.26, severity: "HIGH", description: "Attempted outside customer historical cluster (03:15 AM IST)." },
          { factor_name: "AMOUNT_SURGE", weight: 0.24, severity: "CRITICAL", description: "Maximum daily limit drain surge attempted." }
        ]
      };
    }

    DEMO_PREVIEW_DATA.transactions.unshift(tx);
    return tx;
  }
};

window.FraudShieldAPI = FraudShieldAPI;
window.DEMO_PREVIEW_DATA = DEMO_PREVIEW_DATA;
