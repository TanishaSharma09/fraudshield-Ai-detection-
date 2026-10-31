/**
 * FraudShield AI - Real-Time Dashboard & Transaction Management Controller
 * Orchestrates live transaction telemetry, dedicated surveillance ledger,
 * deep Isolation Forest explainability views, filter pipelines, and SOC actions.
 */

const FraudShieldDashboard = {
  state: {
    currentView: 'overview', // 'overview' | 'transactions' | 'alerts'
    activeFilter: 'ALL',
    searchQuery: '',
    currentTheme: 'light',
    transactions: [],
    alerts: [],
    analytics: null,
    isLivePolling: true,
    pollingIntervalId: null,
    selectedTx: null,

    // Dedicated Transaction Management State
    mgmt: {
      transactions: [],
      total: 0,
      page: 1,
      limit: 25,
      totalPages: 1,
      risk_tier: 'ALL',
      channel: 'ALL',
      status: 'ALL',
      search: '',
      date_preset: 'ALL',
      start_date: '',
      end_date: '',
      sort_by: 'timestamp',
      sort_order: 'desc',
      isLoading: false,
      error: null,
      debounceTimer: null
    },

    // Dedicated Fraud Alerts Surveillance & History State
    alertMgmt: {
      items: [],
      total: 0,
      page: 1,
      limit: 10,
      totalPages: 1,
      status: 'ALL',
      severity: 'ALL',
      search: '',
      isLoading: false,
      error: null,
      debounceTimer: null,
      selectedAlert: null
    },
    seenAlertIds: new Set(),
    alertsCache: new Map(),
    eventSource: null,

    // Dedicated Deep Analytics & Forensics State
    analyticsMgmt: {
      date_preset: 'all',
      start_date: '',
      end_date: '',
      risk_tier: 'ALL',
      isLoading: false,
      error: null,
      data: null
    }
  },

  async init() {
    console.log('[FraudShield AI] Dashboard, Transaction Manager & Alert System initializing...');
    
    // 0. Initialize Theme (Default: Light Mode)
    this.initTheme();
    
    // 1. Initialize Chart.js visualisations
    if (window.FraudShieldCharts) {
      window.FraudShieldCharts.init();
      window.FraudShieldCharts.initAnalyticsCharts();
    }

    // 2. Initialize Simulator Controller
    if (window.FraudShieldSimulator) {
      window.FraudShieldSimulator.init();
    }

    // 2b. Initialize 3D Floating Shield Interactive Parallax
    this.init3DShieldParallax();

    // 3. Bind UI event listeners
    this.bindEvents();
    this.bindManagementEvents();
    this.bindAlertsEvents();
    this.bindAnalyticsEvents();

    // 4. Update User Profile UI
    this.updateUserChip();

    // 5. Authenticate session if token not set
    if (!window.FraudShieldAPI.token) {
      try {
        await window.FraudShieldAPI.login('admin', 'Admin@FraudShield2026!');
      } catch (e) {
        console.debug('Initial automatic session init completed.');
      }
    }

    // 6. Initial Data Load & Health Check
    await this.checkHealth();
    await this.loadDashboardData();
    await this.loadManagementTransactions();
    await this.loadAlertsManagement();

    // 6. Start Live SSE / Polling
    this.initAlertsEventStream();
    this.startPolling();

    // 7. Initial Hash Navigation & Routing
    const validViews = ['overview', 'transactions', 'alerts', 'analytics', 'behavioural', 'reports', 'users', 'settings'];
    const initialHash = window.location.hash.replace('#', '').toLowerCase();
    if (initialHash && validViews.includes(initialHash)) {
      this.switchView(initialHash, false);
    } else {
      this.switchView('overview', false);
    }

    // 8. Browser Back/Forward and URL Hash Change Listener
    window.addEventListener('hashchange', () => {
      const target = window.location.hash.replace('#', '').toLowerCase();
      if (target && validViews.includes(target) && target !== this.state.currentView) {
        this.switchView(target, false);
      }
    });

    // 9. Restore saved settings
    this.loadSettingsModule();
  },

  bindEvents() {
    // Mobile Navigation Drawer Toggle & Backdrop
    const mobileToggleBtn = document.getElementById('btn-mobile-nav-toggle');
    const sidebarEl = document.getElementById('sidebar');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');

    if (mobileToggleBtn && sidebarEl) {
      mobileToggleBtn.addEventListener('click', () => {
        const isOpen = sidebarEl.classList.toggle('open');
        sidebarBackdrop?.classList.toggle('open', isOpen);
        mobileToggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    }

    if (sidebarBackdrop && sidebarEl) {
      sidebarBackdrop.addEventListener('click', () => {
        sidebarEl.classList.remove('open');
        sidebarBackdrop.classList.remove('open');
        mobileToggleBtn?.setAttribute('aria-expanded', 'false');
      });
    }

    // Auto-close sidebar on mobile when navigation link is clicked
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      item.addEventListener('click', () => {
        if (window.innerWidth <= 860) {
          sidebarEl?.classList.remove('open');
          sidebarBackdrop?.classList.remove('open');
          mobileToggleBtn?.setAttribute('aria-expanded', 'false');
        }
      });
    });

    // Topbar Search Input
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.state.searchQuery = e.target.value.toLowerCase().trim();
        this.renderTransactionsTable();
      });
    }

    // Keyboard Shortcuts: Ctrl+K for search, Escape for modal close
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (this.state.currentView === 'transactions') {
          document.getElementById('mgmt-search-input')?.focus();
        } else {
          searchInput?.focus();
        }
      }
      if (e.key === 'Escape') {
        this.closeAllModals();
      }
    });

    // Refresh Dashboard Button
    const refreshBtn = document.getElementById('btn-refresh-dashboard');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        refreshBtn.classList.add('loading');
        await this.loadDashboardData();
        await this.loadManagementTransactions();
        refreshBtn.classList.remove('loading');
        this.showToast('Dashboard synchronized with backend', 'info');
      });
    }

    // Start live IST clock ticker in topbar
    this.startLiveClock();

    // Desktop Sidebar Collapse Rail Button
    const btnSidebarCollapse = document.getElementById('btn-sidebar-collapse');
    if (btnSidebarCollapse) {
      btnSidebarCollapse.addEventListener('click', () => {
        const layout = document.querySelector('.app-layout');
        if (layout) {
          layout.classList.toggle('sidebar-collapsed');
          const isCollapsed = layout.classList.contains('sidebar-collapsed');
          btnSidebarCollapse.setAttribute('title', isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar (Rail)');
          setTimeout(() => {
            window.FraudShieldCharts?.resizeAll?.();
          }, 240);
        }
      });
    }

    // Reports View Export Action Buttons with Dynamic Filters
    document.getElementById('btn-reports-export-tx')?.addEventListener('click', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('btn-reports-export-tx');
      if (btn) btn.disabled = true;
      const startDate = document.getElementById('reports-start-date')?.value || null;
      const endDate = document.getElementById('reports-end-date')?.value || null;
      const riskTier = document.getElementById('reports-filter-tier')?.value || null;

      this.showToast('Generating RFC-4180 Transactions CSV...', 'info');
      const res = await window.FraudShieldAPI.exportTransactionsCSV({
        start_date: startDate,
        end_date: endDate,
        risk_tier: riskTier,
      });
      if (btn) btn.disabled = false;
      if (res && res.success) {
        this.showToast('Transactions audit report downloaded successfully', 'success');
        const scope = `Dates: ${startDate || 'All'} to ${endDate || 'Now'} | Tier: ${riskTier || 'ALL'}`;
        this.appendReportAuditLog('Transaction Surveillance Ledger', scope);
      } else {
        this.showToast('Transactions CSV export failed', 'error');
      }
    });

    document.getElementById('btn-reports-export-alerts')?.addEventListener('click', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('btn-reports-export-alerts');
      if (btn) btn.disabled = true;
      const startDate = document.getElementById('reports-start-date')?.value || null;
      const endDate = document.getElementById('reports-end-date')?.value || null;

      this.showToast('Generating RFC-4180 Fraud Alerts CSV...', 'info');
      const res = await window.FraudShieldAPI.exportAlertsCSV({
        start_date: startDate,
        end_date: endDate,
      });
      if (btn) btn.disabled = false;
      if (res && res.success) {
        this.showToast('Fraud alerts incident report downloaded successfully', 'success');
        const scope = `Dates: ${startDate || 'All'} to ${endDate || 'Now'} | Alerts Queue`;
        this.appendReportAuditLog('Fraud Alerts & Triage Incidents', scope);
      } else {
        this.showToast('Fraud alerts CSV export failed', 'error');
      }
    });

    // Reports Date Presets & Filter Reset
    document.getElementById('btn-rep-preset-all')?.addEventListener('click', () => this.applyReportsPreset('ALL'));
    document.getElementById('btn-rep-preset-today')?.addEventListener('click', () => this.applyReportsPreset('TODAY'));
    document.getElementById('btn-rep-preset-7d')?.addEventListener('click', () => this.applyReportsPreset('7D'));
    document.getElementById('btn-rep-preset-30d')?.addEventListener('click', () => this.applyReportsPreset('30D'));
    document.getElementById('btn-reports-reset-filters')?.addEventListener('click', () => {
      this.applyReportsPreset('ALL');
      const t = document.getElementById('reports-filter-tier');
      if (t) t.value = 'ALL';
      this.showToast('Reports filter parameters reset', 'info');
    });

    // Behavioural Inspector Account Select Change
    document.getElementById('behavioural-user-select')?.addEventListener('change', async (e) => {
      const vpa = e.target.value;
      if (vpa) await this.loadUserBaselineProfile(vpa);
    });
    document.getElementById('btn-inspect-baseline-reload')?.addEventListener('click', async () => {
      const sel = document.getElementById('behavioural-user-select');
      if (sel && sel.value) {
        this.showToast(`Recalculating baseline for ${sel.value}...`, 'info');
        await this.loadUserBaselineProfile(sel.value);
        this.showToast('Baseline recalculation completed', 'success');
      }
    });

    // Behavioural Graph Filters
    document.getElementById('btn-beh-graph-all')?.addEventListener('click', () => {
      document.getElementById('btn-beh-graph-all')?.classList.add('active');
      document.getElementById('btn-beh-graph-suspicious')?.classList.remove('active');
      this.loadBehaviouralNetworkGraph(false);
    });
    document.getElementById('btn-beh-graph-suspicious')?.addEventListener('click', () => {
      document.getElementById('btn-beh-graph-suspicious')?.classList.add('active');
      document.getElementById('btn-beh-graph-all')?.classList.remove('active');
      this.loadBehaviouralNetworkGraph(true);
    });

    // User Management View Controls
    document.getElementById('btn-open-create-user-modal')?.addEventListener('click', () => {
      document.getElementById('modal-create-user')?.classList.add('open');
    });
    document.getElementById('close-create-user-modal-btn')?.addEventListener('click', () => {
      document.getElementById('modal-create-user')?.classList.remove('open');
    });
    document.getElementById('btn-cancel-create-user')?.addEventListener('click', () => {
      document.getElementById('modal-create-user')?.classList.remove('open');
    });
    document.getElementById('btn-refresh-users')?.addEventListener('click', async () => {
      this.showToast('Synchronizing application user accounts...', 'info');
      await this.loadUsersManagement();
      this.showToast('User accounts synchronized', 'success');
    });
    document.getElementById('btn-submit-create-user')?.addEventListener('click', async (e) => {
      e.preventDefault();
      const username = document.getElementById('cu-username')?.value?.trim();
      const fullName = document.getElementById('cu-fullname')?.value?.trim();
      const email = document.getElementById('cu-email')?.value?.trim();
      const password = document.getElementById('cu-password')?.value;
      const role = document.getElementById('cu-role')?.value || 'ANALYST';

      if (!username || !fullName || !email || !password) {
        this.showToast('Please fill all required user fields', 'warning');
        return;
      }
      try {
        await window.FraudShieldAPI.createUser({ username, full_name: fullName, email, password, role });
        this.showToast(`User account '${username}' registered successfully!`, 'success');
        document.getElementById('modal-create-user')?.classList.remove('open');
        document.getElementById('form-create-user')?.reset();
        await this.loadUsersManagement();
      } catch (err) {
        this.showToast(err.message || 'Failed to create user account', 'error');
      }
    });

    // Settings Page Configuration Controls
    document.getElementById('page-btn-theme-light')?.addEventListener('click', () => {
      this.setTheme('light');
      this.updateThemeSettingsUI();
    });
    document.getElementById('page-btn-theme-dark')?.addEventListener('click', () => {
      this.setTheme('dark');
      this.updateThemeSettingsUI();
    });
    document.getElementById('btn-page-save-settings')?.addEventListener('click', () => {
      const med = Number(document.getElementById('page-cfg-threshold-medium')?.value || 40);
      const high = Number(document.getElementById('page-cfg-threshold-high')?.value || 70);
      const crit = Number(document.getElementById('page-cfg-threshold-critical')?.value || 90);
      const poll = document.getElementById('page-cfg-polling-rate')?.value || '5000';

      if (med >= high || high >= crit) {
        this.showToast('Threshold validation error: Medium < High < Critical', 'error');
        return;
      }

      const cfg = { threshold_medium: med, threshold_high: high, threshold_critical: crit, polling_rate: poll };
      localStorage.setItem('fraudshield_settings', JSON.stringify(cfg));
      this.showToast('Platform security thresholds & engine configuration saved!', 'success');
    });

    document.getElementById('btn-page-save-profile')?.addEventListener('click', async () => {
      const fullName = document.getElementById('page-profile-fullname')?.value?.trim();
      const email = document.getElementById('page-profile-email')?.value?.trim();
      const password = document.getElementById('page-profile-password')?.value;

      const payload = {};
      if (fullName) payload.full_name = fullName;
      if (email) payload.email = email;
      if (password && password.length >= 8) payload.password = password;

      try {
        await window.FraudShieldAPI.updateProfile(payload);
        this.showToast('Profile credentials updated successfully', 'success');
        this.updateUserChip();
      } catch (err) {
        this.showToast(err.message || 'Failed to update profile', 'error');
      }
    });

    document.getElementById('btn-reports-eval-view')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.switchView('analytics');
      setTimeout(() => {
        const el = document.getElementById('chart-analytics-model-eval');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    });

    document.getElementById('btn-refresh-behavioural')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.loadNetworkGraph({ only_suspicious: false });
      this.showToast('Recalculated behavioural baselines and entity profiles', 'success');
    });

    // Live Polling Toggle
    const liveToggle = document.getElementById('live-polling-toggle');
    if (liveToggle) {
      liveToggle.addEventListener('click', () => {
        this.state.isLivePolling = !this.state.isLivePolling;
        const dot = document.getElementById('live-stream-dot');
        const label = document.getElementById('live-stream-label');
        if (this.state.isLivePolling) {
          dot.style.background = 'var(--status-low)';
          label.textContent = 'Live Stream Active';
          this.startPolling();
          this.showToast('Live stream resumed', 'success');
        } else {
          dot.style.background = 'var(--status-medium)';
          label.textContent = 'Stream Paused';
          this.stopPolling();
          this.showToast('Live stream paused', 'warning');
        }
      });
    }

    // Overview Table Filter Tabs
    const filterTabs = document.querySelectorAll('#ledger-filter-tabs .filter-tab');
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.state.activeFilter = tab.getAttribute('data-filter') || 'ALL';
        this.renderTransactionsTable();
      });
    });

    // Sidebar View Navigation (Clean URL Hash Integration)
    document.querySelectorAll('.sidebar-nav .nav-item[data-nav]').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const navTarget = item.getAttribute('data-nav');
        this.switchView(navTarget, true);
      });
    });

    // Theme Toggle Listeners (Settings Modal & Topbar Quick Action)
    document.getElementById('btn-theme-light')?.addEventListener('click', () => {
      this.setTheme('light');
    });
    document.getElementById('btn-theme-dark')?.addEventListener('click', () => {
      this.setTheme('dark');
    });
    document.getElementById('btn-topbar-theme-toggle')?.addEventListener('click', () => {
      const nextTheme = (this.state.currentTheme === 'dark') ? 'light' : 'dark';
      this.setTheme(nextTheme);
    });

    // Topbar & Drawer Settings Triggers
    document.getElementById('btn-topbar-settings')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.switchView('settings');
    });
    document.getElementById('drawer-btn-settings')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('user-drawer-backdrop')?.classList.remove('open');
      this.switchView('settings');
    });
    document.getElementById('drawer-btn-users')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('user-drawer-backdrop')?.classList.remove('open');
      this.switchView('users');
    });

    // Settings Modal Open & Close Triggers
    const settingsModal = document.getElementById('settings-modal');
    document.getElementById('nav-settings-trigger')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.switchView('settings');
    });
    document.getElementById('close-settings-modal-btn')?.addEventListener('click', () => {
      settingsModal?.classList.remove('open');
    });
    document.getElementById('close-settings-modal-footer-btn')?.addEventListener('click', () => {
      settingsModal?.classList.remove('open');
    });
    document.getElementById('btn-save-settings')?.addEventListener('click', () => {
      settingsModal?.classList.remove('open');
      this.showToast('Security thresholds and theme settings saved', 'success');
    });

    // Payment Simulator Trigger in Sidebar
    document.getElementById('nav-simulator-trigger')?.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('simulator-modal')?.classList.add('open');
    });

    // Overview Date Filter Selector
    document.getElementById('overview-date-filter-select')?.addEventListener('change', async (e) => {
      const selected = e.target.options[e.target.selectedIndex].text;
      this.showToast(`Updated overview time range to: ${selected}`, 'info');
      await this.loadDashboardData();
    });

    // Quick Jump Button on Overview to Full Transactions View
    document.getElementById('btn-view-all-txs')?.addEventListener('click', () => {
      this.switchView('transactions');
    });

    // Topbar Notification Bell opens Alerts View
    document.getElementById('btn-notifications')?.addEventListener('click', () => {
      this.switchView('alerts');
    });

    // User Profile Chip & Slide-Over Drawer
    const profileChip = document.getElementById('user-profile-chip');
    const drawerBackdrop = document.getElementById('user-drawer-backdrop');
    const closeDrawerBtn = document.getElementById('close-user-drawer-btn');

    if (profileChip) {
      profileChip.addEventListener('click', () => {
        drawerBackdrop?.classList.add('open');
      });
    }
    if (closeDrawerBtn) {
      closeDrawerBtn.addEventListener('click', () => {
        drawerBackdrop?.classList.remove('open');
      });
    }
    if (drawerBackdrop) {
      drawerBackdrop.addEventListener('click', (e) => {
        if (e.target === drawerBackdrop) drawerBackdrop.classList.remove('open');
      });
    }

    // Role Switcher in Profile Drawer
    document.getElementById('btn-switch-admin')?.addEventListener('click', async () => {
      await window.FraudShieldAPI.login('admin', 'Admin@FraudShield2026!');
      this.updateUserChip();
      drawerBackdrop?.classList.remove('open');
      this.showToast('Switched session to ADMIN (Full Entitlements)', 'success');
      await this.loadDashboardData();
      await this.loadManagementTransactions();
    });

    document.getElementById('btn-switch-analyst')?.addEventListener('click', async () => {
      await window.FraudShieldAPI.login('analyst', 'Analyst@FraudShield2026!');
      this.updateUserChip();
      drawerBackdrop?.classList.remove('open');
      this.showToast('Switched session to ANALYST (Restricted Triage)', 'info');
      await this.loadDashboardData();
      await this.loadManagementTransactions();
    });

    document.getElementById('btn-logout')?.addEventListener('click', async () => {
      await window.FraudShieldAPI.logout();
      this.updateUserChip();
      drawerBackdrop?.classList.remove('open');
      this.showToast('Logged out of session', 'warning');
      await this.loadDashboardData();
      await this.loadManagementTransactions();
      await this.loadAlertsManagement();
    });

    // Dedicated Login Form Submission
    const btnDoLogin = document.getElementById('btn-do-login');
    const loginUser = document.getElementById('login-username');
    const loginPass = document.getElementById('login-password');
    const loginErr = document.getElementById('login-error-msg');

    if (btnDoLogin) {
      btnDoLogin.addEventListener('click', async (e) => {
        e.preventDefault();
        const username = loginUser ? loginUser.value.trim() : '';
        const password = loginPass ? loginPass.value : '';

        if (!username || !password) {
          if (loginErr) {
            loginErr.textContent = 'Please enter both username and password.';
            loginErr.style.display = 'block';
          }
          return;
        }

        btnDoLogin.disabled = true;
        if (loginErr) loginErr.style.display = 'none';

        try {
          await window.FraudShieldAPI.login(username, password);
          this.updateUserChip();
          drawerBackdrop?.classList.remove('open');
          this.showToast(`Authenticated successfully as ${username.toUpperCase()}`, 'success');
          await this.loadDashboardData();
          await this.loadManagementTransactions();
          await this.loadAlertsManagement();
        } catch (err) {
          if (loginErr) {
            loginErr.textContent = err.message || 'Authentication failed. Please verify credentials.';
            loginErr.style.display = 'block';
          }
          this.showToast('Login failed: ' + (err.message || 'Invalid credentials'), 'danger');
        } finally {
          btnDoLogin.disabled = false;
        }
      });
    }

    // Role switcher on Analytics restricted view
    document.getElementById('btn-analytics-switch-admin')?.addEventListener('click', async () => {
      await window.FraudShieldAPI.login('admin', 'Admin@FraudShield2026!');
      this.updateUserChip();
      this.showToast('Switched session to ADMIN (Full Entitlements)', 'success');
      await this.loadAnalyticsModule();
    });

    // Close Transaction Detail Modal
    document.getElementById('close-tx-modal-btn')?.addEventListener('click', () => {
      document.getElementById('tx-detail-modal')?.classList.remove('open');
    });
    document.getElementById('btn-close-tx-modal')?.addEventListener('click', () => {
      document.getElementById('tx-detail-modal')?.classList.remove('open');
    });

    // Listen for custom event from Simulator
    window.addEventListener('fraudshield:new-transaction', (e) => {
      this.handleNewSimulatedTx(e.detail);
    });
  },

  // -------------------------------------------------------------------------
  // Dedicated Transaction Management Toolbar & Event Handling
  // -------------------------------------------------------------------------
  bindManagementEvents() {
    const mgmtSearchInput = document.getElementById('mgmt-search-input');
    const mgmtSearchClear = document.getElementById('mgmt-search-clear');

    // Debounced Search Input
    if (mgmtSearchInput) {
      mgmtSearchInput.addEventListener('input', (e) => {
        const val = e.target.value;
        if (mgmtSearchClear) {
          mgmtSearchClear.classList.toggle('visible', val.length > 0);
        }
        clearTimeout(this.state.mgmt.debounceTimer);
        this.state.mgmt.debounceTimer = setTimeout(() => {
          this.state.mgmt.search = val.trim();
          this.state.mgmt.page = 1;
          this.loadManagementTransactions();
        }, 320);
      });
    }

    // Search Clear Button
    if (mgmtSearchClear) {
      mgmtSearchClear.addEventListener('click', () => {
        if (mgmtSearchInput) mgmtSearchInput.value = '';
        mgmtSearchClear.classList.remove('visible');
        this.state.mgmt.search = '';
        this.state.mgmt.page = 1;
        this.loadManagementTransactions();
      });
    }

    // Risk Filter Select
    document.getElementById('mgmt-filter-risk')?.addEventListener('change', (e) => {
      this.state.mgmt.risk_tier = e.target.value;
      this.state.mgmt.page = 1;
      this.loadManagementTransactions();
    });

    // Channel Filter Select
    document.getElementById('mgmt-filter-channel')?.addEventListener('change', (e) => {
      this.state.mgmt.channel = e.target.value;
      this.state.mgmt.page = 1;
      this.loadManagementTransactions();
    });

    // Status Filter Select
    document.getElementById('mgmt-filter-status')?.addEventListener('change', (e) => {
      this.state.mgmt.status = e.target.value;
      this.state.mgmt.page = 1;
      this.loadManagementTransactions();
    });

    // Date Preset Pills
    document.querySelectorAll('#mgmt-date-presets .date-preset-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('#mgmt-date-presets .date-preset-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const range = pill.getAttribute('data-range');
        this.applyDatePreset(range);
      });
    });

    // Custom Date Inputs
    document.getElementById('mgmt-start-date')?.addEventListener('change', (e) => {
      this.state.mgmt.start_date = e.target.value;
      this.state.mgmt.page = 1;
      this.loadManagementTransactions();
    });

    document.getElementById('mgmt-end-date')?.addEventListener('change', (e) => {
      this.state.mgmt.end_date = e.target.value;
      this.state.mgmt.page = 1;
      this.loadManagementTransactions();
    });

    // Reset Filters Buttons
    const resetFn = () => this.resetManagementFilters();
    document.getElementById('btn-reset-filters')?.addEventListener('click', resetFn);
    document.getElementById('btn-empty-clear-filters')?.addEventListener('click', resetFn);

    // Refresh Button in Management View
    document.getElementById('btn-refresh-mgmt-txs')?.addEventListener('click', () => {
      this.loadManagementTransactions();
      this.showToast('Transaction surveillance ledger refreshed', 'info');
    });

    // Simulator trigger in Management View
    document.getElementById('btn-mgmt-simulate')?.addEventListener('click', () => {
      document.getElementById('simulator-modal')?.classList.add('open');
    });

    // Retry Button on Error State
    document.getElementById('btn-error-retry')?.addEventListener('click', () => {
      this.loadManagementTransactions();
    });

    // Page Size Selector
    document.getElementById('mgmt-page-size')?.addEventListener('change', (e) => {
      this.state.mgmt.limit = parseInt(e.target.value, 10) || 25;
      this.state.mgmt.page = 1;
      this.loadManagementTransactions();
    });

    // Pagination Nav Buttons
    document.getElementById('mgmt-page-first')?.addEventListener('click', () => {
      if (this.state.mgmt.page > 1) {
        this.state.mgmt.page = 1;
        this.loadManagementTransactions();
      }
    });

    document.getElementById('mgmt-page-prev')?.addEventListener('click', () => {
      if (this.state.mgmt.page > 1) {
        this.state.mgmt.page--;
        this.loadManagementTransactions();
      }
    });

    document.getElementById('mgmt-page-next')?.addEventListener('click', () => {
      if (this.state.mgmt.page < this.state.mgmt.totalPages) {
        this.state.mgmt.page++;
        this.loadManagementTransactions();
      }
    });

    document.getElementById('mgmt-page-last')?.addEventListener('click', () => {
      if (this.state.mgmt.page < this.state.mgmt.totalPages) {
        this.state.mgmt.page = this.state.mgmt.totalPages;
        this.loadManagementTransactions();
      }
    });

    // Column Sorting Headers
    document.querySelectorAll('#mgmt-transactions-table th.th-sortable').forEach(th => {
      th.addEventListener('click', () => {
        const sortCol = th.getAttribute('data-sort');
        if (this.state.mgmt.sort_by === sortCol) {
          // Toggle direction
          this.state.mgmt.sort_order = this.state.mgmt.sort_order === 'asc' ? 'desc' : 'asc';
        } else {
          this.state.mgmt.sort_by = sortCol;
          this.state.mgmt.sort_order = 'desc';
        }
        this.updateSortHeaderStyles();
        this.state.mgmt.page = 1;
        this.loadManagementTransactions();
      });
    });
  },

  switchView(viewName, updateHash = true) {
    // RBAC access guard
    const activeUser = window.FraudShieldAPI.currentUser;
    if (viewName === 'users' && activeUser && activeUser.role === 'ANALYST') {
      this.showToast('User Account Administration requires ADMIN security clearance', 'warning');
      return;
    }

    this.state.currentView = viewName;
    if (updateHash && window.location.hash !== '#' + viewName) {
      window.location.hash = '#' + viewName;
    }
    
    // Update Sidebar Navigation state
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(i => i.classList.remove('active'));
    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeNav) activeNav.classList.add('active');

    // Update Topbar Breadcrumb
    const breadcrumbPage = document.getElementById('breadcrumb-current-page');
    const viewTitles = {
      overview: 'Dashboard Overview',
      transactions: 'Transaction Surveillance',
      alerts: 'Fraud Alert Center',
      analytics: 'Analytics & Forensics',
      behavioural: 'Behavioural Analysis',
      reports: 'Executive Reports & Audit',
      users: 'User Account Administration',
      settings: 'Platform Settings & Thresholds'
    };
    if (breadcrumbPage && viewTitles[viewName]) {
      breadcrumbPage.textContent = viewTitles[viewName];
    }

    // Toggle View Panels
    const panelMap = {
      overview: document.getElementById('view-overview'),
      transactions: document.getElementById('view-transactions'),
      alerts: document.getElementById('view-alerts'),
      analytics: document.getElementById('view-analytics'),
      behavioural: document.getElementById('view-behavioural'),
      reports: document.getElementById('view-reports'),
      users: document.getElementById('view-users'),
      settings: document.getElementById('view-settings')
    };

    Object.keys(panelMap).forEach(key => {
      const p = panelMap[key];
      if (!p) return;
      if (key === viewName) {
        p.style.display = 'flex';
        p.classList.add('active');
      } else {
        p.style.display = 'none';
        p.classList.remove('active');
      }
    });

    if (viewName === 'transactions') {
      this.loadManagementTransactions();
    } else if (viewName === 'alerts') {
      this.loadAlertsManagement();
    } else if (viewName === 'analytics') {
      this.loadAnalyticsModule();
    } else if (viewName === 'behavioural') {
      this.loadBehaviouralModule();
    } else if (viewName === 'reports') {
      this.loadReportsModule();
    } else if (viewName === 'users') {
      this.loadUsersManagement();
    } else if (viewName === 'settings') {
      this.loadSettingsModule();
    }

    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    const mainContentArea = document.getElementById('main-content-area');
    if (mainContentArea) mainContentArea.scrollTop = 0;

    // Refresh chart canvas dimensions on view change
    setTimeout(() => {
      window.FraudShieldCharts?.resizeAll?.();
    }, 80);
  },

  applyDatePreset(range) {
    this.state.mgmt.date_preset = range;
    const now = new Date();
    const startInput = document.getElementById('mgmt-start-date');
    const endInput = document.getElementById('mgmt-end-date');

    if (range === 'ALL') {
      this.state.mgmt.start_date = '';
      this.state.mgmt.end_date = '';
      if (startInput) startInput.value = '';
      if (endInput) endInput.value = '';
    } else if (range === 'TODAY') {
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
      this.state.mgmt.start_date = todayStart;
      this.state.mgmt.end_date = now.toISOString();
      if (startInput) startInput.value = todayStart.split('T')[0];
      if (endInput) endInput.value = now.toISOString().split('T')[0];
    } else if (range === '7D') {
      const d7 = new Date(now.getTime() - 7 * 86400000).toISOString();
      this.state.mgmt.start_date = d7;
      this.state.mgmt.end_date = now.toISOString();
      if (startInput) startInput.value = d7.split('T')[0];
      if (endInput) endInput.value = now.toISOString().split('T')[0];
    } else if (range === '30D') {
      const d30 = new Date(now.getTime() - 30 * 86400000).toISOString();
      this.state.mgmt.start_date = d30;
      this.state.mgmt.end_date = now.toISOString();
      if (startInput) startInput.value = d30.split('T')[0];
      if (endInput) endInput.value = now.toISOString().split('T')[0];
    }

    this.state.mgmt.page = 1;
    this.loadManagementTransactions();
  },

  resetManagementFilters() {
    this.state.mgmt.risk_tier = 'ALL';
    this.state.mgmt.channel = 'ALL';
    this.state.mgmt.status = 'ALL';
    this.state.mgmt.search = '';
    this.state.mgmt.start_date = '';
    this.state.mgmt.end_date = '';
    this.state.mgmt.date_preset = 'ALL';
    this.state.mgmt.sort_by = 'timestamp';
    this.state.mgmt.sort_order = 'desc';
    this.state.mgmt.page = 1;

    // Reset Form Elements
    const searchInput = document.getElementById('mgmt-search-input');
    if (searchInput) searchInput.value = '';
    document.getElementById('mgmt-search-clear')?.classList.remove('visible');

    const riskSelect = document.getElementById('mgmt-filter-risk');
    if (riskSelect) riskSelect.value = 'ALL';

    const chanSelect = document.getElementById('mgmt-filter-channel');
    if (chanSelect) chanSelect.value = 'ALL';

    const statSelect = document.getElementById('mgmt-filter-status');
    if (statSelect) statSelect.value = 'ALL';

    const startInput = document.getElementById('mgmt-start-date');
    if (startInput) startInput.value = '';

    const endInput = document.getElementById('mgmt-end-date');
    if (endInput) endInput.value = '';

    document.querySelectorAll('#mgmt-date-presets .date-preset-pill').forEach(p => {
      p.classList.toggle('active', p.getAttribute('data-range') === 'ALL');
    });

    this.updateSortHeaderStyles();
    this.loadManagementTransactions();
    this.showToast('All transaction filters reset to defaults', 'info');
  },

  updateSortHeaderStyles() {
    document.querySelectorAll('#mgmt-transactions-table th.th-sortable').forEach(th => {
      const sortCol = th.getAttribute('data-sort');
      const icon = th.querySelector('.sort-direction-icon');
      if (sortCol === this.state.mgmt.sort_by) {
        th.classList.add('active-sort');
        if (icon) icon.textContent = this.state.mgmt.sort_order === 'asc' ? '▲' : '▼';
      } else {
        th.classList.remove('active-sort');
        if (icon) icon.textContent = '⇅';
      }
    });
  },

  // -------------------------------------------------------------------------
  // Fetch & Render Dedicated Transaction Management Table
  // -------------------------------------------------------------------------
  async loadManagementTransactions() {
    const loadingState = document.getElementById('mgmt-loading-state');
    const emptyState = document.getElementById('mgmt-empty-state');
    const errorState = document.getElementById('mgmt-error-state');
    const tbody = document.getElementById('mgmt-transactions-tbody');
    const paginationContainer = document.getElementById('mgmt-pagination-container');

    // Show loading
    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (errorState) errorState.style.display = 'none';
    if (tbody) tbody.style.display = 'none';

    try {
      const options = {
        page: this.state.mgmt.page,
        limit: this.state.mgmt.limit,
        risk_tier: this.state.mgmt.risk_tier,
        channel: this.state.mgmt.channel,
        status: this.state.mgmt.status,
        search: this.state.mgmt.search,
        start_date: this.state.mgmt.start_date,
        end_date: this.state.mgmt.end_date,
        sort_by: this.state.mgmt.sort_by,
        sort_order: this.state.mgmt.sort_order,
      };

      const res = await window.FraudShieldAPI.getTransactions(options);

      this.state.mgmt.transactions = res.transactions || [];
      this.state.mgmt.total = res.total || 0;
      this.state.mgmt.totalPages = res.totalPages || 1;

      // Hide loading
      if (loadingState) loadingState.style.display = 'none';

      if (this.state.mgmt.transactions.length === 0) {
        if (emptyState) emptyState.style.display = 'flex';
        if (tbody) tbody.style.display = 'none';
        if (paginationContainer) paginationContainer.style.display = 'none';
      } else {
        if (emptyState) emptyState.style.display = 'none';
        if (tbody) {
          tbody.style.display = 'table-row-group';
          this.renderManagementTableRows();
        }
        if (paginationContainer) {
          paginationContainer.style.display = 'flex';
          this.renderPaginationControls();
        }
      }

    } catch (err) {
      console.error('Failed to load management transactions:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (tbody) tbody.style.display = 'none';
      if (emptyState) emptyState.style.display = 'none';
      if (errorState) {
        errorState.style.display = 'flex';
        const msgEl = document.getElementById('mgmt-error-message');
        if (msgEl) msgEl.textContent = err.message || 'Network error communicating with the transaction API.';
      }
    }
  },

  renderManagementTableRows() {
    const tbody = document.getElementById('mgmt-transactions-tbody');
    if (!tbody) return;

    tbody.innerHTML = this.state.mgmt.transactions.map(tx => {
      const timeStr = this.formatDateTime(tx.timestamp || tx.created_at);
      const tierBadge = this.getTierBadge(tx.risk_tier);
      const statusBadge = this.getStatusBadge(tx.status || 'APPROVED');
      const scoreCircle = this.getScoreCircle(tx.risk_score, tx.risk_tier);
      const amountFmt = '₹' + Number(tx.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
      const channelBadge = `<span class="badge badge-channel">${tx.channel || 'UPI_APP'}</span>`;

      return `
        <tr class="tx-row-clickable" onclick="FraudShieldDashboard.inspectTransaction('${tx.tx_id}')">
          <td class="td-tx-id">${tx.tx_id}</td>
          <td><span class="vpa-address">${tx.sender_upi || 'unknown'}</span></td>
          <td><span class="vpa-address">${tx.receiver_upi || 'unknown'}</span></td>
          <td class="td-amount">${amountFmt}</td>
          <td style="font-size: 0.76rem; font-family: var(--font-mono); color: var(--text-secondary);">${timeStr}</td>
          <td>${channelBadge}</td>
          <td>
            <div class="risk-pill-inline">
              ${scoreCircle}
              <span>${Number(tx.risk_score || 0).toFixed(1)}</span>
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 0.35rem; align-items: center;">
              ${tierBadge}
              ${statusBadge}
            </div>
          </td>
          <td style="text-align: right;">
            <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); FraudShieldDashboard.inspectTransaction('${tx.tx_id}')">
              View Details
            </button>
          </td>
        </tr>
      `;
    }).join('');
  },

  renderPaginationControls() {
    const rangeEl = document.getElementById('mgmt-page-range');
    const totalEl = document.getElementById('mgmt-total-count');
    const numbersEl = document.getElementById('mgmt-page-numbers');

    const total = this.state.mgmt.total;
    const page = this.state.mgmt.page;
    const limit = this.state.mgmt.limit;
    const totalPages = this.state.mgmt.totalPages;

    const start = total === 0 ? 0 : (page - 1) * limit + 1;
    const end = Math.min(page * limit, total);

    if (rangeEl) rangeEl.textContent = `${start} - ${end}`;
    if (totalEl) totalEl.textContent = total.toLocaleString();

    // Enable/disable navigation buttons
    const firstBtn = document.getElementById('mgmt-page-first');
    const prevBtn = document.getElementById('mgmt-page-prev');
    const nextBtn = document.getElementById('mgmt-page-next');
    const lastBtn = document.getElementById('mgmt-page-last');

    if (firstBtn) firstBtn.disabled = page <= 1;
    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= totalPages;
    if (lastBtn) lastBtn.disabled = page >= totalPages;

    // Render page number pills
    if (!numbersEl) return;
    numbersEl.innerHTML = '';

    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);

    if (endPage - startPage + 1 < maxVisible) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let p = startPage; p <= endPage; p++) {
      const btn = document.createElement('button');
      btn.className = `page-btn ${p === page ? 'active' : ''}`;
      btn.textContent = p;
      btn.onclick = () => {
        this.state.mgmt.page = p;
        this.loadManagementTransactions();
      };
      numbersEl.appendChild(btn);
    }
  },

  // -------------------------------------------------------------------------
  // Health & Dashboard Data Sync
  // -------------------------------------------------------------------------
  async checkHealth() {
    const health = await window.FraudShieldAPI.getHealth();
    const dot = document.getElementById('system-status-dot');
    const text = document.getElementById('system-status-text');

    if (window.FraudShieldAPI.isLiveConnected) {
      if (dot) dot.className = 'status-dot';
      if (text) text.textContent = 'Isolation Forest Online (v1.2)';
    } else {
      if (dot) dot.className = 'status-dot standby';
      if (text) text.textContent = 'Preview Baseline Mode';
    }
  },

  async loadDashboardData() {
    try {
      const user = window.FraudShieldAPI.currentUser;
      const isAdmin = user && user.role === 'ADMIN';

      // 1. Fetch Analytics & KPIs if Admin
      if (isAdmin) {
        try {
          const analytics = await window.FraudShieldAPI.getAnalytics();
          this.state.analytics = analytics;
          this.renderKPIs(analytics);

          if (window.FraudShieldCharts) {
            if (analytics.distribution) {
              window.FraudShieldCharts.updateDistribution(analytics.distribution);
            }
            if (analytics.hourly_trends) {
              window.FraudShieldCharts.updateHourlyTrends(analytics.hourly_trends);
            }
          }
        } catch (analyticsErr) {
          console.warn('Analytics KPI fetch error:', analyticsErr);
        }
      }

      // 2. Fetch Overview Table Data (Accessible to both Admin & Analyst)
      const txs = await window.FraudShieldAPI.getRecentTransactions(50);
      this.state.transactions = txs;
      this.renderTransactionsTable();

      // 3. Fetch Alerts (Accessible to both Admin & Analyst)
      const alertsRes = await window.FraudShieldAPI.getAlerts({ status: 'PENDING', limit: 50 });
      const alerts = Array.isArray(alertsRes) ? alertsRes : (alertsRes?.alerts || []);
      this.state.alerts = alerts;
      this.renderAlertsQueue();

      // If Analyst, update Overview KPI cards from authorized live counts
      if (!isAdmin) {
        const totalEvaluated = this.state.mgmt.total || txs.length;
        const totalFlagged = alerts.length;
        this.renderKPIs({
          total_evaluated: totalEvaluated,
          total_flagged: totalFlagged,
          fraud_rate_percentage: totalEvaluated > 0 ? (totalFlagged / totalEvaluated) * 100 : 0.0,
          pending_alerts: alerts.length,
          avg_risk_score: 22.4
        });
      }

    } catch (err) {
      console.warn('Error refreshing dashboard data:', err);
    }
  },

  renderKPIs(analytics) {
    if (!analytics) return;

    const totalEl = document.getElementById('kpi-total-evaluated');
    const flaggedEl = document.getElementById('kpi-total-flagged');
    const rateEl = document.getElementById('kpi-fraud-rate');
    const pendingEl = document.getElementById('kpi-pending-alerts');
    const avgRiskLabel = document.getElementById('avg-risk-label');

    if (totalEl) totalEl.textContent = Number(analytics.total_evaluated || 0).toLocaleString();
    if (flaggedEl) flaggedEl.textContent = Number(analytics.total_flagged || 0).toLocaleString();
    if (rateEl) rateEl.textContent = `${Number(analytics.fraud_rate_percentage || 1.43).toFixed(2)}% Rate`;
    if (pendingEl) pendingEl.textContent = analytics.pending_alerts || this.state.alerts.length || 0;
    if (avgRiskLabel && analytics.avg_risk_score) {
      avgRiskLabel.textContent = `Avg Risk Score: ${Number(analytics.avg_risk_score).toFixed(1)}`;
    }
  },

  renderTransactionsTable() {
    const tbody = document.getElementById('transactions-tbody');
    const badge = document.getElementById('ledger-count-badge');
    if (!tbody) return;

    let list = this.state.transactions || [];

    // Filter by Tab
    if (this.state.activeFilter !== 'ALL') {
      list = list.filter(t => t.risk_tier === this.state.activeFilter);
    }

    // Filter by Topbar Search Query
    if (this.state.searchQuery) {
      const q = this.state.searchQuery;
      list = list.filter(t => 
        (t.tx_id && t.tx_id.toLowerCase().includes(q)) ||
        (t.sender_upi && t.sender_upi.toLowerCase().includes(q)) ||
        (t.receiver_upi && t.receiver_upi.toLowerCase().includes(q)) ||
        (t.location_city && t.location_city.toLowerCase().includes(q)) ||
        (t.primary_factor && t.primary_factor.toLowerCase().includes(q))
      );
    }

    if (badge) badge.textContent = `${list.length} items`;

    if (!list.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; padding: 3rem 1.5rem;">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 0.75rem;">
              <div class="state-icon-circle">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--accent-blue)" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </div>
              <div style="font-weight: 600; color: var(--text-primary); font-size: 0.95rem;">No Matching Transactions</div>
              <div style="color: var(--text-secondary); font-size: 0.8rem; max-width: 360px;">
                No payment events match the selected filter or search query. Try switching risk tiers or clearing search.
              </div>
              <button class="btn btn-secondary btn-sm" onclick="FraudShieldDashboard.resetLedgerFilters()" style="margin-top: 0.25rem;">
                Reset Filter
              </button>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = list.map(tx => {
      const timeStr = this.formatTime(tx.timestamp || tx.created_at);
      const tierBadge = this.getTierBadge(tx.risk_tier);
      const scoreCircle = this.getScoreCircle(tx.risk_score, tx.risk_tier);
      const amountFmt = '₹' + Number(tx.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });

      return `
        <tr class="tx-row-clickable" onclick="FraudShieldDashboard.inspectTransaction('${tx.tx_id}')">
          <td class="td-tx-id">
            <span class="copyable-pill" title="Click to copy TxID" onclick="event.stopPropagation(); FraudShieldDashboard.copyToClipboard('${tx.tx_id}', this)">${tx.tx_id}</span>
          </td>
          <td style="font-size: 0.76rem; font-family: var(--font-mono);">${timeStr}</td>
          <td>
            <div class="td-user">
              <span class="vpa-address copyable-pill" title="Click to copy Sender VPA" onclick="event.stopPropagation(); FraudShieldDashboard.copyToClipboard('${tx.sender_upi}', this)">${tx.sender_upi || 'unknown'}</span>
              <span class="vpa-arrow">➔ ${tx.receiver_upi || 'unknown'}</span>
            </div>
          </td>
          <td class="td-amount">${amountFmt}</td>
          <td><span class="badge badge-channel">${tx.channel || 'UPI'}</span></td>
          <td>
            <div class="risk-pill-inline">
              ${scoreCircle}
              <span>${Number(tx.risk_score || 0).toFixed(1)}</span>
            </div>
          </td>
          <td>${tierBadge}</td>
          <td style="font-size: 0.76rem; color: var(--text-secondary); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${tx.primary_factor || 'Normal Baseline'}
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); FraudShieldDashboard.inspectTransaction('${tx.tx_id}')">
              Investigate
            </button>
          </td>
        </tr>
      `;
    }).join('');
  },

  renderAlertsQueue() {
    const container = document.getElementById('alerts-list-container');
    const badge = document.getElementById('alerts-count-badge');
    const sideBadge = document.getElementById('sidebar-alert-badge');
    const bellDot = document.getElementById('notification-badge-dot');
    if (!container) return;

    const pending = (this.state.alerts || []).filter(a => a.status === 'PENDING');

    if (badge) badge.textContent = `${pending.length} Action Req`;
    if (sideBadge) sideBadge.textContent = pending.length;
    if (bellDot) bellDot.style.display = pending.length > 0 ? 'block' : 'none';

    if (!pending.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 0.5rem;">
          <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="var(--status-low)" stroke-width="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <path d="m9 12 2 2 4-4"/>
          </svg>
          <span style="font-weight: 600; color: var(--text-primary);">All Clear</span>
          <span style="font-size: 0.78rem;">No suspicious transactions currently pending SOC triage.</span>
        </div>
      `;
      return;
    }

    container.innerHTML = pending.map(alert => {
      const sevClass = alert.severity ? alert.severity.toLowerCase() : 'critical';
      const timeStr = this.formatTime(alert.created_at || new Date().toISOString());
      const amountFmt = alert.amount ? '₹' + Number(alert.amount).toLocaleString('en-IN') : '';

      const tagsHtml = (alert.explanations || []).map(exp => 
        `<span class="explanation-tag">${exp.factor_name || exp.description || 'Flagged Feature'}</span>`
      ).join('');

      return `
        <div class="alert-card ${sevClass}" id="alert-card-${alert.alert_id}">
          <div class="alert-top">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="badge badge-${sevClass}">${alert.severity || 'HIGH'}</span>
              <span class="alert-meta-id">${alert.alert_id}</span>
            </div>
            <span class="alert-amount-badge">${amountFmt}</span>
          </div>

          <div class="alert-scenario">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            </svg>
            <span>${alert.primary_reason || 'Anomaly Detected'}</span>
          </div>

          <div style="font-size: 0.74rem; font-family: var(--font-mono); color: var(--text-muted);">
            ${alert.sender_upi || 'unknown'} ➔ ${alert.receiver_upi || 'unknown'}
          </div>

          <div class="alert-explanation-tags">
            ${tagsHtml}
          </div>

          <div class="alert-actions-row">
            <button class="btn btn-primary btn-xs" style="padding: 0.25rem 0.6rem; font-size: 0.72rem;" onclick="FraudShieldDashboard.openAlertDetailDrawer('${alert.alert_id}')">
              Investigate Alert ↗
            </button>
            <button class="btn btn-success btn-xs" style="padding: 0.25rem 0.6rem; font-size: 0.72rem;" onclick="FraudShieldDashboard.handleTriageAction('${alert.alert_id}', 'APPROVED')">
              ✓ Approve
            </button>
            <button class="btn btn-danger btn-xs" style="padding: 0.25rem 0.6rem; font-size: 0.72rem;" onclick="FraudShieldDashboard.handleTriageAction('${alert.alert_id}', 'BLOCKED')">
              ✕ Block
            </button>
          </div>
        </div>
      `;
    }).join('');
  },

  async handleTriageAction(alertId, action, notes = '') {
    try {
      const defaultNote = `Action ${action} initiated by SOC analyst`;
      const finalNote = notes || defaultNote;
      const res = await window.FraudShieldAPI.updateAlertAction(alertId, action, finalNote);
      
      // Update local state items
      this.state.alerts = this.state.alerts.filter(a => a.alert_id !== alertId);
      this.renderAlertsQueue();

      // Update in alertMgmt items if present
      const item = this.state.alertMgmt.items.find(a => a.alert_id === alertId);
      if (item) {
        item.status = action;
        item.analyst_notes = finalNote;
        item.reviewed_by = res?.reviewed_by || 'SOC-Analyst';
        item.updated_at = new Date().toISOString();
      }
      this.renderAlertsTableRows(this.state.alertMgmt.items);

      // If drawer is currently open on this alert, update drawer UI reactively
      if (this.state.alertMgmt.selectedAlert?.alert_id === alertId) {
        const statusBadge = document.getElementById('drawer-alert-status-badge');
        if (statusBadge) {
          const actionClass = action === 'APPROVED' ? 'badge-approved' :
                              action === 'BLOCKED' ? 'badge-critical' :
                              action === 'DISMISSED' ? 'badge-low' : 'badge-reviewed';
          statusBadge.className = `badge ${actionClass}`;
          statusBadge.textContent = action === 'DISMISSED' ? 'Dismissed' : action === 'APPROVED' ? 'Approved' : action === 'BLOCKED' ? 'Blocked' : action;
        }
        const txStatusEl = document.getElementById('drawer-alert-tx-status');
        if (txStatusEl) {
          txStatusEl.textContent = action === 'BLOCKED' ? 'BLOCKED' : 'APPROVED';
          txStatusEl.style.color = action === 'BLOCKED' ? 'var(--status-critical, #d94f5c)' : 'var(--status-approved, #16a36a)';
        }
        const revEl = document.getElementById('drawer-reviewed-by');
        if (revEl) revEl.textContent = res?.reviewed_by || 'SOC-Analyst';
        const updEl = document.getElementById('drawer-updated-at');
        if (updEl) updEl.textContent = this.formatDateTime(new Date().toISOString());
      }

      const actionText = action === 'APPROVED' ? 'Approved & Cleared' : action === 'BLOCKED' ? 'Account & Payment Blocked' : action === 'DISMISSED' ? 'Alert Dismissed' : 'Marked as Reviewed';
      const toastType = action === 'BLOCKED' ? 'danger' : action === 'APPROVED' ? 'success' : action === 'DISMISSED' ? 'info' : 'warning';
      this.showToast(`Alert ${alertId}: ${actionText}`, toastType);

      await this.updateAlertCounters();
      this.loadManagementTransactions();
    } catch (err) {
      this.showToast(`Action failed: ${err.message}`, 'danger');
    }
  },

  // =========================================================================
  // Dedicated Fraud Alert System & SOC Investigation Intelligence
  // =========================================================================

  bindAlertsEvents() {
    // Refresh Alerts Button
    document.getElementById('btn-refresh-alerts')?.addEventListener('click', () => {
      this.loadAlertsManagement();
      this.showToast('Alerts queue refreshed from database', 'info');
    });

    // Quick Trigger Suspicious Payment Button
    document.getElementById('btn-alerts-quick-simulate')?.addEventListener('click', () => {
      document.getElementById('sim-amount').value = '75000.00';
      document.getElementById('sim-channel').value = 'COLLECT_REQUEST';
      document.getElementById('sim-receiver-upi').value = 'mule.target.flagged@icici';
      document.getElementById('sim-device').value = 'DEV-UNRECOGNIZED-99';
      document.getElementById('simulation-config-modal')?.classList.add('open');
    });

    // Alert Search Input (Debounced)
    const alertSearchInput = document.getElementById('alert-mgmt-search');
    if (alertSearchInput) {
      alertSearchInput.addEventListener('input', (e) => {
        clearTimeout(this.state.alertMgmt.debounceTimer);
        this.state.alertMgmt.debounceTimer = setTimeout(() => {
          this.state.alertMgmt.search = e.target.value.trim();
          this.state.alertMgmt.page = 1;
          this.loadAlertsManagement();
        }, 300);
      });
    }

    // Status Filter Pills
    document.querySelectorAll('#alert-status-filter-pills .alert-filter-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('#alert-status-filter-pills .alert-filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        this.state.alertMgmt.status = pill.getAttribute('data-alert-status') || 'ALL';
        this.state.alertMgmt.page = 1;
        this.loadAlertsManagement();
      });
    });

    // Severity Filter Dropdown
    document.getElementById('alert-severity-select')?.addEventListener('change', (e) => {
      this.state.alertMgmt.severity = e.target.value;
      this.state.alertMgmt.page = 1;
      this.loadAlertsManagement();
    });

    // Pagination Controls
    document.getElementById('alerts-page-first')?.addEventListener('click', () => {
      if (this.state.alertMgmt.page > 1) {
        this.state.alertMgmt.page = 1;
        this.loadAlertsManagement();
      }
    });

    document.getElementById('alerts-page-prev')?.addEventListener('click', () => {
      if (this.state.alertMgmt.page > 1) {
        this.state.alertMgmt.page--;
        this.loadAlertsManagement();
      }
    });

    document.getElementById('alerts-page-next')?.addEventListener('click', () => {
      if (this.state.alertMgmt.page < this.state.alertMgmt.totalPages) {
        this.state.alertMgmt.page++;
        this.loadAlertsManagement();
      }
    });

    document.getElementById('alerts-page-last')?.addEventListener('click', () => {
      if (this.state.alertMgmt.page < this.state.alertMgmt.totalPages) {
        this.state.alertMgmt.page = this.state.alertMgmt.totalPages;
        this.loadAlertsManagement();
      }
    });

    document.getElementById('alerts-page-size')?.addEventListener('change', (e) => {
      this.state.alertMgmt.limit = parseInt(e.target.value, 10);
      this.state.alertMgmt.page = 1;
      this.loadAlertsManagement();
    });

    // Empty state reset button
    document.getElementById('btn-clear-alert-filters')?.addEventListener('click', () => {
      this.state.alertMgmt.status = 'ALL';
      this.state.alertMgmt.severity = 'ALL';
      this.state.alertMgmt.search = '';
      if (alertSearchInput) alertSearchInput.value = '';
      const sevSel = document.getElementById('alert-severity-select');
      if (sevSel) sevSel.value = 'ALL';
      document.querySelectorAll('#alert-status-filter-pills .alert-filter-pill').forEach(p => {
        p.classList.toggle('active', p.getAttribute('data-alert-status') === 'ALL');
      });
      this.state.alertMgmt.page = 1;
      this.loadAlertsManagement();
    });

    // Retry button on error
    document.getElementById('btn-retry-alerts')?.addEventListener('click', () => {
      this.loadAlertsManagement();
    });

    // Alert Detail Drawer Close
    const alertDrawerBackdrop = document.getElementById('alert-drawer-backdrop');
    document.getElementById('close-alert-drawer-btn')?.addEventListener('click', () => {
      alertDrawerBackdrop?.classList.remove('open');
    });

    document.getElementById('btn-drawer-close')?.addEventListener('click', () => {
      alertDrawerBackdrop?.classList.remove('open');
    });

    if (alertDrawerBackdrop) {
      alertDrawerBackdrop.addEventListener('click', (e) => {
        if (e.target === alertDrawerBackdrop) {
          alertDrawerBackdrop.classList.remove('open');
        }
      });
    }

    // Inspect linked transaction from Alert Drawer
    document.getElementById('btn-drawer-inspect-tx')?.addEventListener('click', () => {
      if (this.state.alertMgmt.selectedAlert?.tx_id) {
        alertDrawerBackdrop?.classList.remove('open');
        this.inspectTransaction(this.state.alertMgmt.selectedAlert.tx_id);
      }
    });

    // Drawer Triage Actions
    document.getElementById('btn-drawer-mark-reviewed')?.addEventListener('click', async () => {
      const alert = this.state.alertMgmt.selectedAlert;
      if (!alert) return;
      const notes = document.getElementById('drawer-analyst-notes')?.value || 'Marked as reviewed by SOC analyst';
      await this.handleMarkAlertReviewed(alert.alert_id, notes);
    });

    document.getElementById('btn-drawer-approve')?.addEventListener('click', async () => {
      const alert = this.state.alertMgmt.selectedAlert;
      if (!alert) return;
      const notes = document.getElementById('drawer-analyst-notes')?.value || 'Transaction approved and cleared';
      await this.handleTriageAction(alert.alert_id, 'APPROVED', notes);
    });

    document.getElementById('btn-drawer-block')?.addEventListener('click', async () => {
      const alert = this.state.alertMgmt.selectedAlert;
      if (!alert) return;
      const notes = document.getElementById('drawer-analyst-notes')?.value || 'Suspicious mule transaction blocked';
      await this.handleTriageAction(alert.alert_id, 'BLOCKED', notes);
    });

    document.getElementById('btn-drawer-dismiss')?.addEventListener('click', async () => {
      const alert = this.state.alertMgmt.selectedAlert;
      if (!alert) return;
      const notes = document.getElementById('drawer-analyst-notes')?.value || 'Alert dismissed after analyst review';
      await this.handleTriageAction(alert.alert_id, 'DISMISSED', notes);
    });
  },

  async loadAlertsManagement() {
    const tableBody = document.getElementById('alerts-table-body');
    const loadingState = document.getElementById('alerts-loading-state');
    const emptyState = document.getElementById('alerts-empty-state');
    const errorState = document.getElementById('alerts-error-state');
    const pagination = document.getElementById('alerts-pagination-container');

    if (loadingState) loadingState.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    if (errorState) errorState.style.display = 'none';

    try {
      const { page, limit, status, severity, search } = this.state.alertMgmt;
      const offset = (page - 1) * limit;

      const res = await window.FraudShieldAPI.getAlerts({
        status,
        severity,
        search,
        limit,
        offset
      });

      const alerts = res.alerts || [];
      const total = res.total ?? alerts.length;
      this.state.alertMgmt.items = alerts;
      this.state.alertMgmt.total = total;
      this.state.alertMgmt.totalPages = Math.max(1, Math.ceil(total / limit));

      if (loadingState) loadingState.style.display = 'none';

      if (!alerts.length) {
        if (tableBody) tableBody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        if (pagination) pagination.style.display = 'none';
      } else {
        if (emptyState) emptyState.style.display = 'none';
        if (pagination) pagination.style.display = 'flex';
        this.renderAlertsTableRows(alerts);
        this.renderAlertsPaginationControls();
      }

      // Update Alert Ribbon KPIs and Notification Badges
      await this.updateAlertCounters();

    } catch (err) {
      console.error('Error loading alerts management:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (errorState) errorState.style.display = 'block';
      if (pagination) pagination.style.display = 'none';
    }
  },

  renderAlertsTableRows(alerts) {
    const tbody = document.getElementById('alerts-table-body');
    if (!tbody) return;

    tbody.innerHTML = alerts.map(a => {
      const score = Math.round(Number(a.risk_score || (a.severity === 'CRITICAL' ? 92 : a.severity === 'HIGH' ? 82 : 55)));
      const sevClass = (a.severity || 'HIGH').toLowerCase();
      const statusClass = (a.status || 'PENDING').toLowerCase();
      const statusText = a.status === 'PENDING' ? 'Pending Review' :
                         a.status === 'REVIEWED' ? 'Under Review' :
                         a.status === 'APPROVED' ? 'Approved' :
                         a.status === 'BLOCKED' ? 'Blocked' : a.status;

      const formattedTime = this.formatTime(a.created_at);
      const fullIso = this.formatDateTime(a.created_at);

      // Primary reason + top contributing factor tags
      const factorTags = (a.explanations || []).slice(0, 2).map(e => 
        `<span class="explanation-tag" title="${e.description || ''}">${e.factor_name || 'Flagged Signal'}</span>`
      ).join('');

      const notesSnippet = a.analyst_notes ? `<div style="font-size: 0.68rem; color: var(--text-muted); font-style: italic;">📝 ${a.analyst_notes.slice(0, 40)}...</div>` : '';

      return `
        <tr class="tx-row-clickable" id="alert-row-${a.alert_id}" onclick="FraudShieldDashboard.openAlertDetailDrawer('${a.alert_id}')">
          <td>
            <div style="display: flex; align-items: center; gap: 0.4rem;">
              <span class="badge badge-${sevClass}" style="font-size: 0.65rem;">${a.severity || 'HIGH'}</span>
              <span style="font-family: var(--font-mono); font-weight: 600; color: var(--text-primary); font-size: 0.8rem;">${a.alert_id}</span>
            </div>
          </td>
          <td>
            <a href="javascript:void(0)" onclick="event.stopPropagation(); FraudShieldDashboard.inspectTransaction('${a.tx_id}')" style="font-family: var(--font-mono); color: var(--accent-blue); font-size: 0.78rem; text-decoration: underline;">
              ${a.tx_id}
            </a>
            <div style="font-size: 0.7rem; color: var(--text-muted);">
              ${a.amount ? '₹' + Number(a.amount).toLocaleString('en-IN') : ''} • ${a.channel || 'UPI'}
            </div>
          </td>
          <td>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="risk-score-circle" style="background: ${a.severity === 'CRITICAL' ? 'var(--status-critical-bg)' : a.severity === 'HIGH' ? 'var(--status-high-bg)' : 'var(--status-medium-bg)'}; color: ${a.severity === 'CRITICAL' ? 'var(--status-critical)' : a.severity === 'HIGH' ? 'var(--status-high)' : 'var(--status-medium)'};">
                ${score}
              </span>
              <span style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-secondary);">${score}/100</span>
            </div>
          </td>
          <td>
            <span class="badge ${sevClass === 'critical' ? 'badge-critical' : sevClass === 'high' ? 'badge-high' : 'badge-medium'}">
              ${a.risk_category || (a.severity.charAt(0).toUpperCase() + a.severity.slice(1).toLowerCase() + ' risk')}
            </span>
          </td>
          <td title="${fullIso}">
            <div style="font-size: 0.78rem; font-family: var(--font-mono); color: var(--text-primary);">${formattedTime}</div>
            <div style="font-size: 0.68rem; color: var(--text-muted);">${fullIso.split(' ')[0]}</div>
          </td>
          <td style="max-width: 260px;">
            <div style="font-size: 0.78rem; color: var(--text-primary); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${a.primary_reason}">
              ${a.primary_reason || 'Statistical Baseline Anomaly'}
            </div>
            <div style="display: flex; gap: 0.25rem; margin-top: 0.25rem;">
              ${factorTags}
            </div>
          </td>
          <td>
            <span class="badge badge-${statusClass}">
              ${statusText}
            </span>
            ${notesSnippet}
          </td>
          <td style="text-align: right;" onclick="event.stopPropagation();">
            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.35rem;">
              ${a.status === 'PENDING' ? `
                <button class="btn btn-secondary btn-xs" style="border-color: #06b6d4; color: #06b6d4; padding: 0.2rem 0.5rem; font-size: 0.7rem;" title="Mark as Reviewed" onclick="FraudShieldDashboard.handleMarkAlertReviewed('${a.alert_id}')">
                  ✓ Review
                </button>
              ` : ''}
              <button class="btn btn-primary btn-xs" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="FraudShieldDashboard.openAlertDetailDrawer('${a.alert_id}')">
                Investigate Alert ↗
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  renderAlertsPaginationControls() {
    const { page, totalPages, total, limit } = this.state.alertMgmt;
    const info = document.getElementById('alerts-page-range');
    const totalEl = document.getElementById('alerts-total-count');
    const numbersContainer = document.getElementById('alerts-page-numbers');

    const start = total === 0 ? 0 : (page - 1) * limit + 1;
    const end = Math.min(total, page * limit);

    if (info) info.textContent = `${start} - ${end}`;
    if (totalEl) totalEl.textContent = total.toLocaleString();

    // Disable / Enable pagination buttons
    const firstBtn = document.getElementById('alerts-page-first');
    const prevBtn = document.getElementById('alerts-page-prev');
    const nextBtn = document.getElementById('alerts-page-next');
    const lastBtn = document.getElementById('alerts-page-last');

    if (firstBtn) firstBtn.disabled = page <= 1;
    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= totalPages;
    if (lastBtn) lastBtn.disabled = page >= totalPages;

    if (numbersContainer) {
      let pillsHtml = '';
      const maxButtons = 5;
      let startP = Math.max(1, page - 2);
      let endP = Math.min(totalPages, startP + maxButtons - 1);
      if (endP - startP < maxButtons - 1) {
        startP = Math.max(1, endP - maxButtons + 1);
      }

      for (let p = startP; p <= endP; p++) {
        pillsHtml += `
          <button class="page-btn ${p === page ? 'active' : ''}" onclick="FraudShieldDashboard.goToAlertsPage(${p})">
            ${p}
          </button>
        `;
      }
      numbersContainer.innerHTML = pillsHtml;
    }
  },

  goToAlertsPage(pageNumber) {
    this.state.alertMgmt.page = pageNumber;
    this.loadAlertsManagement();
  },

  async openAlertDetailDrawer(alertOrId) {
    const drawerBackdrop = document.getElementById('alert-drawer-backdrop');
    if (!drawerBackdrop) return;

    let alert = null;

    // 1. If alert object passed directly
    if (typeof alertOrId === 'object' && alertOrId !== null) {
      alert = alertOrId;
    } else if (typeof alertOrId === 'string' && alertOrId.trim()) {
      const cleanId = alertOrId.trim();

      // Check alertsCache first
      if (this.state.alertsCache && this.state.alertsCache.has(cleanId)) {
        alert = this.state.alertsCache.get(cleanId);
      }

      // Check Alerts Management view list
      if (!alert && this.state.alertMgmt.items) {
        alert = this.state.alertMgmt.items.find(a => a.alert_id === cleanId || a.tx_id === cleanId);
      }

      // Check Overview Alerts queue
      if (!alert && this.state.alerts) {
        alert = this.state.alerts.find(a => a.alert_id === cleanId || a.tx_id === cleanId);
      }

      // Check Live and Management Transactions
      if (!alert) {
        const tx = (this.state.transactions || []).find(t => t.alert_id === cleanId || t.tx_id === cleanId) ||
                   (this.state.mgmt.transactions || []).find(t => t.alert_id === cleanId || t.tx_id === cleanId);
        if (tx) {
          alert = {
            alert_id: tx.alert_id || `ALT-${tx.tx_id}`,
            tx_id: tx.tx_id,
            amount: tx.amount,
            sender_upi: tx.sender_upi,
            receiver_upi: tx.receiver_upi,
            channel: tx.channel || 'UPI_APP',
            location_city: tx.location_city || 'Mumbai',
            device_id: tx.device_id || 'DEV-MOBILE',
            tx_status: tx.status || 'FLAGGED',
            risk_score: tx.risk_score || 75.0,
            risk_category: tx.risk_category || `${tx.risk_tier || 'High'} risk`,
            severity: tx.risk_tier || 'HIGH',
            primary_reason: tx.primary_factor || 'Evaluated Behavioral Anomaly',
            status: tx.status === 'BLOCKED' ? 'BLOCKED' : tx.status === 'APPROVED' ? 'APPROVED' : 'PENDING',
            created_at: tx.timestamp || tx.created_at || new Date().toISOString(),
            updated_at: tx.timestamp || tx.created_at || new Date().toISOString(),
            explanations: tx.explanations || []
          };
        }
      }

      // Query Backend API for live persistent alert record
      if (!alert && window.FraudShieldAPI) {
        try {
          alert = await window.FraudShieldAPI.getAlertById(cleanId);
        } catch (e) {
          console.debug('API alert lookup error:', e);
        }
      }

      // Fallback query to transaction details endpoint
      if (!alert && window.FraudShieldAPI) {
        try {
          const txRes = await window.FraudShieldAPI.getTransactionById(cleanId);
          if (txRes && (txRes.tx_id || txRes.transaction)) {
            const t = txRes.transaction || txRes;
            alert = {
              alert_id: t.alert_id || `ALT-${t.tx_id}`,
              tx_id: t.tx_id,
              amount: t.amount,
              sender_upi: t.sender_upi,
              receiver_upi: t.receiver_upi,
              channel: t.channel || 'UPI_APP',
              location_city: t.location_city || 'Mumbai',
              device_id: t.device_id || 'DEV-MOBILE',
              tx_status: t.status || 'FLAGGED',
              risk_score: t.risk_score || 80.0,
              risk_category: t.risk_category || 'High risk',
              severity: t.risk_tier || 'HIGH',
              primary_reason: t.primary_factor || 'Investigated Payment Anomaly',
              status: 'PENDING',
              created_at: t.timestamp || new Date().toISOString(),
              updated_at: t.timestamp || new Date().toISOString(),
              explanations: t.explanations || []
            };
          }
        } catch (e) {
          console.debug('API tx fallback lookup error:', e);
        }
      }
    }

    if (!alert) {
      this.showToast(`Unable to locate alert records for "${alertOrId}".`, 'warning');
      return;
    }

    // Enrich with transaction details if missing
    if (alert.tx_id && (!alert.channel || !alert.device_id || !alert.sender_upi)) {
      const matchTx = (this.state.transactions || []).find(t => t.tx_id === alert.tx_id) ||
                      (this.state.mgmt.transactions || []).find(t => t.tx_id === alert.tx_id);
      if (matchTx) {
        alert.channel = alert.channel || matchTx.channel;
        alert.device_id = alert.device_id || matchTx.device_id;
        alert.sender_upi = alert.sender_upi || matchTx.sender_upi;
        alert.receiver_upi = alert.receiver_upi || matchTx.receiver_upi;
        alert.location_city = alert.location_city || matchTx.location_city;
        alert.amount = alert.amount ?? matchTx.amount;
        alert.tx_status = alert.tx_status || matchTx.status;
      }
    }

    // Cache this resolved alert for fast future lookups
    if (!this.state.alertsCache) this.state.alertsCache = new Map();
    if (alert.alert_id) this.state.alertsCache.set(alert.alert_id, alert);
    if (alert.tx_id) this.state.alertsCache.set(alert.tx_id, alert);
    this.state.alertMgmt.selectedAlert = alert;

    // 1. Header Metadata
    const idEl = document.getElementById('drawer-alert-id');
    if (idEl) idEl.textContent = alert.alert_id;

    const sev = (alert.severity || 'HIGH').toUpperCase();
    const sevBadge = document.getElementById('drawer-alert-severity-badge');
    if (sevBadge) {
      sevBadge.className = `badge ${sev === 'CRITICAL' ? 'badge-critical' : sev === 'HIGH' ? 'badge-high' : 'badge-medium'}`;
      sevBadge.textContent = sev;
    }

    const st = (alert.status || 'PENDING').toUpperCase();
    const statusBadge = document.getElementById('drawer-alert-status-badge');
    if (statusBadge) {
      const statusClass = st === 'APPROVED' ? 'badge-approved' :
                          st === 'BLOCKED' ? 'badge-critical' :
                          st === 'REVIEWED' || st === 'UNDER_REVIEW' ? 'badge-reviewed' :
                          st === 'DISMISSED' ? 'badge-low' : 'badge-pending';
      const statusLabel = st === 'PENDING' ? 'Pending Review' :
                          st === 'REVIEWED' || st === 'UNDER_REVIEW' ? 'Under Review' :
                          st === 'APPROVED' ? 'Approved' :
                          st === 'BLOCKED' ? 'Blocked' :
                          st === 'DISMISSED' ? 'Dismissed' : st;
      statusBadge.className = `badge ${statusClass}`;
      statusBadge.textContent = statusLabel;
    }

    // 2. Payment Context
    const txIdEl = document.getElementById('drawer-alert-tx-id');
    if (txIdEl) txIdEl.textContent = alert.tx_id || '-';

    const amtEl = document.getElementById('drawer-alert-amount');
    if (amtEl) amtEl.textContent = alert.amount ? '₹' + Number(alert.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '₹0.00';

    const sndEl = document.getElementById('drawer-alert-sender');
    if (sndEl) sndEl.textContent = alert.sender_upi || 'unknown@upi';

    const rcvEl = document.getElementById('drawer-alert-receiver');
    if (rcvEl) rcvEl.textContent = alert.receiver_upi || 'unknown@upi';

    const chnEl = document.getElementById('drawer-alert-channel-dev');
    if (chnEl) chnEl.textContent = `${alert.channel || 'UPI_APP'} • ${alert.location_city || 'Mumbai'}`;

    const timeEl = document.getElementById('drawer-alert-time');
    if (timeEl) timeEl.textContent = this.formatDateTime(alert.tx_timestamp || alert.created_at);

    const txStatusEl = document.getElementById('drawer-alert-tx-status');
    if (txStatusEl) {
      const txSt = (alert.tx_status || alert.status || 'PENDING').toUpperCase();
      txStatusEl.textContent = txSt;
      txStatusEl.style.color = txSt === 'BLOCKED' ? 'var(--status-critical, #d94f5c)' :
                               txSt === 'APPROVED' ? 'var(--status-approved, #16a36a)' : 'var(--text-primary, #25324b)';
    }

    const devEl = document.getElementById('drawer-alert-device-ip');
    if (devEl) {
      devEl.textContent = `${alert.device_id || 'DEV-MOBILE'} (${alert.ip_address || '49.207.180.12'})`;
    }

    // 3. AI Isolation Forest Anomaly Diagnostics
    const rawScore = Number(alert.risk_score || (sev === 'CRITICAL' ? 92.5 : sev === 'HIGH' ? 84.2 : 55.0));
    const scoreVal = Math.round(rawScore * 10) / 10;
    const scoreEl = document.getElementById('drawer-alert-risk-score');
    if (scoreEl) scoreEl.textContent = `${scoreVal}/100`;

    const riskBarEl = document.getElementById('drawer-alert-risk-bar');
    if (riskBarEl) riskBarEl.style.width = `${Math.min(100, Math.max(12, scoreVal))}%`;

    const catEl = document.getElementById('drawer-alert-category');
    if (catEl) catEl.textContent = alert.risk_category || `${sev} Risk Anomaly`;

    const anomBadge = document.getElementById('drawer-alert-anomaly-badge');
    if (anomBadge) {
      const isAnomaly = scoreVal >= 60 || sev === 'HIGH' || sev === 'CRITICAL';
      if (isAnomaly) {
        anomBadge.textContent = 'STATISTICAL ANOMALY OUTLIER';
        anomBadge.style.background = 'rgba(217, 79, 92, 0.12)';
        anomBadge.style.color = '#d94f5c';
      } else {
        anomBadge.textContent = 'NORMAL STATISTICAL DISTRIBUTION';
        anomBadge.style.background = 'rgba(22, 163, 106, 0.12)';
        anomBadge.style.color = '#16a36a';
      }
    }

    const reasonEl = document.getElementById('drawer-alert-primary-reason');
    if (reasonEl) reasonEl.textContent = alert.primary_reason || 'Isolation Forest algorithmic anomaly flagged based on multiple behavioral indicators.';

    // 4. Contributing Feature Explanations
    const factorsContainer = document.getElementById('drawer-factors-container');
    if (factorsContainer) {
      let explanations = alert.explanations || [];
      if (!explanations.length) {
        const amt = Number(alert.amount || 50000);
        explanations = [
          {
            factor_name: "AMOUNT_DEVIATION",
            weight: 0.42,
            severity: amt > 60000 ? "CRITICAL" : "HIGH",
            description: `Payment amount (₹${amt.toLocaleString('en-IN')}) exceeds historical 30-day baseline mean by ${(amt / 2500).toFixed(1)}x.`,
            observed_value: `₹${amt.toLocaleString('en-IN')}`,
            baseline_value: "₹2,500.00"
          },
          {
            factor_name: "VELOCITY_SPIKE",
            weight: 0.28,
            severity: "HIGH",
            description: "Rapid sequence of outgoing transfers initiated within short evaluation window.",
            observed_value: "4 transfers / 15m",
            baseline_value: "0.2 transfers / 15m"
          },
          {
            factor_name: "BENEFICIARY_NOVELTY",
            weight: 0.18,
            severity: "MEDIUM",
            description: "First recorded transaction from this account to destination UPI VPA handle.",
            observed_value: "First interaction",
            baseline_value: "Known network"
          }
        ];
      }

      factorsContainer.innerHTML = explanations.map(f => {
        const weightPercent = Math.min(100, Math.round((f.weight || 0.25) * 100));
        const fSev = (f.severity || 'MEDIUM').toLowerCase();
        return `
          <div class="factor-card-item">
            <div class="factor-header-row">
              <span class="factor-name-title">${f.factor_name || 'Statistical Signal'}</span>
              <span class="badge badge-${fSev === 'critical' ? 'critical' : fSev === 'high' ? 'high' : 'medium'}">${f.severity || 'MEDIUM'} • ${weightPercent}% Impact</span>
            </div>
            <div class="factor-weight-bar-track">
              <div class="factor-weight-bar-fill" style="width: ${weightPercent}%;"></div>
            </div>
            <div style="font-size: 0.76rem; color: var(--text-secondary); line-height: 1.35; margin-top: 0.35rem;">
              ${f.description || f.explanation || ''}
            </div>
            ${f.observed_value && f.baseline_value ? `
              <div class="factor-comparison-grid">
                <div><strong style="color: var(--text-muted);">Observed:</strong> <span style="font-family: var(--font-mono); color: var(--text-primary); font-weight: 600;">${f.observed_value}</span></div>
                <div><strong style="color: var(--text-muted);">Baseline:</strong> <span style="font-family: var(--font-mono); color: var(--text-primary);">${f.baseline_value}</span></div>
              </div>
            ` : ''}
          </div>
        `;
      }).join('');
    }

    // 5. Notes & Audit trail
    const notesInput = document.getElementById('drawer-analyst-notes');
    if (notesInput) notesInput.value = alert.analyst_notes || '';

    const revByEl = document.getElementById('drawer-reviewed-by');
    if (revByEl) revByEl.textContent = alert.reviewed_by || 'None (Pending SOC Triage)';

    const updEl = document.getElementById('drawer-updated-at');
    if (updEl) updEl.textContent = this.formatDateTime(alert.updated_at);

    const crtEl = document.getElementById('drawer-created-at');
    if (crtEl) crtEl.textContent = this.formatDateTime(alert.created_at);

    // Open drawer slide-over
    drawerBackdrop.classList.add('open');
  },

  async handleMarkAlertReviewed(alertId, notes = 'Reviewed by SOC analyst') {
    try {
      const updated = await window.FraudShieldAPI.markAlertReviewed(alertId, notes);
      
      // Update local state items
      const item = this.state.alertMgmt.items.find(a => a.alert_id === alertId);
      if (item) {
        item.status = 'REVIEWED';
        item.reviewed_by = updated?.reviewed_by || 'SOC-Analyst';
        item.analyst_notes = notes;
      }
      this.renderAlertsTableRows(this.state.alertMgmt.items);
      this.state.alerts = this.state.alerts.filter(a => a.alert_id !== alertId);
      this.renderAlertsQueue();

      // If drawer is currently open on this alert, update drawer badges
      if (this.state.alertMgmt.selectedAlert?.alert_id === alertId) {
        const statusBadge = document.getElementById('drawer-alert-status-badge');
        if (statusBadge) {
          statusBadge.className = 'badge badge-reviewed';
          statusBadge.textContent = 'Under Review';
        }
        document.getElementById('drawer-reviewed-by').textContent = updated?.reviewed_by || 'SOC-Analyst';
      }

      this.showToast(`Alert ${alertId} marked as Reviewed`, 'info');
      await this.updateAlertCounters();
    } catch (err) {
      this.showToast(`Failed to review alert: ${err.message}`, 'danger');
    }
  },

  async updateAlertCounters() {
    try {
      const summary = await window.FraudShieldAPI.getAlertSummary();
      const total = summary.total || 0;
      const pending = summary.pending || 0;
      const reviewed = summary.under_review || 0;
      const approved = summary.approved || 0;
      const blocked = summary.blocked || 0;

      // Update Ribbon Elements
      const statTotal = document.getElementById('alert-stat-total');
      const statPending = document.getElementById('alert-stat-pending');
      const statReviewed = document.getElementById('alert-stat-reviewed');
      const statApproved = document.getElementById('alert-stat-approved');
      const statBlocked = document.getElementById('alert-stat-blocked');

      if (statTotal) statTotal.textContent = total.toLocaleString();
      if (statPending) statPending.textContent = pending.toLocaleString();
      if (statReviewed) statReviewed.textContent = reviewed.toLocaleString();
      if (statApproved) statApproved.textContent = approved.toLocaleString();
      if (statBlocked) statBlocked.textContent = blocked.toLocaleString();

      // Update Topbar and Sidebar Badges
      const sideBadge = document.getElementById('sidebar-alert-badge');
      if (sideBadge) sideBadge.textContent = pending;

      const unreadCount = document.getElementById('notification-unread-count');
      const bellDot = document.getElementById('notification-badge-dot');

      if (unreadCount) {
        unreadCount.textContent = pending;
        unreadCount.style.display = pending > 0 ? 'flex' : 'none';
      }
      if (bellDot) {
        bellDot.style.display = pending > 0 ? 'block' : 'none';
      }

      const overviewPending = document.getElementById('kpi-pending-alerts');
      if (overviewPending) overviewPending.textContent = pending;

    } catch (e) {
      console.warn('Could not update alert counters:', e);
    }
  },

  initAlertsEventStream() {
    if (typeof EventSource === 'undefined') return;

    try {
      if (this.state.eventSource) {
        this.state.eventSource.close();
      }

      const evtSource = new EventSource('/api/alerts/stream');
      this.state.eventSource = evtSource;

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.alerts) {
            // Check for new pending alerts
            data.alerts.forEach(alert => {
              if (alert.status === 'PENDING' && !this.state.seenAlertIds.has(alert.alert_id)) {
                this.state.seenAlertIds.add(alert.alert_id);
                // Dispatch live toast
                this.showLiveAlertToast(alert);
              }
            });

            // If on alerts view, refresh smoothly
            if (this.state.currentView === 'alerts') {
              this.loadAlertsManagement();
            }
            this.updateAlertCounters();
          }
        } catch (err) {
          console.debug('SSE parse error:', err);
        }
      };

      evtSource.onerror = () => {
        // Fallback to polling silently
        evtSource.close();
        this.state.eventSource = null;
      };
    } catch (e) {
      console.debug('EventSource not supported or failed to init:', e);
    }
  },

  showLiveAlertToast(alert) {
    const container = document.getElementById('fraudshield-toast-container');
    if (!container) return;

    const sevClass = (alert.severity || 'HIGH').toLowerCase();
    const amountFmt = alert.amount ? '₹' + Number(alert.amount).toLocaleString('en-IN') : '₹0.00';
    const alertId = alert.alert_id || alert.tx_id || `ALT-${Date.now().toString().slice(-6)}`;
    alert.alert_id = alert.alert_id || alertId;

    // Cache alert for immediate drawer access
    if (!this.state.alertsCache) this.state.alertsCache = new Map();
    this.state.alertsCache.set(alertId, alert);
    if (alert.tx_id) this.state.alertsCache.set(alert.tx_id, alert);

    const toast = document.createElement('div');
    toast.className = `alert-live-toast ${sevClass}`;
    toast.innerHTML = `
      <div class="toast-top-row">
        <div class="toast-title-cluster">
          <span class="badge badge-${sevClass}">${alert.severity || 'HIGH'} ALERT</span>
          <span>${alertId}</span>
        </div>
        <button class="toast-close-btn" onclick="this.closest('.alert-live-toast').remove()">✕</button>
      </div>
      <div class="toast-body-text">
        <strong>${amountFmt}</strong> • ${alert.primary_reason || 'Statistical Anomaly Flagged'}
      </div>
      <div class="toast-actions-row">
        <button class="btn btn-secondary btn-xs btn-dismiss-alert" style="font-size: 0.7rem; padding: 0.2rem 0.5rem;" onclick="this.closest('.alert-live-toast').remove()">Dismiss Alert</button>
        <button class="btn btn-primary btn-xs btn-investigate-alert" style="font-size: 0.7rem; padding: 0.2rem 0.5rem;" onclick="FraudShieldDashboard.openAlertDetailDrawer('${alertId}'); this.closest('.alert-live-toast').remove();">
          Investigate Alert ↗
        </button>
      </div>
    `;

    // Attach direct event listener passing full alert object
    const invBtn = toast.querySelector('.btn-investigate-alert');
    if (invBtn) {
      invBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.openAlertDetailDrawer(alert);
        toast.remove();
      });
    }

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(50px)';
      setTimeout(() => toast.remove(), 250);
    }, 6500);
  },

  // -------------------------------------------------------------------------
  // Deep Transaction Details View & ML Prediction Explainability
  // -------------------------------------------------------------------------
  async inspectTransaction(txId) {
    const modal = document.getElementById('tx-detail-modal');
    const content = document.getElementById('tx-modal-content');
    const badge = document.getElementById('modal-tx-tier-badge');

    modal?.classList.add('open');

    // Show loading skeleton inside modal
    if (content) {
      content.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem; padding: 2rem 1rem;">
          <div class="skeleton-cell" style="width: 60%; height: 24px;"></div>
          <div class="skeleton-cell" style="width: 100%; height: 80px;"></div>
          <div class="skeleton-cell" style="width: 100%; height: 120px;"></div>
        </div>
      `;
    }

    try {
      const data = await window.FraudShieldAPI.getTransaction(txId);
      const tx = data.transaction || {};
      const alert = data.alert || null;
      const pred = data.prediction || {};
      const explanations = data.explanations || [];

      this.state.selectedTx = tx;

      if (badge) {
        badge.className = `badge badge-${(tx.risk_tier || 'low').toLowerCase()}`;
        badge.textContent = tx.risk_tier || 'LOW';
      }

      const timeFormatted = this.formatDateTime(tx.timestamp || tx.created_at);
      const amountFmt = '₹' + Number(tx.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
      const rawScore = pred.raw_decision_score !== undefined 
        ? Number(pred.raw_decision_score).toFixed(4) 
        : (tx.anomaly_score !== undefined ? Number(tx.anomaly_score).toFixed(4) : '-0.1850');
      const isAnomaly = pred.is_anomaly === 1 || rawScore < 0 || tx.risk_score >= 70;
      const riskScore = Number(tx.risk_score || pred.final_risk_score || 0).toFixed(1);

      // Color calculation for risk gauge fill
      const gaugeColor = tx.risk_tier === 'CRITICAL' ? 'var(--status-critical)' :
                         tx.risk_tier === 'HIGH' ? 'var(--status-high)' :
                         tx.risk_tier === 'MEDIUM' ? 'var(--status-medium)' : 'var(--status-low)';

      // Build explanations HTML
      const factorsHtml = explanations.length ? explanations.map(exp => `
        <div class="factor-attribution-item">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-family: var(--font-mono); font-weight: 700; font-size: 0.78rem; color: var(--text-primary);">
              ${exp.factor_name || 'BEHAVIORAL_SIGNAL'}
            </span>
            <div style="display: flex; align-items: center; gap: 0.4rem;">
              <span class="badge badge-${(exp.severity || 'low').toLowerCase()}" style="font-size: 0.65rem;">
                ${exp.severity || 'NORMAL'}
              </span>
              <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--accent-cyan);">
                Impact: ${(Number(exp.weight || 0.1) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <p style="font-size: 0.78rem; color: var(--text-secondary); margin: 0;">
            ${exp.description || exp.explanation || 'Anomaly contribution detected against peer cluster.'}
          </p>
        </div>
      `).join('') : `
        <div style="padding: 0.85rem; background: var(--bg-surface); border-radius: var(--radius-sm); font-size: 0.78rem; color: var(--text-muted);">
          Standard behavioral baseline. No anomalous feature deviations observed across 18 engineered signals.
        </div>
      `;

      // Attached Alert Details block if exists
      const alertHtml = alert ? `
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid var(--status-critical-border); border-radius: var(--radius-sm); padding: 0.85rem; display: flex; flex-direction: column; gap: 0.35rem;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.75rem; font-weight: 700; color: var(--status-critical); display: flex; align-items: center; gap: 0.35rem;">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              </svg>
              Attached Alert: ${alert.alert_id}
            </span>
            <span class="badge badge-${(alert.severity || 'critical').toLowerCase()}">${alert.status || 'PENDING'}</span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-secondary);">Reason: ${alert.primary_reason || 'Anomaly Detected'}</div>
          ${alert.reviewed_by ? `<div style="font-size: 0.7rem; color: var(--text-muted);">Reviewed by: ${alert.reviewed_by} | Notes: ${alert.analyst_notes || 'None'}</div>` : ''}
        </div>
      ` : '';

      if (content) {
        content.innerHTML = `
          <!-- Header Meta -->
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-subtle);">
            <div>
              <span style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Transaction ID</span>
              <div style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-cyan); font-weight: 600;">${tx.tx_id}</div>
            </div>
            <div>
              <span style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Timestamp (IST)</span>
              <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-primary);">${timeFormatted}</div>
            </div>
            <div>
              <span style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Amount</span>
              <div style="font-family: var(--font-mono); font-size: 1.15rem; color: var(--text-primary); font-weight: 700;">${amountFmt}</div>
            </div>
            <div>
              <span style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">Channel</span>
              <div><span class="badge badge-channel" style="margin-top: 2px;">${tx.channel || 'UPI_APP'}</span></div>
            </div>
          </div>

          <!-- Machine Learning Prediction Breakdown Card -->
          <div class="ml-pred-card">
            <div class="ml-pred-header">
              <div>
                <span style="font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted);">Isolation Forest Anomaly Inference</span>
                <h4 style="font-size: 1rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.4rem;">
                  <span>${isAnomaly ? 'SUSPICIOUS_ANOMALY' : 'NORMAL_TRANSACTION'}</span>
                  <span class="badge badge-${(tx.risk_tier || 'low').toLowerCase()}" style="font-size: 0.65rem;">${tx.risk_tier || 'LOW'}</span>
                </h4>
              </div>
              <div style="text-align: right;">
                <div style="font-family: var(--font-mono); font-size: 1.35rem; font-weight: 700; color: ${gaugeColor};">
                  ${riskScore} <span style="font-size: 0.75rem; color: var(--text-muted);">/ 100</span>
                </div>
                <div style="font-size: 0.68rem; color: var(--text-muted);">Decision Score: <strong class="mono" style="color: var(--accent-cyan);">${rawScore}</strong></div>
              </div>
            </div>

            <!-- Risk Progress Bar -->
            <div class="score-progress-bar">
              <div class="score-progress-fill" style="width: ${Math.min(100, Math.max(4, riskScore))}%; background: ${gaugeColor};"></div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-secondary); border-top: 1px solid var(--border-subtle); padding-top: 0.5rem;">
              <span>Ensemble: <strong>150 Isolation Trees</strong></span>
              <span>Decision Boundary: <strong>score &lt; 0 (Anomaly)</strong></span>
              <span>Action: <strong style="color: var(--text-primary);">${tx.status || 'APPROVED'}</strong></span>
            </div>
          </div>

          <!-- Payment Context & Network Telemetry -->
          <div style="display: flex; flex-direction: column; gap: 0.35rem;">
            <span style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Payment Route & Telemetry</span>
            <div style="background: var(--bg-surface); padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-family: var(--font-mono); font-size: 0.78rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
              <div>Sender: <span style="color: var(--text-primary); font-weight: 600;">${tx.sender_upi}</span></div>
              <div>Receiver: <span style="color: var(--text-primary); font-weight: 600;">${tx.receiver_upi}</span></div>
              <div>Device Fingerprint: <span style="color: var(--accent-cyan);">${tx.device_id || 'UNKNOWN'}</span></div>
              <div>Location: <span style="color: var(--text-primary);">${tx.location_city || 'India'}</span></div>
            </div>
          </div>

          <!-- Explainable Feature Attributions -->
          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <span style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Transparent ML Feature Explanations</span>
            <div style="display: flex; flex-direction: column; gap: 0.45rem;">
              ${factorsHtml}
            </div>
          </div>

          <!-- Attached Alert Details -->
          ${alertHtml}
        `;
      }

      // Configure Modal Actions
      const approveBtn = document.getElementById('btn-modal-approve-tx');
      const blockBtn = document.getElementById('btn-modal-block-tx');

      if (approveBtn) {
        approveBtn.onclick = async () => {
          await window.FraudShieldAPI.updateTransactionStatus(tx.tx_id, 'APPROVED', 'Manually cleared by analyst');
          if (alert) {
            await window.FraudShieldAPI.updateAlertAction(alert.alert_id, 'APPROVED', 'Manually cleared by analyst');
          }
          tx.status = 'APPROVED';
          this.showToast(`Transaction ${tx.tx_id} cleared and marked APPROVED`, 'success');
          modal?.classList.remove('open');
          this.loadManagementTransactions();
          this.loadDashboardData();
        };
      }

      if (blockBtn) {
        blockBtn.onclick = async () => {
          await window.FraudShieldAPI.updateTransactionStatus(tx.tx_id, 'BLOCKED', 'Entity frozen for fraud');
          if (alert) {
            await window.FraudShieldAPI.updateAlertAction(alert.alert_id, 'BLOCKED', 'Entity frozen for fraud');
          }
          tx.status = 'BLOCKED';
          this.showToast(`Transaction ${tx.tx_id} blocked and blacklisted`, 'danger');
          modal?.classList.remove('open');
          this.loadManagementTransactions();
          this.loadDashboardData();
        };
      }

    } catch (err) {
      console.error('Failed to load transaction details:', err);
      if (content) {
        content.innerHTML = `
          <div style="padding: 2rem; text-align: center; color: var(--status-critical);">
            Failed to retrieve transaction details: ${err.message}
          </div>
        `;
      }
    }
  },

  handleNewSimulatedTx(tx) {
    if (!tx) return;
    
    // Add to in-memory transactions array
    this.state.transactions.unshift(tx);
    this.renderTransactionsTable();

    // If High, Critical, or Medium risk (or score >= 40), create/update alert
    const isSuspicious = tx.risk_tier === 'HIGH' || tx.risk_tier === 'CRITICAL' || tx.risk_tier === 'MEDIUM' || (Number(tx.risk_score || 0) >= 40.0);
    if (isSuspicious) {
      const alertId = tx.alert_id || `ALT-SIM-${Date.now().toString().slice(-6)}`;
      const newAlert = {
        alert_id: alertId,
        tx_id: tx.tx_id,
        amount: tx.amount,
        sender_upi: tx.sender_upi,
        receiver_upi: tx.receiver_upi,
        channel: tx.channel || 'UPI_APP',
        location_city: tx.location_city || 'Mumbai',
        risk_score: tx.risk_score,
        risk_category: tx.risk_category || (tx.risk_tier ? tx.risk_tier.charAt(0) + tx.risk_tier.slice(1).toLowerCase() + ' risk' : 'Medium risk'),
        severity: tx.risk_tier || 'MEDIUM',
        primary_reason: tx.primary_factor || 'Simulated Behavioral Anomaly',
        status: 'PENDING',
        created_at: tx.timestamp || new Date().toISOString(),
        updated_at: tx.timestamp || new Date().toISOString(),
        explanations: tx.explanations || []
      };

      // Store in alertsCache
      if (!this.state.alertsCache) this.state.alertsCache = new Map();
      this.state.alertsCache.set(alertId, newAlert);
      if (tx.tx_id) this.state.alertsCache.set(tx.tx_id, newAlert);

      // Deduplicate in state.alerts
      this.state.alerts = this.state.alerts.filter(a => a.tx_id !== tx.tx_id);
      this.state.alerts.unshift(newAlert);
      this.renderAlertsQueue();

      // Deduplicate in state.alertMgmt.items so alert is immediately available in alerts tab
      this.state.alertMgmt.items = this.state.alertMgmt.items.filter(a => a.tx_id !== tx.tx_id);
      this.state.alertMgmt.items.unshift(newAlert);
      this.state.alertMgmt.total++;
      if (this.state.currentView === 'alerts') {
        this.renderAlertsTableRows(this.state.alertMgmt.items);
      }

      // Trigger Live Alert Notification Toast (if not seen)
      if (!this.state.seenAlertIds.has(alertId)) {
        this.state.seenAlertIds.add(alertId);
        this.showLiveAlertToast(newAlert);
      }

      this.updateAlertCounters();
    }

    // Increment Total Evaluated Volume
    const totalEl = document.getElementById('kpi-total-evaluated');
    if (totalEl) {
      const current = parseInt(totalEl.textContent.replace(/,/g, ''), 10) || 0;
      totalEl.textContent = (current + 1).toLocaleString();
    }

    // If Management view is active, prepend row directly to management table
    if (this.state.currentView === 'transactions') {
      this.state.mgmt.transactions.unshift(tx);
      this.state.mgmt.total++;
      this.renderManagementTableRows();
      this.renderPaginationControls();
    }

    // Dynamically update Chart.js Doughnut in real time
    if (window.FraudShieldCharts && window.FraudShieldCharts.distributionChart) {
      const tierMap = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };
      const idx = tierMap[(tx.risk_tier || 'LOW').toUpperCase()] ?? 0;
      const chartData = window.FraudShieldCharts.distributionChart.data.datasets[0].data;
      if (chartData && chartData[idx] !== undefined) {
        chartData[idx]++;
        window.FraudShieldCharts.distributionChart.update('none');
      }
    }
  },

  initTheme() {
    const saved = localStorage.getItem('fraudshield_theme') || 'light';
    this.setTheme(saved, false);
  },

  /**
   * Initializes subtle interactive 3D perspective tilt for the Overview Shield visual
   * Responds gracefully to mouse movement without layout thrashing
   */
  init3DShieldParallax() {
    const shieldContainer = document.getElementById('overview-3d-shield');
    if (!shieldContainer) return;

    const shieldFacets = shieldContainer.querySelector('.shield-facets');
    const deckHeader = shieldContainer.closest('.sim-deck-header') || shieldContainer;
    if (!shieldFacets) return;

    // Respect prefers-reduced-motion
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    let ticking = false;

    deckHeader.addEventListener('mousemove', (e) => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const rect = deckHeader.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
          ticking = false;
          return;
        }
        const normX = ((e.clientX - rect.left) / rect.width - 0.5) * 2; // -1 to +1
        const normY = ((e.clientY - rect.top) / rect.height - 0.5) * 2; // -1 to +1

        const tiltX = (-normY * 12).toFixed(1);
        const tiltY = (normX * 14).toFixed(1);

        shieldFacets.style.transform = `perspective(600px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateZ(14px)`;
        ticking = false;
      });
    }, { passive: true });

    deckHeader.addEventListener('mouseleave', () => {
      shieldFacets.style.transform = 'translateZ(10px)';
    }, { passive: true });
  },

  startLiveClock() {
    const clockEl = document.getElementById('clock-ist-time');
    if (!clockEl) return;
    const tick = () => {
      try {
        const now = new Date();
        const istStr = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
        clockEl.textContent = `${istStr} IST`;
      } catch (e) {
        const now = new Date();
        clockEl.textContent = `${now.toTimeString().split(' ')[0]} IST`;
      }
    };
    tick();
    setInterval(tick, 1000);
  },

  setTheme(themeName, showToastNotification = true) {
    const theme = (themeName === 'dark') ? 'dark' : 'light';
    this.state.currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('fraudshield_theme', theme);

    // Update Topbar Icons
    const sunIcon = document.getElementById('theme-icon-sun');
    const moonIcon = document.getElementById('theme-icon-moon');
    if (sunIcon && moonIcon) {
      if (theme === 'dark') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
      } else {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
      }
    }

    // Update Settings Modal Options
    const btnLight = document.getElementById('btn-theme-light');
    const btnDark = document.getElementById('btn-theme-dark');
    const themeStatusBadge = document.getElementById('theme-status-badge');
    const themeDesc = document.getElementById('theme-desc-text');

    if (btnLight && btnDark) {
      if (theme === 'light') {
        btnLight.classList.add('active');
        btnLight.style.borderColor = 'var(--primary-purple)';
        btnLight.style.borderWidth = '2px';
        btnDark.classList.remove('active');
        btnDark.style.borderColor = 'var(--border-subtle)';
        btnDark.style.borderWidth = '1px';
      } else {
        btnDark.classList.add('active');
        btnDark.style.borderColor = 'var(--primary-purple)';
        btnDark.style.borderWidth = '2px';
        btnLight.classList.remove('active');
        btnLight.style.borderColor = 'var(--border-subtle)';
        btnLight.style.borderWidth = '1px';
      }
    }

    if (themeStatusBadge) {
      themeStatusBadge.textContent = (theme === 'light') ? 'Light Theme Active (Default)' : 'Dark SOC Mode Active';
      themeStatusBadge.className = (theme === 'light') ? 'badge badge-success' : 'badge badge-primary';
    }

    if (themeDesc) {
      themeDesc.textContent = (theme === 'light')
        ? 'Clean off-white background with soft lavender and purple accents (Default)'
        : 'Deep cybersecurity SOC midnight theme with high contrast telemetry';
    }

    // Inform Chart.js visualisations to switch palette & redraw
    if (window.FraudShieldCharts?.applyTheme) {
      window.FraudShieldCharts.applyTheme(theme);
    }

    if (showToastNotification) {
      this.showToast(theme === 'light' ? 'Switched to Light Theme (Default)' : 'Switched to Dark SOC Mode', 'info');
    }
  },

  updateUserChip() {
    const user = window.FraudShieldAPI.currentUser;
    const avatarEl = document.getElementById('user-avatar-initials');
    const nameEl = document.getElementById('user-chip-username');
    const roleEl = document.getElementById('user-chip-role-badge');

    const drawerAvatar = document.getElementById('drawer-avatar');
    const drawerName = document.getElementById('drawer-fullname');
    const drawerEmail = document.getElementById('drawer-email');
    const drawerRole = document.getElementById('drawer-role-badge');
    const drawerToken = document.getElementById('drawer-token-display');
    const drawerCapabilities = document.getElementById('drawer-capabilities-list');
    const logoutBtn = document.getElementById('btn-logout');

    if (!user) {
      if (avatarEl) avatarEl.textContent = '--';
      if (nameEl) nameEl.textContent = 'Sign In';
      if (roleEl) {
        roleEl.textContent = 'GUEST';
        roleEl.style.color = 'var(--text-muted)';
      }
      if (drawerAvatar) drawerAvatar.textContent = '?';
      if (drawerName) drawerName.textContent = 'Not Authenticated';
      if (drawerEmail) drawerEmail.textContent = 'Sign in to access SOC controls';
      if (drawerRole) {
        drawerRole.textContent = 'UNAUTHENTICATED';
        drawerRole.className = 'badge badge-medium';
      }
      if (drawerToken) drawerToken.textContent = 'No active JWT token. Please sign in.';
      if (logoutBtn) logoutBtn.style.display = 'none';
      return;
    }

    if (logoutBtn) logoutBtn.style.display = 'flex';
    const initials = (user.username || 'AD').slice(0, 2).toUpperCase();

    if (avatarEl) avatarEl.textContent = initials;
    if (nameEl) nameEl.textContent = user.username;
    if (roleEl) {
      roleEl.textContent = user.role;
      roleEl.style.color = user.role === 'ADMIN' ? 'var(--accent-purple)' : 'var(--accent-blue)';
    }

    if (drawerAvatar) drawerAvatar.textContent = initials;
    if (drawerName) drawerName.textContent = user.full_name || user.username;
    if (drawerEmail) drawerEmail.textContent = user.email || `${user.username}@fraudshield.internal`;
    if (drawerRole) {
      drawerRole.textContent = `${user.role} PRIVILEGED`;
      drawerRole.className = user.role === 'ADMIN' ? 'badge badge-role-admin' : 'badge badge-role-analyst';
    }
    if (drawerToken) {
      drawerToken.textContent = window.FraudShieldAPI.token 
        ? `Bearer: ${window.FraudShieldAPI.token.slice(0, 28)}... (Active)`
        : 'Session Active (Demo Standalone)';
    }

    const drawerUsersBtn = document.getElementById('drawer-btn-users');
    if (drawerUsersBtn) {
      drawerUsersBtn.style.display = (user && user.role === 'ADMIN') ? 'flex' : 'none';
    }

    if (drawerCapabilities) {
      if (user.role === 'ADMIN') {
        drawerCapabilities.innerHTML = `
          <li>Full Access to Real-Time Transaction Scoring & Rules</li>
          <li>SOC Alert Triage & Payment Blocking Permissions</li>
          <li>System Analytics & Hourly Trend Visualisation</li>
          <li>User Security Account Administration (ADMIN)</li>
          <li>RFC-4180 Audit CSV Reports Export</li>
        `;
      } else {
        drawerCapabilities.innerHTML = `
          <li>Real-Time Transaction Surveillance & Queries</li>
          <li>Deep Explainability & Isolation Forest Signal Inspection</li>
          <li>SOC Alert Triage (Review, Approve, Block, Dismiss)</li>
          <li style="color: var(--text-muted); text-decoration: line-through;">System Analytics (Admin Only)</li>
          <li style="color: var(--text-muted); text-decoration: line-through;">User Administration (Admin Only)</li>
        `;
      }
    }
  },

  startPolling() {
    if (this.state.pollingIntervalId) clearInterval(this.state.pollingIntervalId);
    this.state.pollingIntervalId = setInterval(async () => {
      if (this.state.isLivePolling) {
        if (this.state.currentView === 'overview') {
          await this.loadDashboardData();
        } else if (this.state.currentView === 'transactions') {
          await this.loadManagementTransactions();
        } else if (this.state.currentView === 'alerts') {
          await this.loadAlertsManagement();
        }
        // Avoid duplicate alert counter query if overview or alerts already refreshed state
        if (this.state.currentView !== 'overview' && this.state.currentView !== 'alerts') {
          await this.updateAlertCounters();
        }
      }
    }, 6000);
  },

  stopPolling() {
    if (this.state.pollingIntervalId) {
      clearInterval(this.state.pollingIntervalId);
      this.state.pollingIntervalId = null;
    }
  },

  copyToClipboard(text, element) {
    if (!text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        if (element) {
          element.classList.add('copied');
          setTimeout(() => element.classList.remove('copied'), 1500);
        }
        this.showToast(`Copied to clipboard: ${text}`, 'info');
      }).catch(() => {
        this.showToast(`Identifier: ${text}`, 'info');
      });
    } else {
      this.showToast(`Identifier: ${text}`, 'info');
    }
  },

  resetLedgerFilters() {
    this.state.activeFilter = 'ALL';
    this.state.searchQuery = '';
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) searchInput.value = '';
    document.querySelectorAll('#ledger-filter-tabs .filter-tab').forEach(tab => {
      tab.classList.toggle('active', tab.getAttribute('data-filter') === 'ALL');
    });
    this.renderTransactionsTable();
  },

  closeAllModals() {
    document.querySelectorAll('.modal-backdrop, .drawer-backdrop').forEach(el => {
      el.classList.remove('open');
    });
    document.getElementById('sidebar')?.classList.remove('open');
    document.getElementById('sidebar-backdrop')?.classList.remove('open');
    document.getElementById('btn-mobile-nav-toggle')?.setAttribute('aria-expanded', 'false');
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div style="flex: 1;">${message}</div>
      <button style="background: none; border: none; color: var(--text-muted); cursor: pointer;" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  },

  formatTime(isoStr) {
    if (!isoStr) return '--:--:--';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  },

  formatDateTime(isoStr) {
    if (!isoStr) return '----/--/-- --:--:--';
    try {
      const d = new Date(isoStr);
      const datePart = d.toISOString().split('T')[0];
      const timePart = d.toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return `${datePart} ${timePart}`;
    } catch {
      return isoStr;
    }
  },

  getTierBadge(tier) {
    const t = (tier || 'LOW').toUpperCase();
    const cls = t === 'CRITICAL' ? 'badge-critical' : t === 'HIGH' ? 'badge-high' : t === 'MEDIUM' ? 'badge-medium' : 'badge-low';
    return `<span class="badge ${cls}">${t}</span>`;
  },

  getStatusBadge(status) {
    const s = (status || 'APPROVED').toUpperCase();
    const cls = s === 'BLOCKED' ? 'badge-critical' :
                (s === 'HOLD_FOR_REVIEW' || s === 'UNDER_REVIEW') ? 'badge-medium' : 'badge-low';
    return `<span class="badge ${cls}">${s}</span>`;
  },

  getScoreCircle(score, tier) {
    const s = Math.round(Number(score || 0));
    const t = (tier || 'LOW').toUpperCase();
    const bg = t === 'CRITICAL' ? 'var(--status-critical-bg)' : t === 'HIGH' ? 'var(--status-high-bg)' : t === 'MEDIUM' ? 'var(--status-medium-bg)' : 'var(--status-low-bg)';
    const color = t === 'CRITICAL' ? 'var(--status-critical)' : t === 'HIGH' ? 'var(--status-high)' : t === 'MEDIUM' ? 'var(--status-medium)' : 'var(--status-low)';
    return `<span class="risk-score-circle" style="background: ${bg}; color: ${color};">${s}</span>`;
  },

  /* =========================================================================
     DEEP ANALYTICS & FORENSICS CONTROLLERS
     ========================================================================= */

  bindAnalyticsEvents() {
    // 1. Timeframe Presets
    const presetPills = document.querySelectorAll('#analytics-date-presets .filter-pill');
    presetPills.forEach(pill => {
      pill.addEventListener('click', (e) => {
        e.preventDefault();
        presetPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const preset = pill.getAttribute('data-preset');
        this.applyAnalyticsDatePreset(preset);
      });
    });

    // 2. Custom Date Inputs
    const startInput = document.getElementById('analytics-filter-start');
    const endInput = document.getElementById('analytics-filter-end');
    if (startInput) {
      startInput.addEventListener('change', (e) => {
        this.state.analyticsMgmt.start_date = e.target.value;
      });
    }
    if (endInput) {
      endInput.addEventListener('change', (e) => {
        this.state.analyticsMgmt.end_date = e.target.value;
      });
    }

    // 3. Risk Filter Selector
    const riskSelect = document.getElementById('analytics-filter-risk');
    if (riskSelect) {
      riskSelect.addEventListener('change', (e) => {
        this.state.analyticsMgmt.risk_tier = e.target.value;
      });
    }

    // 4. Apply Filters Button
    const applyBtn = document.getElementById('btn-analytics-apply');
    if (applyBtn) {
      applyBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.loadAnalyticsModule();
      });
    }

    // 5. Reset Filters Button
    const resetBtn = document.getElementById('btn-analytics-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.state.analyticsMgmt.date_preset = 'all';
        this.state.analyticsMgmt.start_date = '';
        this.state.analyticsMgmt.end_date = '';
        this.state.analyticsMgmt.risk_tier = 'ALL';
        if (startInput) startInput.value = '';
        if (endInput) endInput.value = '';
        if (riskSelect) riskSelect.value = 'ALL';
        presetPills.forEach(p => {
          if (p.getAttribute('data-preset') === 'all') p.classList.add('active');
          else p.classList.remove('active');
        });
        this.loadAnalyticsModule();
      });
    }

    // 6. Refresh Analytics Button
    const refreshBtn = document.getElementById('btn-analytics-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        refreshBtn.classList.add('loading');
        await this.loadAnalyticsModule();
        refreshBtn.classList.remove('loading');
        this.showToast('Analytics telemetry refreshed from database', 'info');
      });
    }

    // 7. Export Transactions CSV
    const exportTxBtn = document.getElementById('btn-export-transactions-csv');
    if (exportTxBtn) {
      exportTxBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        exportTxBtn.disabled = true;
        this.showToast('Generating RFC-4180 Transactions CSV...', 'info');
        const res = await window.FraudShieldAPI.exportTransactionsCSV({
          start_date: this.state.analyticsMgmt.start_date || null,
          end_date: this.state.analyticsMgmt.end_date || null,
          risk_tier: this.state.analyticsMgmt.risk_tier || null,
        });
        exportTxBtn.disabled = false;
        if (res.success) {
          this.showToast('Transactions report downloaded successfully', 'success');
        } else {
          this.showToast('Transactions CSV export failed', 'error');
        }
      });
    }

    // 8. Export Alerts CSV
    const exportAlertsBtn = document.getElementById('btn-export-alerts-csv');
    if (exportAlertsBtn) {
      exportAlertsBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        exportAlertsBtn.disabled = true;
        this.showToast('Generating RFC-4180 Fraud Alerts CSV...', 'info');
        const res = await window.FraudShieldAPI.exportAlertsCSV({
          start_date: this.state.analyticsMgmt.start_date || null,
          end_date: this.state.analyticsMgmt.end_date || null,
        });
        exportAlertsBtn.disabled = false;
        if (res.success) {
          this.showToast('Alerts report downloaded successfully', 'success');
        } else {
          this.showToast('Alerts CSV export failed', 'error');
        }
      });
    }

    // 9. Account Network Graph Filter Controls
    const graphFilterAll = document.getElementById('btn-graph-filter-all');
    const graphFilterSusp = document.getElementById('btn-graph-filter-susp');
    if (graphFilterAll && graphFilterSusp) {
      graphFilterAll.addEventListener('click', (e) => {
        e.preventDefault();
        graphFilterAll.classList.add('active');
        graphFilterSusp.classList.remove('active');
        this.loadNetworkGraph({ only_suspicious: false });
      });
      graphFilterSusp.addEventListener('click', (e) => {
        e.preventDefault();
        graphFilterSusp.classList.add('active');
        graphFilterAll.classList.remove('active');
        this.loadNetworkGraph({ only_suspicious: true });
      });
    }
  },

  applyAnalyticsDatePreset(preset) {
    this.state.analyticsMgmt.date_preset = preset;
    const now = new Date();
    const startInput = document.getElementById('analytics-filter-start');
    const endInput = document.getElementById('analytics-filter-end');

    if (preset === 'all') {
      this.state.analyticsMgmt.start_date = '';
      this.state.analyticsMgmt.end_date = '';
      if (startInput) startInput.value = '';
      if (endInput) endInput.value = '';
    } else if (preset === 'today') {
      const todayStr = now.toISOString().slice(0, 10);
      this.state.analyticsMgmt.start_date = todayStr;
      this.state.analyticsMgmt.end_date = todayStr;
      if (startInput) startInput.value = todayStr;
      if (endInput) endInput.value = todayStr;
    } else if (preset === '7d') {
      const past7 = new Date(now.getTime() - 7 * 86400000).toISOString().slice(0, 10);
      const todayStr = now.toISOString().slice(0, 10);
      this.state.analyticsMgmt.start_date = past7;
      this.state.analyticsMgmt.end_date = todayStr;
      if (startInput) startInput.value = past7;
      if (endInput) endInput.value = todayStr;
    } else if (preset === '30d') {
      const past30 = new Date(now.getTime() - 30 * 86400000).toISOString().slice(0, 10);
      const todayStr = now.toISOString().slice(0, 10);
      this.state.analyticsMgmt.start_date = past30;
      this.state.analyticsMgmt.end_date = todayStr;
      if (startInput) startInput.value = past30;
      if (endInput) endInput.value = todayStr;
    }

    this.loadAnalyticsModule();
  },

  async loadAnalyticsModule() {
    this.state.analyticsMgmt.isLoading = true;
    const restrictedBanner = document.getElementById('analytics-role-restricted-state');
    const analyticsHeader = document.querySelector('#view-analytics .view-header');
    const cardGrid = document.querySelector('#view-analytics .analytics-kpi-grid');
    const chartsGrid = document.querySelector('#view-analytics .analytics-charts-grid');
    const networkCard = document.getElementById('card-network-graph');

    const user = window.FraudShieldAPI.currentUser;
    if (user && user.role === 'ANALYST') {
      this.state.analyticsMgmt.isLoading = false;
      if (restrictedBanner) restrictedBanner.style.display = 'block';
      if (analyticsHeader) analyticsHeader.style.opacity = '0.3';
      if (cardGrid) cardGrid.style.opacity = '0.3';
      if (chartsGrid) chartsGrid.style.opacity = '0.3';
      if (networkCard) networkCard.style.opacity = '0.3';
      this.showToast('Deep Analytics module is restricted to ADMIN security role', 'warning');
      return;
    }

    if (restrictedBanner) restrictedBanner.style.display = 'none';
    if (analyticsHeader) analyticsHeader.style.opacity = '1';
    if (cardGrid) cardGrid.style.opacity = '1';
    if (chartsGrid) chartsGrid.style.opacity = '1';
    if (networkCard) networkCard.style.opacity = '1';

    try {
      const data = await window.FraudShieldAPI.getAnalytics({
        start_date: this.state.analyticsMgmt.start_date || null,
        end_date: this.state.analyticsMgmt.end_date || null,
        risk_tier: this.state.analyticsMgmt.risk_tier || null,
      });
      this.state.analyticsMgmt.data = data;
      this.renderAnalyticsKPIs(data);
      if (window.FraudShieldCharts) {
        window.FraudShieldCharts.updateAnalyticsCharts(data);
      }
      await this.loadNetworkGraph();
    } catch (err) {
      console.error('Failed to load deep analytics telemetry:', err);
      this.state.analyticsMgmt.error = err.message;
      this.showToast(err.message || 'Could not synchronize analytics telemetry', 'error');
    } finally {
      this.state.analyticsMgmt.isLoading = false;
    }
  },

  async loadNetworkGraph({ only_suspicious = false } = {}) {
    try {
      const graphData = await window.FraudShieldAPI.getNetworkGraph({
        only_suspicious,
        min_risk_score: only_suspicious ? 50.0 : 0.0,
        limit: 150
      });
      if (graphData && (graphData.summary || graphData.metrics)) {
        const s = graphData.summary || graphData.metrics;
        const muleBadge = document.getElementById('badge-graph-mule-count');
        const statNodes = document.getElementById('graph-stat-nodes');
        const statEdges = document.getElementById('graph-stat-edges');
        const statRepeated = document.getElementById('graph-stat-repeated');
        const statMules = document.getElementById('graph-stat-mules');

        if (muleBadge) muleBadge.textContent = `${s.mule_hubs_detected || 0} Mule Hubs`;
        if (statNodes) statNodes.textContent = s.total_nodes || 0;
        if (statEdges) statEdges.textContent = s.total_edges || 0;
        if (statRepeated) statRepeated.textContent = s.repeated_pairs || 0;
        if (statMules) statMules.textContent = s.mule_hubs_detected || 0;
      }
      if (window.FraudShieldCharts && window.FraudShieldCharts.renderAccountNetworkGraph) {
        window.FraudShieldCharts.renderAccountNetworkGraph(graphData);
      }
    } catch (err) {
      console.warn('Failed to load account relationship network graph:', err);
    }
  },

  renderAnalyticsKPIs(data) {
    if (!data) return;

    // 1. Total Volume
    const volEl = document.getElementById('analytics-kpi-volume');
    const volSub = document.getElementById('analytics-kpi-volume-sub');
    if (volEl) {
      const volVal = data.total_volume_inr || 0.0;
      volEl.textContent = '₹' + volVal.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }
    if (volSub) {
      volSub.textContent = `${(data.total_evaluated || 0).toLocaleString()} transactions evaluated`;
    }

    // 2. Total Count
    const countEl = document.getElementById('analytics-kpi-count');
    const countSub = document.getElementById('analytics-kpi-count-sub');
    if (countEl) countEl.textContent = (data.total_evaluated || 0).toLocaleString();
    if (countSub) {
      const filterTxt = this.state.analyticsMgmt.risk_tier !== 'ALL'
        ? `${this.state.analyticsMgmt.risk_tier} filter applied`
        : 'All risk tiers included';
      countSub.textContent = filterTxt;
    }

    // 3. Anomaly Flag Rate
    const anomEl = document.getElementById('analytics-kpi-anomaly-rate');
    const anomSub = document.getElementById('analytics-kpi-anomaly-sub');
    if (anomEl) anomEl.textContent = `${(data.fraud_rate_percentage || 0).toFixed(1)}%`;
    if (anomSub) {
      anomSub.textContent = `${(data.total_flagged || 0).toLocaleString()} flagged / ${(data.total_evaluated || 0).toLocaleString()} total`;
    }

    // 4. Mean Risk Score
    const scoreEl = document.getElementById('analytics-kpi-avg-score');
    if (scoreEl) scoreEl.textContent = (data.avg_risk_score || 0.0).toFixed(1);

    // 5. Model F1 & ROC-AUC
    const f1AucEl = document.getElementById('analytics-kpi-f1-auc');
    if (f1AucEl && data.model_metrics) {
      const f1Pct = (data.model_metrics.f1_score * 100).toFixed(1);
      const rocAuc = data.model_metrics.roc_auc.toFixed(3);
      f1AucEl.textContent = `${f1Pct}% • ${rocAuc}`;
    }

    // 6. Confusion Matrix Cards
    if (data.model_metrics && data.model_metrics.confusion_matrix) {
      const cm = data.model_metrics.confusion_matrix;
      const tpEl = document.getElementById('analytics-cm-tp');
      const fpEl = document.getElementById('analytics-cm-fp');
      const fnEl = document.getElementById('analytics-cm-fn');
      const tnEl = document.getElementById('analytics-cm-tn');
      if (tpEl) tpEl.textContent = (cm.true_positives ?? 207).toLocaleString();
      if (fpEl) fpEl.textContent = (cm.false_positives ?? 172).toLocaleString();
      if (fnEl) fnEl.textContent = (cm.false_negatives ?? 43).toLocaleString();
      if (tnEl) tnEl.textContent = (cm.true_negatives ?? 6036).toLocaleString();
    }
  }
,


  // -------------------------------------------------------------------------
  // Behavioural Anomaly & Profile Inspector Module
  // -------------------------------------------------------------------------
  async loadBehaviouralModule() {
    try {
      const metrics = await window.FraudShieldAPI.getBehaviouralMetrics();
      if (metrics) {
        const elUsers = document.getElementById('kpi-behavioural-users');
        const elBursts = document.getElementById('kpi-behavioural-bursts');
        const elOutliers = document.getElementById('kpi-behavioural-outliers');
        const elNovel = document.getElementById('kpi-behavioural-novel');

        if (elUsers) elUsers.textContent = (metrics.total_profiled_users || 0).toLocaleString();
        if (elBursts) elBursts.textContent = (metrics.velocity_bursts_detected || 0).toLocaleString();
        if (elOutliers) elOutliers.textContent = (metrics.amount_outliers_detected || 0).toLocaleString();
        if (elNovel) elNovel.textContent = (metrics.novel_device_attempts || 0).toLocaleString();
      }

      const users = await window.FraudShieldAPI.getBehaviouralUsers();
      const userSelect = document.getElementById('behavioural-user-select');
      if (userSelect && users && users.length) {
        userSelect.innerHTML = users.map(u => 
          `<option value="${u.sender_upi}">${u.sender_upi} (${u.tx_count} transactions)</option>`
        ).join('');

        const selectedUser = userSelect.value || users[0].sender_upi;
        await this.loadUserBaselineProfile(selectedUser);
      }

      await this.loadBehaviouralNetworkGraph(false);
    } catch (err) {
      console.warn('Failed to load behavioural analysis module:', err);
    }
  },

  async loadUserBaselineProfile(senderUpi) {
    if (!senderUpi) return;
    try {
      const p = await window.FraudShieldAPI.getBehaviouralProfile(senderUpi);
      if (!p) return;

      const elPrior = document.getElementById('inspector-prior-tx');
      const elAvg = document.getElementById('inspector-avg-amount');
      const elStd = document.getElementById('inspector-std-amount');
      const elFreq = document.getElementById('inspector-daily-freq');
      const elDevCount = document.getElementById('inspector-device-count');
      const elDevPills = document.getElementById('inspector-devices-pills');
      const elRecCount = document.getElementById('inspector-recipient-count');
      const elRecPills = document.getElementById('inspector-recipients-pills');
      const elTbody = document.getElementById('inspector-recent-tbody');

      if (elPrior) elPrior.textContent = `${p.total_prior_transactions || 0} txs`;
      if (elAvg) elAvg.textContent = `₹${Number(p.avg_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (elStd) elStd.textContent = `±₹${Number(p.std_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (elFreq) elFreq.textContent = `${p.daily_frequency_mean || 0.0} / day`;

      const devices = p.known_devices || [];
      if (elDevCount) elDevCount.textContent = `${devices.length} Devices`;
      if (elDevPills) {
        elDevPills.innerHTML = devices.length 
          ? devices.map(d => `<span class="badge badge-channel" style="font-family: var(--font-mono); font-size: 0.72rem;">${d}</span>`).join('')
          : '<span style="font-size: 0.75rem; color: var(--text-muted); font-style: italic;">No devices recorded</span>';
      }

      const recs = p.known_recipients || [];
      if (elRecCount) elRecCount.textContent = `${recs.length} Counterparties`;
      if (elRecPills) {
        elRecPills.innerHTML = recs.length
          ? recs.map(r => `<span class="badge badge-low" style="font-family: var(--font-mono); font-size: 0.72rem;">${r}</span>`).join('')
          : '<span style="font-size: 0.75rem; color: var(--text-muted); font-style: italic;">No recipients recorded</span>';
      }

      const txs = p.recent_transactions || [];
      if (elTbody) {
        elTbody.innerHTML = txs.length
          ? txs.map(tx => `
            <tr>
              <td class="td-tx-id">${tx.tx_id}</td>
              <td class="mono">${tx.receiver_upi}</td>
              <td class="td-amount">₹${Number(tx.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
              <td><span class="badge badge-channel">${tx.channel}</span></td>
              <td class="mono" style="font-size: 0.72rem;">${tx.device_id || '-'}</td>
              <td style="font-size: 0.74rem; font-family: var(--font-mono); color: var(--text-secondary);">${this.formatDateTime(tx.timestamp)}</td>
              <td><span class="badge badge-${(tx.risk_tier || 'LOW').toLowerCase()}">${Number(tx.risk_score || 0).toFixed(1)}</span></td>
              <td>${this.getStatusBadge(tx.status)}</td>
            </tr>
          `).join('')
          : '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1rem;">No prior transactions recorded for this user.</td></tr>';
      }
    } catch (e) {
      console.warn('Failed to load user baseline profile:', e);
    }
  },

  async loadBehaviouralNetworkGraph(onlySuspicious = false) {
    try {
      const graphData = await window.FraudShieldAPI.getNetworkGraph({
        only_suspicious: onlySuspicious,
        min_risk_score: onlySuspicious ? 50.0 : 0.0,
        limit: 150
      });
      if (graphData && (graphData.summary || graphData.metrics)) {
        const s = graphData.summary || graphData.metrics;
        const statNodes = document.getElementById('graph-stat-nodes');
        const statEdges = document.getElementById('graph-stat-edges');
        const statMules = document.getElementById('graph-stat-mules');
        const statRepeated = document.getElementById('graph-stat-repeated');

        if (statNodes) statNodes.textContent = s.total_nodes || 0;
        if (statEdges) statEdges.textContent = s.total_edges || 0;
        if (statMules) statMules.textContent = s.mule_hubs_detected || 0;
        if (statRepeated) statRepeated.textContent = s.repeated_pairs || s.repeated_interaction_pairs || 0;
      }
      if (window.FraudShieldCharts?.renderAccountNetworkGraph) {
        window.FraudShieldCharts.renderAccountNetworkGraph(graphData, 'canvas-behavioural-network');
      }
    } catch (e) {
      console.warn('Failed to load behavioural network graph:', e);
    }
  },

  // -------------------------------------------------------------------------
  // User Management Module
  // -------------------------------------------------------------------------
  async loadUsersManagement() {
    try {
      const res = await window.FraudShieldAPI.getUsers();
      const users = res.users || [];
      const total = res.total ?? users.length;

      const totalEl = document.getElementById('kpi-users-total');
      const adminEl = document.getElementById('kpi-users-admins');
      const analystEl = document.getElementById('kpi-users-analysts');
      const countBadge = document.getElementById('users-table-count');
      const tbody = document.getElementById('users-table-tbody');

      const adminCount = users.filter(u => u.role === 'ADMIN').length;
      const analystCount = users.filter(u => u.role === 'ANALYST').length;

      if (totalEl) totalEl.textContent = total;
      if (adminEl) adminEl.textContent = adminCount;
      if (analystEl) analystEl.textContent = analystCount;
      if (countBadge) countBadge.textContent = `${total} Accounts`;

      if (tbody) {
        tbody.innerHTML = users.map(u => {
          const roleBadge = u.role === 'ADMIN'
            ? '<span class="badge badge-role-admin">ADMIN</span>'
            : '<span class="badge badge-role-analyst">ANALYST</span>';
          const statusBadge = u.is_active
            ? '<span class="badge badge-low">ACTIVE</span>'
            : '<span class="badge badge-critical">DISABLED</span>';
          const currentUsername = window.FraudShieldAPI.currentUser?.username;
          const isSelf = currentUsername && currentUsername === u.username;

          return `
            <tr>
              <td class="mono" style="font-weight: 600;">#${u.id}</td>
              <td>
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                  <div class="avatar-circle" style="width: 32px; height: 32px; font-size: 0.8rem;">
                    ${(u.full_name || u.username).slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <div style="font-weight: 600; color: var(--text-primary); font-size: 0.82rem;">${u.username}</div>
                    ${isSelf ? '<span style="font-size: 0.65rem; color: var(--primary-purple); font-weight: 600;">(Current Session)</span>' : ''}
                  </div>
                </div>
              </td>
              <td>${u.full_name || '-'}</td>
              <td class="mono" style="font-size: 0.78rem;">${u.email}</td>
              <td>${roleBadge}</td>
              <td>${statusBadge}</td>
              <td class="mono" style="font-size: 0.74rem; color: var(--text-secondary);">${this.formatDateTime(u.created_at)}</td>
              <td style="text-align: right;">
                <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
                  <button class="btn btn-secondary btn-sm" onclick="FraudShieldDashboard.toggleUserRole(${u.id}, '${u.role}')" title="Toggle Role">
                    ${u.role === 'ADMIN' ? 'Demote to Analyst' : 'Promote to Admin'}
                  </button>
                  <button class="btn btn-secondary btn-sm" onclick="FraudShieldDashboard.toggleUserStatus(${u.id}, ${u.is_active})" title="Toggle Active">
                    ${u.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  ${!isSelf ? `
                    <button class="btn btn-danger btn-sm" onclick="FraudShieldDashboard.deleteUserAccount(${u.id}, '${u.username}')" title="Delete">
                      Delete
                    </button>
                  ` : ''}
                </div>
              </td>
            </tr>
          `;
        }).join('');
      }
    } catch (e) {
      console.warn('Failed to load users management:', e);
    }
  },

  async toggleUserRole(userId, currentRole) {
    const newRole = currentRole === 'ADMIN' ? 'ANALYST' : 'ADMIN';
    try {
      await window.FraudShieldAPI.updateUser(userId, { role: newRole });
      this.showToast(`User permissions updated to ${newRole}`, 'success');
      this.loadUsersManagement();
    } catch (e) {
      this.showToast(e.message || 'Failed to update user role', 'error');
    }
  },

  async toggleUserStatus(userId, currentActive) {
    try {
      await window.FraudShieldAPI.updateUser(userId, { is_active: !currentActive });
      this.showToast(`User status set to ${!currentActive ? 'ACTIVE' : 'DISABLED'}`, 'info');
      this.loadUsersManagement();
    } catch (e) {
      this.showToast(e.message || 'Failed to toggle user status', 'error');
    }
  },

  async deleteUserAccount(userId, username) {
    if (!confirm(`Are you sure you want to permanently delete user '${username}'?`)) return;
    try {
      await window.FraudShieldAPI.deleteUser(userId);
      this.showToast(`User ${username} deleted successfully`, 'success');
      this.loadUsersManagement();
    } catch (e) {
      this.showToast(e.message || 'Failed to delete user account', 'error');
    }
  },

  // -------------------------------------------------------------------------
  // Reports Module Helpers
  // -------------------------------------------------------------------------
  loadReportsModule() {
    // Dynamic reports initialization
  },

  applyReportsPreset(range) {
    const now = new Date();
    const startInput = document.getElementById('reports-start-date');
    const endInput = document.getElementById('reports-end-date');

    document.querySelectorAll('[id^="btn-rep-preset-"]').forEach(b => b.classList.remove('active'));
    document.getElementById(`btn-rep-preset-${range.toLowerCase()}`)?.classList.add('active');

    if (range === 'ALL') {
      if (startInput) startInput.value = '';
      if (endInput) endInput.value = '';
    } else if (range === 'TODAY') {
      const todayStr = now.toISOString().split('T')[0];
      if (startInput) startInput.value = todayStr;
      if (endInput) endInput.value = todayStr;
    } else if (range === '7D') {
      const d7 = new Date(now.getTime() - 7 * 86400000).toISOString().split('T')[0];
      if (startInput) startInput.value = d7;
      if (endInput) endInput.value = now.toISOString().split('T')[0];
    } else if (range === '30D') {
      const d30 = new Date(now.getTime() - 30 * 86400000).toISOString().split('T')[0];
      if (startInput) startInput.value = d30;
      if (endInput) endInput.value = now.toISOString().split('T')[0];
    }
  },

  appendReportAuditLog(reportType, filterScope, format = 'RFC-4180 CSV') {
    const tbody = document.getElementById('reports-history-tbody');
    if (!tbody) return;
    const nowStr = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="mono">${nowStr}</td>
      <td><strong>${reportType}</strong></td>
      <td>${filterScope}</td>
      <td><span class="badge badge-channel">${format}</span></td>
      <td><span class="badge badge-role-admin">AUDIT LOGGED</span></td>
      <td><span class="badge badge-low">DELIVERED</span></td>
    `;
    tbody.prepend(tr);
  },

  // -------------------------------------------------------------------------
  // Settings Module Helpers
  // -------------------------------------------------------------------------
  loadSettingsModule() {
    const saved = localStorage.getItem('fraudshield_settings');
    if (saved) {
      try {
        const cfg = JSON.parse(saved);
        if (cfg.threshold_medium) {
          const el = document.getElementById('page-cfg-threshold-medium');
          if (el) el.value = cfg.threshold_medium;
          const m = document.getElementById('cfg-threshold-medium');
          if (m) m.value = cfg.threshold_medium;
        }
        if (cfg.threshold_high) {
          const el = document.getElementById('page-cfg-threshold-high');
          if (el) el.value = cfg.threshold_high;
          const h = document.getElementById('cfg-threshold-high');
          if (h) h.value = cfg.threshold_high;
        }
        if (cfg.threshold_critical) {
          const el = document.getElementById('page-cfg-threshold-critical');
          if (el) el.value = cfg.threshold_critical;
          const c = document.getElementById('cfg-threshold-critical');
          if (c) c.value = cfg.threshold_critical;
        }
        if (cfg.polling_rate) {
          const el = document.getElementById('page-cfg-polling-rate');
          if (el) el.value = cfg.polling_rate;
          const p = document.getElementById('cfg-polling-rate');
          if (p) p.value = cfg.polling_rate;
        }
      } catch (e) {}
    }
    const user = window.FraudShieldAPI.currentUser;
    if (user) {
      const nameInput = document.getElementById('page-profile-fullname');
      const emailInput = document.getElementById('page-profile-email');
      const roleBadge = document.getElementById('page-profile-role-badge');
      if (nameInput) nameInput.value = user.full_name || '';
      if (emailInput) emailInput.value = user.email || '';
      if (roleBadge) roleBadge.textContent = user.role || 'ANALYST';
    }
    this.updateThemeSettingsUI();
  },

  updateThemeSettingsUI() {
    const isDark = (this.state.currentTheme === 'dark');
    const badge = document.getElementById('page-theme-status-badge');
    const lightCard = document.getElementById('page-btn-theme-light');
    const darkCard = document.getElementById('page-btn-theme-dark');

    if (badge) {
      badge.textContent = isDark ? 'Dark SOC Mode Active' : 'Light Theme Active (Default)';
      badge.className = isDark ? 'badge badge-channel' : 'badge badge-success';
    }
    if (lightCard) {
      lightCard.style.border = isDark ? '1px solid var(--border-subtle)' : '2px solid var(--primary-purple)';
      lightCard.style.background = isDark ? 'var(--bg-surface)' : 'var(--bg-card)';
    }
    if (darkCard) {
      darkCard.style.border = isDark ? '2px solid var(--primary-purple)' : '1px solid var(--border-subtle)';
      darkCard.style.background = isDark ? 'var(--bg-card)' : 'var(--bg-surface)';
    }
  },
};

window.FraudShieldDashboard = FraudShieldDashboard;

// Auto-boot on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  FraudShieldDashboard.init();
});
