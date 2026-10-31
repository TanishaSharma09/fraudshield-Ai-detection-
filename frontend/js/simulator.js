/**
 * FraudShield AI - Real-Time UPI Transaction Stream Simulator Controller
 * Provides continuous synthetic payment stream generation with live controls:
 * Start, Pause, Resume, Stop, and Dynamic Velocity/Speed adjustments.
 * Every payment is evaluated through FastAPI Isolation Forest endpoints and persisted to SQLite.
 */

const FraudShieldSimulator = {
  state: {
    status: 'STOPPED', // 'STOPPED' | 'RUNNING' | 'PAUSED'
    intervalMs: 1500,  // default 1.5s between transactions
    timerId: null,
    scenarioMode: 'REALISTIC_MIX',
    stats: {
      totalGenerated: 0,
      anomaliesFlagged: 0,
      startTime: null,
      sessionTxCount: 0
    }
  },

  scenarios: [
    { id: 'NORMAL_PAYMENT', label: '1. Normal Payments (Grocery / Peer)', weight: 0.70 },
    { id: 'UNUSUALLY_LARGE', label: '2. Unusually Large Payments (₹75k - ₹98k)', weight: 0.08 },
    { id: 'VELOCITY_BURST', label: '3. Repeated Rapid Payments (Velocity Burst)', weight: 0.10 },
    { id: 'NEW_RECIPIENT', label: '4. Payments to New Recipients (Mule/Crypto)', weight: 0.07 },
    { id: 'UNUSUAL_PATTERN', label: '5. Unusual Patterns (SIM Swap / Night Window)', weight: 0.05 }
  ],

  init() {
    console.log('[FraudShield AI] Stream Simulator Engine initialized.');
    this.bindDeckControls();
    this.bindManualModal();
  },

  // -------------------------------------------------------------------------
  // Live Stream Simulator Control Deck Bindings
  // -------------------------------------------------------------------------
  bindDeckControls() {
    // Control Buttons
    const btnStart = document.getElementById('btn-sim-start');
    const btnPause = document.getElementById('btn-sim-pause');
    const btnResume = document.getElementById('btn-sim-resume');
    const btnStop = document.getElementById('btn-sim-stop');

    if (btnStart) btnStart.addEventListener('click', () => this.start());
    if (btnPause) btnPause.addEventListener('click', () => this.pause());
    if (btnResume) btnResume.addEventListener('click', () => this.resume());
    if (btnStop) btnStop.addEventListener('click', () => this.stop());

    // Speed Slider
    const speedSlider = document.getElementById('sim-speed-slider');
    const speedDisplay = document.getElementById('sim-speed-val');
    if (speedSlider) {
      speedSlider.addEventListener('input', (e) => {
        const ms = parseInt(e.target.value, 10);
        this.setSpeed(ms);
        if (speedDisplay) {
          const sec = (ms / 1000).toFixed(1);
          speedDisplay.textContent = `${sec}s / tx`;
        }
      });
    }

    // Speed Preset Pills
    document.querySelectorAll('.sim-speed-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.sim-speed-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const ms = parseInt(pill.getAttribute('data-speed'), 10);
        if (speedSlider) speedSlider.value = ms;
        this.setSpeed(ms);
        if (speedDisplay) {
          const sec = (ms / 1000).toFixed(1);
          speedDisplay.textContent = `${sec}s / tx`;
        }
      });
    });

    // Scenario Mode Selector
    const modeSelect = document.getElementById('sim-scenario-select');
    if (modeSelect) {
      modeSelect.addEventListener('change', (e) => {
        this.state.scenarioMode = e.target.value;
        const modeLabel = modeSelect.options[modeSelect.selectedIndex]?.text || e.target.value;
        window.FraudShieldDashboard?.showToast(`Simulation scenario mode: ${modeLabel}`, 'info');
      });
    }
  },

  // -------------------------------------------------------------------------
  // Manual Modal Preset Bindings (For Single Injections)
  // -------------------------------------------------------------------------
  bindManualModal() {
    const openBtn = document.getElementById('btn-quick-simulate');
    const navBtn = document.getElementById('nav-simulator-trigger');
    const modal = document.getElementById('simulator-modal');
    const closeBtn = document.getElementById('close-simulator-btn');
    const closeFooterBtn = document.getElementById('close-sim-footer-btn');

    const openModal = () => modal?.classList.add('open');
    const closeModal = () => modal?.classList.remove('open');

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (navBtn) navBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeModal);

    // Preset scenario cards click inside modal
    document.querySelectorAll('.preset-card').forEach(card => {
      card.addEventListener('click', () => {
        const presetKey = card.getAttribute('data-preset');
        this.triggerManualPreset(presetKey);
      });
    });

    // Fire custom parameter button
    document.getElementById('btn-fire-simulation')?.addEventListener('click', () => {
      this.handleCustomPaymentSimulation();
    });
  },

  // -------------------------------------------------------------------------
  // Stream Simulator Engine Actions
  // -------------------------------------------------------------------------
  start() {
    if (this.state.status === 'RUNNING') return;

    this.state.status = 'RUNNING';
    if (!this.state.stats.startTime) {
      this.state.stats.startTime = Date.now();
    }
    this.updateControlsUI();
    this.scheduleNextTick();

    window.FraudShieldDashboard?.showToast('Real-time UPI transaction stream started', 'success');
  },

  pause() {
    if (this.state.status !== 'RUNNING') return;

    this.state.status = 'PAUSED';
    if (this.state.timerId) {
      clearTimeout(this.state.timerId);
      this.state.timerId = null;
    }
    this.updateControlsUI();

    window.FraudShieldDashboard?.showToast('Transaction stream paused', 'warning');
  },

  resume() {
    if (this.state.status !== 'PAUSED') return;
    this.start();
  },

  stop() {
    if (this.state.status === 'STOPPED') return;

    this.state.status = 'STOPPED';
    if (this.state.timerId) {
      clearTimeout(this.state.timerId);
      this.state.timerId = null;
    }
    this.state.stats.startTime = null;
    this.updateControlsUI();

    window.FraudShieldDashboard?.showToast('Transaction stream stopped', 'info');
  },

  setSpeed(ms) {
    this.state.intervalMs = Math.max(300, Math.min(10000, ms));
    // If currently running, reschedule timer with new speed
    if (this.state.status === 'RUNNING') {
      if (this.state.timerId) {
        clearTimeout(this.state.timerId);
      }
      this.scheduleNextTick();
    }
  },

  scheduleNextTick() {
    if (this.state.status !== 'RUNNING') return;
    this.state.timerId = setTimeout(async () => {
      await this.generateAndEvaluate();
      this.scheduleNextTick();
    }, this.state.intervalMs);
  },

  async generateAndEvaluate() {
    if (this.state.status !== 'RUNNING') return;

    const scenarioKey = this.pickNextScenario();

    try {
      // Execute through actual FastAPI prediction endpoint
      const result = await window.FraudShieldAPI.triggerPreset(scenarioKey);
      if (!result) return;

      // Update session statistics
      this.state.stats.totalGenerated++;
      this.state.stats.sessionTxCount++;
      const isAnomaly = result.risk_tier === 'HIGH' || result.risk_tier === 'CRITICAL';
      if (isAnomaly) {
        this.state.stats.anomaliesFlagged++;
      }

      this.updateTelemetryCounters();

      // Dispatch real-time event to Dashboard (updates tables, charts, alerts, KPIs)
      window.dispatchEvent(new CustomEvent('fraudshield:new-transaction', { detail: result }));

      // If anomalous, show notification toast
      if (isAnomaly) {
        window.FraudShieldDashboard?.showToast(
          `⚡ Flagged Anomaly: ${result.tx_id} | ${result.primary_factor || scenarioKey} (Score: ${result.risk_score})`,
          result.risk_tier === 'CRITICAL' ? 'danger' : 'warning'
        );
      }

    } catch (err) {
      console.warn('Simulation tick error:', err);
    }
  },

  pickNextScenario() {
    const mode = this.state.scenarioMode;

    if (mode === 'REALISTIC_MIX') {
      // 70% Normal, 30% Threat vectors
      const rand = Math.random();
      if (rand < 0.70) return 'NORMAL_PAYMENT';
      if (rand < 0.78) return 'UNUSUALLY_LARGE';
      if (rand < 0.88) return 'VELOCITY_BURST';
      if (rand < 0.95) return 'NEW_RECIPIENT';
      return 'UNUSUAL_PATTERN';
    }

    if (mode === 'HIGH_THREAT') {
      // 40% Normal, 60% Threat vectors
      const rand = Math.random();
      if (rand < 0.40) return 'NORMAL_PAYMENT';
      if (rand < 0.55) return 'UNUSUALLY_LARGE';
      if (rand < 0.75) return 'VELOCITY_BURST';
      if (rand < 0.90) return 'NEW_RECIPIENT';
      return 'UNUSUAL_PATTERN';
    }

    // Specific pinned scenario
    return mode;
  },

  updateControlsUI() {
    const statusBadge = document.getElementById('sim-status-badge');
    const statusText = document.getElementById('sim-status-text');
    const btnStart = document.getElementById('btn-sim-start');
    const btnPause = document.getElementById('btn-sim-pause');
    const btnResume = document.getElementById('btn-sim-resume');
    const btnStop = document.getElementById('btn-sim-stop');

    const status = this.state.status;

    if (statusBadge) {
      statusBadge.className = `sim-status-badge ${status.toLowerCase()}`;
    }

    if (statusText) {
      if (status === 'RUNNING') {
        const rate = (1000 / this.state.intervalMs).toFixed(1);
        statusText.textContent = `STREAM RUNNING (${rate} tx/s)`;
      } else if (status === 'PAUSED') {
        statusText.textContent = 'STREAM PAUSED';
      } else {
        statusText.textContent = 'SIMULATION STOPPED';
      }
    }

    if (btnStart) {
      btnStart.style.display = status === 'STOPPED' ? 'inline-flex' : 'none';
      btnStart.disabled = status === 'RUNNING';
    }

    if (btnPause) {
      btnPause.style.display = status === 'RUNNING' ? 'inline-flex' : 'none';
    }

    if (btnResume) {
      btnResume.style.display = status === 'PAUSED' ? 'inline-flex' : 'none';
    }

    if (btnStop) {
      btnStop.disabled = status === 'STOPPED';
    }
  },

  updateTelemetryCounters() {
    const totalEl = document.getElementById('sim-metric-total');
    const flaggedEl = document.getElementById('sim-metric-flagged');
    const rateEl = document.getElementById('sim-metric-rate');

    if (totalEl) totalEl.textContent = this.state.stats.totalGenerated.toLocaleString();
    if (flaggedEl) flaggedEl.textContent = this.state.stats.anomaliesFlagged.toLocaleString();

    if (rateEl && this.state.stats.startTime) {
      const elapsedSec = Math.max(1, (Date.now() - this.state.stats.startTime) / 1000);
      const rate = (this.state.stats.sessionTxCount / elapsedSec).toFixed(1);
      rateEl.textContent = `${rate} tx/s`;
    }
  },

  async triggerManualPreset(presetKey) {
    try {
      const res = await window.FraudShieldAPI.triggerPreset(presetKey);
      document.getElementById('simulator-modal')?.classList.remove('open');
      if (res) {
        window.dispatchEvent(new CustomEvent('fraudshield:new-transaction', { detail: res }));
        window.FraudShieldDashboard?.showToast(
          `Evaluated ${presetKey}: ${res.tx_id} | ${res.risk_tier} (Score: ${res.risk_score})`,
          res.risk_tier === 'CRITICAL' ? 'danger' : res.risk_tier === 'HIGH' ? 'warning' : 'success'
        );
      }
    } catch (e) {
      console.error('Manual preset trigger failed:', e);
    }
  },

  async handleCustomPaymentSimulation() {
    const fireBtn = document.getElementById('btn-fire-simulation');
    const origHtml = fireBtn ? fireBtn.innerHTML : '';
    if (fireBtn) {
      fireBtn.disabled = true;
      fireBtn.innerHTML = `<span>Evaluating...</span>`;
    }

    try {
      const payload = {
        sender_upi: document.getElementById('sim-sender-upi')?.value.trim() || 'user@bank',
        receiver_upi: document.getElementById('sim-receiver-upi')?.value.trim() || 'merchant@upi',
        amount: parseFloat(document.getElementById('sim-amount')?.value) || 1000.0,
        channel: document.getElementById('sim-channel')?.value || 'UPI_APP',
        device_id: document.getElementById('sim-device')?.value.trim() || 'DEV-DEFAULT',
        location_city: document.getElementById('sim-city')?.value.trim() || 'Mumbai'
      };

      const result = await window.FraudShieldAPI.evaluateTransaction(payload);
      
      document.getElementById('simulator-modal')?.classList.remove('open');
      window.dispatchEvent(new CustomEvent('fraudshield:new-transaction', { detail: result }));

      const isHigh = result.risk_tier === 'HIGH' || result.risk_tier === 'CRITICAL';
      window.FraudShieldDashboard?.showToast(
        `Custom Tx Evaluated: ${result.tx_id} | ${result.risk_tier} (Score: ${result.risk_score})`,
        isHigh ? 'danger' : 'success'
      );

    } catch (err) {
      console.error('Simulation error:', err);
      window.FraudShieldDashboard?.showToast('Simulation failed: ' + err.message, 'danger');
    } finally {
      if (fireBtn) {
        fireBtn.disabled = false;
        fireBtn.innerHTML = origHtml;
      }
    }
  }
};

window.FraudShieldSimulator = FraudShieldSimulator;
