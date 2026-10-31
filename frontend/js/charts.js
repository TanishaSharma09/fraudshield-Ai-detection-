/**
 * FraudShield AI - Chart.js Visualisation Controllers
 * Dynamic Dual-Theme Architecture (Default: Light Fintech Mode, with full Dark Mode support)
 */

const FraudShieldCharts = {
  // Overview Dashboard Chart Instances
  activityChart: null,
  distributionChart: null,

  // Deep Analytics 7-Chart Suite Instances
  analyticsTotalTxChart: null,
  analyticsRiskDistChart: null,
  analyticsSuspiciousTrendsChart: null,
  analyticsAmountDistChart: null,
  analyticsFrequencyDistChart: null,
  analyticsFraudVsLegitChart: null,
  analyticsModelEvalChart: null,

  // Dynamic Theme Colors Lookup
  getThemeColors() {
    const isDark = (document.documentElement.getAttribute('data-theme') === 'dark');
    return {
      isDark,
      gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(231, 233, 240, 0.8)',
      tickColor: isDark ? '#94A3B8' : '#758098',
      legendColor: isDark ? '#F8FAFC' : '#25324B',
      tooltipBg: isDark ? '#10172A' : '#FFFFFF',
      tooltipTitle: isDark ? '#F8FAFC' : '#25324B',
      tooltipBody: isDark ? '#CBD5E1' : '#758098',
      tooltipBorder: isDark ? '#1E2C48' : '#E7E9F0',
      doughnutBorder: isDark ? '#131D33' : '#FFFFFF',
      radarAngle: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(231, 233, 240, 0.9)',
      pointBorder: isDark ? '#10172A' : '#FFFFFF'
    };
  },

  // Dynamic Tooltip Configuration
  getTooltipConfig(customCallbacks = {}) {
    const c = this.getThemeColors();
    return {
      backgroundColor: c.tooltipBg,
      titleColor: c.tooltipTitle,
      bodyColor: c.tooltipBody,
      borderColor: c.tooltipBorder,
      borderWidth: 1,
      padding: 10,
      boxPadding: 4,
      usePointStyle: true,
      cornerRadius: 6,
      titleFont: { family: "'Inter', sans-serif", size: 12, weight: 600 },
      bodyFont: { family: "'Inter', sans-serif", size: 11 },
      callbacks: customCallbacks
    };
  },

  init() {
    const c = this.getThemeColors();
    if (typeof Chart !== 'undefined') {
      Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      Chart.defaults.color = c.tickColor;
      Chart.defaults.borderColor = c.gridColor;
    }

    this.initActivityChart();
    this.initDistributionChart();

    // Debounced window resize handler to keep all active charts sharp & pixel-perfect
    let resizeTimer = null;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        this.resizeAll();
      }, 100);
    });
  },

  applyTheme(themeName) {
    const c = this.getThemeColors();

    if (typeof Chart !== 'undefined') {
      Chart.defaults.color = c.tickColor;
      Chart.defaults.borderColor = c.gridColor;
    }

    const updateChart = (chart) => {
      if (!chart) return;
      if (chart.options.plugins?.legend?.labels) {
        chart.options.plugins.legend.labels.color = c.legendColor;
      }
      if (chart.options.plugins?.tooltip) {
        chart.options.plugins.tooltip.backgroundColor = c.tooltipBg;
        chart.options.plugins.tooltip.titleColor = c.tooltipTitle;
        chart.options.plugins.tooltip.bodyColor = c.tooltipBody;
        chart.options.plugins.tooltip.borderColor = c.tooltipBorder;
      }
      if (chart.options.scales) {
        if (chart.options.scales.x) {
          if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = c.gridColor;
          if (chart.options.scales.x.ticks) chart.options.scales.x.ticks.color = c.tickColor;
        }
        if (chart.options.scales.y) {
          if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = c.gridColor;
          if (chart.options.scales.y.ticks) chart.options.scales.y.ticks.color = c.tickColor;
        }
        if (chart.options.scales.r) {
          if (chart.options.scales.r.angleLines) chart.options.scales.r.angleLines.color = c.radarAngle;
          if (chart.options.scales.r.grid) chart.options.scales.r.grid.color = c.radarAngle;
          if (chart.options.scales.r.pointLabels) chart.options.scales.r.pointLabels.color = c.legendColor;
          if (chart.options.scales.r.ticks) chart.options.scales.r.ticks.color = c.tickColor;
        }
      }
      chart.update();
    };

    if (this.distributionChart) {
      this.distributionChart.data.datasets[0].borderColor = c.doughnutBorder;
      updateChart(this.distributionChart);
    }
    if (this.analyticsRiskDistChart) {
      this.analyticsRiskDistChart.data.datasets[0].borderColor = c.doughnutBorder;
      updateChart(this.analyticsRiskDistChart);
    }

    updateChart(this.activityChart);
    updateChart(this.analyticsTotalTxChart);
    updateChart(this.analyticsSuspiciousTrendsChart);
    updateChart(this.analyticsAmountDistChart);
    updateChart(this.analyticsFrequencyDistChart);
    updateChart(this.analyticsFraudVsLegitChart);
    updateChart(this.analyticsModelEvalChart);

    if (this._networkGraphState.data) {
      this.renderAccountNetworkGraph(this._networkGraphState.data);
    }
  },

  resizeAll() {
    const list = [
      this.activityChart,
      this.distributionChart,
      this.analyticsTotalTxChart,
      this.analyticsRiskDistChart,
      this.analyticsSuspiciousTrendsChart,
      this.analyticsAmountDistChart,
      this.analyticsFrequencyDistChart,
      this.analyticsFraudVsLegitChart,
      this.analyticsModelEvalChart
    ];
    list.forEach(c => {
      if (c && typeof c.resize === 'function') {
        try { c.resize(); } catch (e) {}
      }
    });
  },

  /* =========================================================================
     1. OVERVIEW DASHBOARD CHARTS
     ========================================================================= */

  initActivityChart() {
    const ctx = document.getElementById('activityChart');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js not loaded from CDN; charts running in placeholder mode.');
      return;
    }

    const c = this.getThemeColors();
    const defaultHours = [
      "00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
      "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"
    ];
    const defaultTotal = [1420, 850, 620, 1980, 4850, 8920, 11400, 13200, 14500, 16800, 15200, 7800];
    const defaultAnomalies = [18, 24, 15, 12, 38, 72, 98, 115, 142, 184, 162, 85];

    const context2d = ctx.getContext('2d');
    const blueGradient = context2d.createLinearGradient(0, 0, 0, 260);
    blueGradient.addColorStop(0, 'rgba(76, 131, 217, 0.25)');
    blueGradient.addColorStop(1, 'rgba(76, 131, 217, 0.01)');

    const redGradient = context2d.createLinearGradient(0, 0, 0, 260);
    redGradient.addColorStop(0, 'rgba(217, 79, 92, 0.25)');
    redGradient.addColorStop(1, 'rgba(217, 79, 92, 0.01)');

    this.activityChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: defaultHours,
        datasets: [
          {
            label: 'Total Volume',
            data: defaultTotal,
            borderColor: '#4C83D9',
            backgroundColor: blueGradient,
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#4C83D9',
            pointBorderColor: c.pointBorder,
            pointBorderWidth: 2,
            pointRadius: 3.5,
            pointHoverRadius: 6,
            yAxisID: 'y'
          },
          {
            label: 'Flagged Anomalies',
            data: defaultAnomalies,
            borderColor: '#D94F5C',
            backgroundColor: redGradient,
            borderWidth: 2,
            borderDash: [4, 4],
            fill: false,
            tension: 0.3,
            pointBackgroundColor: '#D94F5C',
            pointBorderColor: c.pointBorder,
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 7,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: {
              boxWidth: 12,
              boxHeight: 12,
              color: c.legendColor,
              font: { family: "'Inter', sans-serif", size: 11, weight: 500 }
            }
          },
          tooltip: this.getTooltipConfig()
        },
        scales: {
          x: {
            grid: { color: c.gridColor, drawBorder: false },
            ticks: { color: c.tickColor, font: { family: "'JetBrains Mono', monospace", size: 10 } }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            grid: { color: c.gridColor, drawBorder: false },
            ticks: {
              color: c.tickColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: (v) => v >= 1000 ? (v / 1000) + 'k' : v
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#D94F5C', font: { family: "'JetBrains Mono', monospace", size: 10 } }
          }
        }
      }
    });
  },

  initDistributionChart() {
    const ctx = document.getElementById('riskDistributionChart');
    if (!ctx || typeof Chart === 'undefined') return;

    const c = this.getThemeColors();
    this.distributionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Low Risk (0-39)', 'Medium Risk (40-69)', 'High Risk (70-89)', 'Critical (90-100)'],
        datasets: [{
          data: [114520, 12088, 1422, 420],
          backgroundColor: ['#16A36A', '#D99324', '#D94F5C', '#7665D5'],
          borderColor: c.doughnutBorder,
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              color: c.legendColor,
              padding: 12,
              font: { family: "'Inter', sans-serif", size: 11, weight: 500 }
            }
          },
          tooltip: this.getTooltipConfig({
            label: (context) => {
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const val = context.raw;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${context.label}: ${val.toLocaleString()} (${pct}%)`;
            }
          })
        }
      }
    });
  },

  updateDistribution(distribution) {
    if (!this.distributionChart || !distribution) return;
    this.distributionChart.data.datasets[0].data = [
      distribution.low || 0,
      distribution.medium || 0,
      distribution.high || 0,
      distribution.critical || 0
    ];
    this.distributionChart.update();
  },

  updateHourlyTrends(hourlyData) {
    if (!this.activityChart || !Array.isArray(hourlyData) || !hourlyData.length) return;
    this.activityChart.data.labels = hourlyData.map(d => d.hour_label);
    this.activityChart.data.datasets[0].data = hourlyData.map(d => d.total_count);
    this.activityChart.data.datasets[1].data = hourlyData.map(d => d.flagged_count);
    this.activityChart.update();
  },

  /* =========================================================================
     2. DEEP ANALYTICS 7-CHART SUITE INITIALISATION & UPDATES
     ========================================================================= */

  initAnalyticsCharts() {
    if (typeof Chart === 'undefined') return;

    this.initAnalyticsTotalTxChart();
    this.initAnalyticsRiskDistChart();
    this.initAnalyticsSuspiciousTrendsChart();
    this.initAnalyticsAmountDistChart();
    this.initAnalyticsFrequencyDistChart();
    this.initAnalyticsFraudVsLegitChart();
    this.initAnalyticsModelEvalChart();
  },

  // 1. Total Transactions & Ingested Volume (Dual Axis)
  initAnalyticsTotalTxChart() {
    const ctx = document.getElementById('chart-analytics-total-tx');
    if (!ctx) return;
    if (this.analyticsTotalTxChart) this.analyticsTotalTxChart.destroy();

    const c = this.getThemeColors();
    const c2d = ctx.getContext('2d');
    const blueGradient = c2d.createLinearGradient(0, 0, 0, 240);
    blueGradient.addColorStop(0, 'rgba(76, 131, 217, 0.25)');
    blueGradient.addColorStop(1, 'rgba(76, 131, 217, 0.02)');

    this.analyticsTotalTxChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        datasets: [
          {
            label: 'Total Volume (₹)',
            data: [0, 0, 0, 0, 0, 0],
            borderColor: '#4C83D9',
            backgroundColor: blueGradient,
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            yAxisID: 'y'
          },
          {
            label: 'Txn Count',
            data: [0, 0, 0, 0, 0, 0],
            borderColor: '#7665D5',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 3,
            fill: false,
            tension: 0.25,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: c.legendColor, boxWidth: 10, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig({
            label: (ctx) => ctx.datasetIndex === 0
              ? ` Volume: ₹${Number(ctx.raw).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
              : ` Count: ${ctx.raw} txns`
          })
        },
        scales: {
          x: { grid: { color: c.gridColor }, ticks: { color: c.tickColor, font: { family: 'monospace', size: 9 } } },
          y: {
            position: 'left',
            grid: { color: c.gridColor },
            ticks: { color: '#4C83D9', font: { family: 'monospace', size: 9 }, callback: (v) => '₹' + (v >= 1000 ? (v/1000).toFixed(0) + 'k' : v) }
          },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#7665D5', font: { family: 'monospace', size: 9 } }
          }
        }
      }
    });
  },

  // 2. Risk Tier Distribution (Doughnut)
  initAnalyticsRiskDistChart() {
    const ctx = document.getElementById('chart-analytics-risk-dist');
    if (!ctx) return;
    if (this.analyticsRiskDistChart) this.analyticsRiskDistChart.destroy();

    const c = this.getThemeColors();
    this.analyticsRiskDistChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Low (<40)', 'Medium (40-69)', 'High (70-89)', 'Critical (≥90)'],
        datasets: [{
          data: [1, 0, 0, 0],
          backgroundColor: ['#16A36A', '#D99324', '#D94F5C', '#7665D5'],
          borderColor: c.doughnutBorder,
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: { position: 'bottom', labels: { color: c.legendColor, boxWidth: 10, padding: 8, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig({
            label: (item) => {
              const total = item.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((item.raw / total) * 100).toFixed(1) : 0;
              return ` ${item.label}: ${item.raw.toLocaleString()} (${pct}%)`;
            }
          })
        }
      }
    });
  },

  // 3. Suspicious Transaction Trends Over Time (Time-series)
  initAnalyticsSuspiciousTrendsChart() {
    const ctx = document.getElementById('chart-analytics-suspicious-trends');
    if (!ctx) return;
    if (this.analyticsSuspiciousTrendsChart) this.analyticsSuspiciousTrendsChart.destroy();

    const c = this.getThemeColors();
    const c2d = ctx.getContext('2d');
    const redGradient = c2d.createLinearGradient(0, 0, 0, 240);
    redGradient.addColorStop(0, 'rgba(217, 79, 92, 0.25)');
    redGradient.addColorStop(1, 'rgba(217, 79, 92, 0.02)');

    this.analyticsSuspiciousTrendsChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        datasets: [
          {
            label: 'Flagged Anomalies (Score ≥ 40)',
            data: [0, 0, 0, 0, 0, 0],
            borderColor: '#D94F5C',
            backgroundColor: redGradient,
            borderWidth: 2.2,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: '#D94F5C',
            pointBorderColor: c.pointBorder,
            pointRadius: 3
          },
          {
            label: 'Normal Flow',
            data: [0, 0, 0, 0, 0, 0],
            borderColor: '#4C83D9',
            borderWidth: 1.5,
            fill: false,
            tension: 0.3,
            pointBackgroundColor: '#4C83D9',
            pointBorderColor: c.pointBorder,
            pointRadius: 2.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: c.legendColor, boxWidth: 10, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig()
        },
        scales: {
          x: { grid: { color: c.gridColor }, ticks: { color: c.tickColor, font: { family: 'monospace', size: 9 } } },
          y: { grid: { color: c.gridColor }, ticks: { color: c.tickColor, font: { family: 'monospace', size: 9 } } }
        }
      }
    });
  },

  // 4. Transaction Amount Distribution Histogram Brackets
  initAnalyticsAmountDistChart() {
    const ctx = document.getElementById('chart-analytics-amount-dist');
    if (!ctx) return;
    if (this.analyticsAmountDistChart) this.analyticsAmountDistChart.destroy();

    const c = this.getThemeColors();
    this.analyticsAmountDistChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['< ₹500', '₹500-2k', '₹2k-10k', '₹10k-50k', '₹50k-1L', '> ₹1L'],
        datasets: [
          {
            label: 'Normal Transactions',
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: 'rgba(76, 131, 217, 0.75)',
            borderColor: '#4C83D9',
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'Flagged Anomalies',
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: 'rgba(217, 79, 92, 0.85)',
            borderColor: '#D94F5C',
            borderWidth: 1,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: c.legendColor, boxWidth: 10, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig()
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: c.tickColor, font: { family: 'monospace', size: 9 } } },
          y: { grid: { color: c.gridColor }, ticks: { color: c.tickColor, font: { family: 'monospace', size: 9 } } }
        }
      }
    });
  },

  // 5. Transaction Frequency & Velocity Bursts
  initAnalyticsFrequencyDistChart() {
    const ctx = document.getElementById('chart-analytics-frequency-dist');
    if (!ctx) return;
    if (this.analyticsFrequencyDistChart) this.analyticsFrequencyDistChart.destroy();

    const c = this.getThemeColors();
    this.analyticsFrequencyDistChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Single Txn (1.0x)', 'Moderate (2-3 txs)', 'High Velocity (4-5 txs)', 'Critical Burst (6+ txs)'],
        datasets: [
          {
            label: 'Total Volume in Burst',
            data: [0, 0, 0, 0],
            backgroundColor: 'rgba(118, 101, 213, 0.75)',
            borderColor: '#7665D5',
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'High Risk Intercepts',
            data: [0, 0, 0, 0],
            backgroundColor: 'rgba(217, 79, 92, 0.85)',
            borderColor: '#D94F5C',
            borderWidth: 1,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: c.legendColor, boxWidth: 10, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig()
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: c.tickColor, font: { size: 9 } } },
          y: { grid: { color: c.gridColor }, ticks: { color: c.tickColor, font: { family: 'monospace', size: 9 } } }
        }
      }
    });
  },

  // 6. Fraud-Labelled vs Legitimate Transactions
  initAnalyticsFraudVsLegitChart() {
    const ctx = document.getElementById('chart-analytics-fraud-vs-legit');
    if (!ctx) return;
    if (this.analyticsFraudVsLegitChart) this.analyticsFraudVsLegitChart.destroy();

    const c = this.getThemeColors();
    this.analyticsFraudVsLegitChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Test Set Ground Truth', 'Operational SOC Decisions'],
        datasets: [
          {
            label: 'Legitimate / Cleared',
            data: [6208, 0],
            backgroundColor: 'rgba(22, 163, 106, 0.75)',
            borderColor: '#16A36A',
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'Confirmed Fraud / Blocked',
            data: [250, 0],
            backgroundColor: 'rgba(217, 79, 92, 0.85)',
            borderColor: '#D94F5C',
            borderWidth: 1,
            borderRadius: 4
          },
          {
            label: 'Model Anomaly Outliers (Unconfirmed)',
            data: [0, 0],
            backgroundColor: 'rgba(217, 147, 36, 0.75)',
            borderColor: '#D99324',
            borderWidth: 1,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: c.legendColor, boxWidth: 10, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig({
            afterBody: () => [
              '',
              'Note: Model Anomaly indicates statistical deviation.',
              'Confirmed Fraud requires chargeback or SOC block.'
            ]
          })
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: c.legendColor, font: { size: 10, weight: 500 } } },
          y: {
            grid: { color: c.gridColor },
            ticks: {
              color: c.tickColor,
              font: { family: 'monospace', size: 9 },
              callback: (v) => v >= 1000 ? (v / 1000) + 'k' : v
            }
          }
        }
      }
    });
  },

  // 7. Active ML Model Evaluation Metrics Radar Chart
  initAnalyticsModelEvalChart() {
    const ctx = document.getElementById('chart-analytics-model-eval');
    if (!ctx) return;
    if (this.analyticsModelEvalChart) this.analyticsModelEvalChart.destroy();

    const c = this.getThemeColors();
    this.analyticsModelEvalChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: [
          'Precision (54.6%)',
          'Recall (82.8%)',
          'F1-Score (65.8%)',
          'Specificity (97.2%)',
          'Balanced Acc (90.0%)',
          'ROC-AUC (97.3%)',
          'PR-AUC (82.5%)'
        ],
        datasets: [{
          label: 'Isolation Forest (Calibrated v1.0)',
          data: [54.6, 82.8, 65.8, 97.2, 90.0, 97.3, 82.5],
          backgroundColor: 'rgba(118, 101, 213, 0.20)',
          borderColor: '#7665D5',
          pointBackgroundColor: '#9686EA',
          pointBorderColor: c.pointBorder,
          pointHoverBackgroundColor: '#7665D5',
          pointHoverBorderColor: c.pointBorder,
          borderWidth: 2,
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: c.radarAngle },
            grid: { color: c.radarAngle },
            pointLabels: { color: c.legendColor, font: { family: "'Inter', sans-serif", size: 10, weight: 600 } },
            ticks: {
              display: true,
              backdropColor: 'transparent',
              color: c.tickColor,
              font: { size: 8 },
              stepSize: 20
            },
            suggestedMin: 0,
            suggestedMax: 100
          }
        },
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: c.legendColor, boxWidth: 10, font: { size: 10, weight: 500 } } },
          tooltip: this.getTooltipConfig({
            label: (item) => ` ${item.dataset.label}: ${item.raw}%`
          })
        }
      }
    });
  },

  /* =========================================================================
     3. DEEP ANALYTICS LIVE DATA BINDING
     ========================================================================= */

  updateAnalyticsCharts(data) {
    if (!data) return;

    if (!this.analyticsTotalTxChart) this.initAnalyticsTotalTxChart();
    if (!this.analyticsRiskDistChart) this.initAnalyticsRiskDistChart();
    if (!this.analyticsSuspiciousTrendsChart) this.initAnalyticsSuspiciousTrendsChart();
    if (!this.analyticsAmountDistChart) this.initAnalyticsAmountDistChart();
    if (!this.analyticsFrequencyDistChart) this.initAnalyticsFrequencyDistChart();
    if (!this.analyticsFraudVsLegitChart) this.initAnalyticsFraudVsLegitChart();
    if (!this.analyticsModelEvalChart) this.initAnalyticsModelEvalChart();

    // 1. Total Transactions Chart
    if (this.analyticsTotalTxChart && Array.isArray(data.hourly_trends) && data.hourly_trends.length) {
      this.analyticsTotalTxChart.data.labels = data.hourly_trends.map(h => h.hour_label);
      this.analyticsTotalTxChart.data.datasets[0].data = data.hourly_trends.map(h => h.total_volume || 0.0);
      this.analyticsTotalTxChart.data.datasets[1].data = data.hourly_trends.map(h => h.total_count || 0);
      this.analyticsTotalTxChart.update();
    }

    // 2. Risk Distribution Chart
    if (this.analyticsRiskDistChart && data.distribution) {
      this.analyticsRiskDistChart.data.datasets[0].data = [
        data.distribution.low || 0,
        data.distribution.medium || 0,
        data.distribution.high || 0,
        data.distribution.critical || 0
      ];
      this.analyticsRiskDistChart.update();
    }

    // 3. Suspicious Trends Chart
    if (this.analyticsSuspiciousTrendsChart && Array.isArray(data.hourly_trends) && data.hourly_trends.length) {
      this.analyticsSuspiciousTrendsChart.data.labels = data.hourly_trends.map(h => h.hour_label);
      this.analyticsSuspiciousTrendsChart.data.datasets[0].data = data.hourly_trends.map(h => h.flagged_count || 0);
      this.analyticsSuspiciousTrendsChart.data.datasets[1].data = data.hourly_trends.map(h => (h.total_count || 0) - (h.flagged_count || 0));
      this.analyticsSuspiciousTrendsChart.update();
    }

    // 4. Amount Distribution Histogram
    if (this.analyticsAmountDistChart && Array.isArray(data.amount_distribution) && data.amount_distribution.length) {
      this.analyticsAmountDistChart.data.labels = data.amount_distribution.map(b => b.bracket_label);
      this.analyticsAmountDistChart.data.datasets[0].data = data.amount_distribution.map(b => (b.total_count || 0) - (b.flagged_count || 0));
      this.analyticsAmountDistChart.data.datasets[1].data = data.amount_distribution.map(b => b.flagged_count || 0);
      this.analyticsAmountDistChart.update();
    }

    // 5. Frequency & Velocity Distribution
    if (this.analyticsFrequencyDistChart && Array.isArray(data.frequency_distribution) && data.frequency_distribution.length) {
      this.analyticsFrequencyDistChart.data.labels = data.frequency_distribution.map(f => f.frequency_label);
      this.analyticsFrequencyDistChart.data.datasets[0].data = data.frequency_distribution.map(f => f.count || 0);
      this.analyticsFrequencyDistChart.data.datasets[1].data = data.frequency_distribution.map(f => f.flagged_count || 0);
      this.analyticsFrequencyDistChart.update();
    }

    // 6. Fraud-Labelled vs Legitimate
    if (this.analyticsFraudVsLegitChart && data.fraud_vs_legit) {
      const fvl = data.fraud_vs_legit;
      this.analyticsFraudVsLegitChart.data.datasets[0].data = [
        fvl.ground_truth_legitimate || 6208,
        fvl.operational_confirmed_legit || 0
      ];
      this.analyticsFraudVsLegitChart.data.datasets[1].data = [
        fvl.ground_truth_fraud || 250,
        fvl.operational_confirmed_fraud || 0
      ];
      this.analyticsFraudVsLegitChart.data.datasets[2].data = [
        0,
        fvl.model_flagged_anomalies || 0
      ];
      this.analyticsFraudVsLegitChart.update();
    }

    // 7. Model Evaluation Metrics
    if (this.analyticsModelEvalChart && data.model_metrics) {
      const mm = data.model_metrics;
      const prec = +(mm.precision * 100).toFixed(1);
      const rec = +(mm.recall * 100).toFixed(1);
      const f1 = +(mm.f1_score * 100).toFixed(1);
      const spec = +(mm.specificity * 100).toFixed(1);
      const balAcc = +(mm.balanced_accuracy * 100).toFixed(1);
      const rocAuc = +(mm.roc_auc * 100).toFixed(1);
      const prAuc = +(mm.pr_auc * 100).toFixed(1);

      this.analyticsModelEvalChart.data.labels = [
        `Precision (${prec}%)`,
        `Recall (${rec}%)`,
        `F1-Score (${f1}%)`,
        `Specificity (${spec}%)`,
        `Balanced Acc (${balAcc}%)`,
        `ROC-AUC (${rocAuc}%)`,
        `PR-AUC (${prAuc}%)`
      ];
      this.analyticsModelEvalChart.data.datasets[0].data = [prec, rec, f1, spec, balAcc, rocAuc, prAuc];
      this.analyticsModelEvalChart.update();
    }
  },

  /* =========================================================================
     4. ACCOUNT RELATIONSHIP NETWORK GRAPH VISUALISER (DUAL THEME)
     ========================================================================= */

  _networkGraphState: {
    data: null,
    nodePositions: {},
    isHovering: false,
    hoveredItem: null
  },

  renderAccountNetworkGraph(graphData, canvasId = 'canvas-account-network-graph') {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !graphData || !Array.isArray(graphData.nodes)) return;

    const ctx = canvas.getContext('2d');
    const tooltip = document.getElementById('graph-node-tooltip');
    const isDark = (document.documentElement.getAttribute('data-theme') === 'dark');

    // High-DPI scaling
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || 800;
    const height = rect.height || 380;
    const dpr = window.devicePixelRatio || 1;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const nodes = graphData.nodes;
    const edges = graphData.edges || [];
    this._networkGraphState.data = graphData;

    // Layout calculation: Clustered layout (Mule Hubs in center/right, senders around left/top)
    const positions = {};
    const n = nodes.length;
    const cx = width * 0.48;
    const cy = height * 0.50;

    nodes.forEach((node, i) => {
      let x, y;
      if (node.is_mule_candidate || node.role === 'MULE_HUB') {
        const muleAngle = ((i % 3) * (2 * Math.PI / 3)) + Math.PI / 4;
        const r = Math.min(width, height) * 0.18;
        x = cx + r * Math.cos(muleAngle) + 50;
        y = cy + r * Math.sin(muleAngle);
      } else if (node.role === 'RECEIVER') {
        x = width * 0.82;
        y = height * 0.25 + (i * 70) % (height * 0.5);
      } else {
        const sendAngle = ((i / Math.max(1, n)) * Math.PI) + Math.PI / 2;
        const r = Math.min(width, height) * 0.36;
        x = cx + r * Math.cos(sendAngle) - 40;
        y = cy + r * Math.sin(sendAngle);
      }
      x = Math.max(50, Math.min(width - 60, x));
      y = Math.max(40, Math.min(height - 40, y));
      positions[node.id] = { x, y, node };
    });
    this._networkGraphState.nodePositions = positions;

    // Draw Routine for Light & Dark Themes
    function draw() {
      ctx.clearRect(0, 0, width, height);

      // Background grid dots
      ctx.fillStyle = isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(37, 50, 75, 0.05)';
      for (let gx = 20; gx < width; gx += 40) {
        for (let gy = 20; gy < height; gy += 40) {
          ctx.beginPath();
          ctx.arc(gx, gy, 1.2, 0, 2 * Math.PI);
          ctx.fill();
        }
      }

      // Draw Directed Edges
      edges.forEach(edge => {
        const src = positions[edge.source];
        const tgt = positions[edge.target];
        if (!src || !tgt) return;

        const isSusp = edge.is_suspicious || edge.avg_risk_score >= 60.0;
        const isRepeated = edge.is_repeated || edge.tx_count >= 2;

        ctx.save();
        ctx.beginPath();
        const mx = (src.x + tgt.x) / 2;
        const my = (src.y + tgt.y) / 2;
        const dx = tgt.x - src.x;
        const dy = tgt.y - src.y;
        const norm = Math.sqrt(dx * dx + dy * dy) || 1;
        const curveOffset = isRepeated ? 25 : 12;
        const qx = mx - (dy / norm) * curveOffset;
        const qy = my + (dx / norm) * curveOffset;

        ctx.moveTo(src.x, src.y);
        ctx.quadraticCurveTo(qx, qy, tgt.x, tgt.y);

        if (isSusp) {
          ctx.strokeStyle = '#D94F5C';
          ctx.lineWidth = isRepeated ? 2.5 : 1.8;
          ctx.setLineDash([6, 4]);
          ctx.shadowColor = 'rgba(217, 79, 92, 0.35)';
          ctx.shadowBlur = 6;
        } else {
          ctx.strokeStyle = isDark ? 'rgba(59, 130, 246, 0.45)' : 'rgba(76, 131, 217, 0.45)';
          ctx.lineWidth = 1.4;
          ctx.setLineDash([]);
        }
        ctx.stroke();
        ctx.restore();

        // Edge Transfer Count Pill
        if (edge.tx_count > 1 || isSusp) {
          ctx.save();
          ctx.fillStyle = isSusp ? '#D94F5C' : (isDark ? '#10172A' : '#FFFFFF');
          ctx.strokeStyle = isSusp ? '#D94F5C' : (isDark ? '#1E2C48' : '#E7E9F0');
          ctx.lineWidth = 1;
          const badgeText = `${edge.tx_count}x`;
          ctx.font = 'bold 9px monospace';
          const tw = ctx.measureText(badgeText).width;
          ctx.beginPath();
          ctx.roundRect(qx - tw / 2 - 4, qy - 7, tw + 8, 14, 4);
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = isSusp ? '#FFFFFF' : (isDark ? '#F8FAFC' : '#25324B');
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(badgeText, qx, qy);
          ctx.restore();
        }
      });

      // Draw Nodes
      nodes.forEach(node => {
        const pos = positions[node.id];
        if (!pos) return;

        const isMule = node.is_mule_candidate || node.role === 'MULE_HUB';
        const isSusp = node.is_suspicious || node.avg_risk_score >= 60.0;
        const radius = isMule ? 16 : 12;

        ctx.save();

        // Outer halo ring
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 4, 0, 2 * Math.PI);
        if (isMule) {
          ctx.fillStyle = 'rgba(217, 79, 92, 0.15)';
          ctx.strokeStyle = 'rgba(217, 79, 92, 0.5)';
        } else if (isSusp) {
          ctx.fillStyle = 'rgba(217, 147, 36, 0.15)';
          ctx.strokeStyle = 'rgba(217, 147, 36, 0.5)';
        } else {
          ctx.fillStyle = isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(76, 131, 217, 0.15)';
          ctx.strokeStyle = isDark ? 'rgba(59, 130, 246, 0.5)' : 'rgba(76, 131, 217, 0.5)';
        }
        ctx.fill();
        ctx.stroke();

        // Node center body
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = isMule ? '#D94F5C' : (isSusp ? '#D99324' : '#4C83D9');
        ctx.shadowColor = 'rgba(0, 0, 0, 0.08)';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.restore();

        // Inner core
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius - 4, 0, 2 * Math.PI);
        ctx.fillStyle = isDark ? '#0B101D' : '#FFFFFF';
        ctx.fill();

        // Node Label
        ctx.save();
        ctx.font = '600 10px "JetBrains Mono", monospace';
        ctx.fillStyle = isMule ? '#D94F5C' : (isDark ? '#CBD5E1' : '#25324B');
        ctx.textAlign = 'center';
        ctx.fillText(node.label, pos.x, pos.y + radius + 14);
        ctx.restore();
      });
    }

    draw();

    // Mouse Move Hover Listener for Interactive Tooltips
    if (!canvas._hasHoverListener) {
      canvas.addEventListener('mousemove', (e) => {
        const b = canvas.getBoundingClientRect();
        const mx = e.clientX - b.left;
        const my = e.clientY - b.top;

        let foundNode = null;
        for (const [id, pos] of Object.entries(this._networkGraphState.nodePositions)) {
          const dx = mx - pos.x;
          const dy = my - pos.y;
          if (Math.sqrt(dx * dx + dy * dy) <= 20) {
            foundNode = pos.node;
            break;
          }
        }

        if (foundNode && tooltip) {
          const isDarkNow = (document.documentElement.getAttribute('data-theme') === 'dark');
          canvas.style.cursor = 'pointer';
          tooltip.style.display = 'block';
          tooltip.style.left = `${mx + 15}px`;
          tooltip.style.top = `${my - 10}px`;
          tooltip.style.backgroundColor = isDarkNow ? '#10172A' : '#FFFFFF';
          tooltip.style.color = isDarkNow ? '#F8FAFC' : '#25324B';
          tooltip.style.border = isDarkNow ? '1px solid #1E2C48' : '1px solid #E7E9F0';
          tooltip.style.boxShadow = isDarkNow ? '0 8px 24px rgba(0, 0, 0, 0.5)' : '0 8px 24px rgba(37, 50, 75, 0.12)';
          tooltip.style.borderRadius = '8px';
          tooltip.style.padding = '10px 14px';

          const textColorSecondary = isDarkNow ? '#94A3B8' : '#758098';
          const textColorPrimary = isDarkNow ? '#F8FAFC' : '#25324B';
          const muleBadge = foundNode.is_mule_candidate
            ? `<span style="color:#D94F5C;font-weight:700;">[MULE HUB CANDIDATE]</span><br/>`
            : '';
          tooltip.innerHTML = `
            <div style="font-weight:700;margin-bottom:3px;color:#7665D5;font-size:0.85rem;">${foundNode.id}</div>
            ${muleBadge}
            <div style="font-size:0.75rem;color:${textColorSecondary};">Role: <strong style="color:${textColorPrimary};">${foundNode.role}</strong></div>
            <div style="font-size:0.75rem;color:${textColorSecondary};">Sent: <strong style="color:${textColorPrimary};">₹${foundNode.total_sent.toLocaleString()}</strong> (${foundNode.tx_sent_count} txs)</div>
            <div style="font-size:0.75rem;color:${textColorSecondary};">Received: <strong style="color:${textColorPrimary};">₹${foundNode.total_received.toLocaleString()}</strong> (${foundNode.tx_recv_count} txs)</div>
            <div style="font-size:0.75rem;color:${textColorSecondary};">Avg Risk Score: <strong style="color:${foundNode.avg_risk_score >= 60 ? '#D94F5C' : '#16A36A'};">${foundNode.avg_risk_score}</strong> / 100</div>
          `;
        } else if (tooltip) {
          canvas.style.cursor = 'default';
          tooltip.style.display = 'none';
        }
      });

      canvas.addEventListener('mouseleave', () => {
        if (tooltip) tooltip.style.display = 'none';
      });

      canvas._hasHoverListener = true;
    }
  }
};

window.FraudShieldCharts = FraudShieldCharts;
