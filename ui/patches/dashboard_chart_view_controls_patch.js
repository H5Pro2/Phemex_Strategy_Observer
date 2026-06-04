// ==================================================
// dashboard_chart_view_controls_patch.js
// ==================================================
// CHART VIEW CONTROLS PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-24-chart-view-controls-v2-removed-panel';
  const CONTROL_DEFS = [
    ['structure', 'Struktur', 'BOS/CHoCH | Boxen | Swing | Support/Resistance'],
    ['price', 'Preislinien', 'VWAP | HMA/SMA/Triple EMA | Breakout Range'],
    ['panes', 'Indikator Panes', 'MACD | MFI | RSI | Volume'],
    ['status', 'Status Quellen', 'Breakout | Volatility | Risk'],
    ['debug', 'Plugin Debug', 'erkannte KLineCharts-Funktionen']
  ];

  function storageKey(key) {
    return `botChartViewControl_${key}`;
  }

  function controlEnabled(key) {
    const value = localStorage.getItem(storageKey(key));
    return value === null ? true : value === '1';
  }

  function setControlEnabled(key, enabled) {
    localStorage.setItem(storageKey(key), enabled ? '1' : '0');
    applyControls();
  }

  function chartInstance() {
    if (window.__klineChartInstance) return window.__klineChartInstance;
    try {
      if (typeof window.initKlineChart === 'function') return window.initKlineChart();
    } catch (_) {}
    return null;
  }

  function removeOverlay(id) {
    const chart = chartInstance();
    if (!chart || typeof chart.removeOverlay !== 'function') return;
    try { chart.removeOverlay({ id }); return; } catch (_) {}
    try { chart.removeOverlay(id); } catch (_) {}
  }

  function removeIndicator(ref) {
    const chart = chartInstance();
    if (!chart || !ref || ref === 'attempted' || typeof chart.removeIndicator !== 'function') return;
    try { chart.removeIndicator(ref); } catch (_) {}
  }

  function removeKnownPriceOverlays() {
    [
      'bot_direct_vwap_line',
      'bot_direct_breakout_high',
      'bot_direct_breakout_low',
      'bot_hma_line',
      'bot_sma_line',
      'bot_triple_ema_fast_line',
      'bot_triple_ema_slow_line'
    ].forEach(removeOverlay);
  }

  function removeKnownPaneIndicators() {
    const direct = window.__botDirectAgentChartView || {};
    ['rsi', 'volume'].forEach(key => {
      if (direct[key]) removeIndicator(direct[key]);
      delete direct[key];
    });
    const native = window.__botNativeIndicators || {};
    ['macd', 'mfi', 'rsi', 'volume'].forEach(key => {
      if (native[key]) removeIndicator(native[key]);
      delete native[key];
    });
  }

  function upsertControlPanel() {
    document.getElementById('chartViewControlPanel')?.remove();
  }

  function setBodyFlags() {
    CONTROL_DEFS.forEach(([key]) => {
      document.body.dataset[`chartControl${key.charAt(0).toUpperCase()}${key.slice(1)}`] = '1';
    });
  }

  function syncButtonStates() {
    document.querySelectorAll('[data-chart-control]').forEach(button => {
      const key = button.getAttribute('data-chart-control');
      button.classList.toggle('active', controlEnabled(key));
    });
  }

  function applyControls() {
    setBodyFlags();
    syncButtonStates();

    const statusPanel = document.getElementById('directAgentChartStatusPanel');
    if (statusPanel) statusPanel.hidden = false;

    const capabilityPanel = document.getElementById('chartViewCapabilityPanel');
    if (capabilityPanel) capabilityPanel.hidden = true;

    const legend = document.getElementById('chartViewLegendPanel');
    if (legend) legend.classList.toggle('chartViewLegendFiltered', true);

    document.body.dataset.chartViewControlsPatch = PATCH_VERSION;
  }

  function installStyles() {
    const oldStyle = document.getElementById('chart-view-controls-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'chart-view-controls-style';
    style.textContent = `
      #chartView .chartViewControlPanel {
        display:none !important;
        margin:0 0 14px !important;
        padding:12px 14px !important;
        border:1px solid var(--line) !important;
        border-radius:10px !important;
        background:rgba(15,23,42,.24) !important;
      }
      #chartView .chartViewControlHeader {
        display:flex !important;
        align-items:flex-start !important;
        justify-content:space-between !important;
        gap:12px !important;
        margin-bottom:10px !important;
        padding-bottom:9px !important;
        border-bottom:1px solid rgba(148,163,184,.18) !important;
      }
      #chartView .chartViewControlHeader strong {
        color:var(--ink) !important;
        font-size:13px !important;
        font-weight:900 !important;
        letter-spacing:.07em !important;
        text-transform:uppercase !important;
      }
      #chartView .chartViewControlHeader span {
        color:var(--muted) !important;
        font-size:12px !important;
        text-align:right !important;
      }
      #chartView .chartViewControlGrid {
        display:grid !important;
        grid-template-columns:repeat(5, minmax(0, 1fr)) !important;
        gap:9px !important;
      }
      #chartView .chartViewControlToggle {
        min-height:70px !important;
        padding:10px !important;
        border:1px solid var(--line) !important;
        border-left:4px solid #64748b !important;
        border-radius:8px !important;
        background:rgba(30,41,59,.42) !important;
        color:var(--muted) !important;
        text-align:left !important;
        cursor:pointer !important;
      }
      #chartView .chartViewControlToggle.active {
        border-left-color:#22d3ee !important;
        background:rgba(8,145,178,.16) !important;
        color:var(--ink) !important;
      }
      #chartView .chartViewControlToggle span {
        display:block !important;
        font-size:12px !important;
        font-weight:900 !important;
        letter-spacing:.04em !important;
        text-transform:uppercase !important;
      }
      #chartView .chartViewControlToggle small {
        display:block !important;
        margin-top:6px !important;
        color:var(--muted) !important;
        font-size:11px !important;
        line-height:1.3 !important;
      }
      body[data-chart-control-structure="0"] #chartView .chartViewLegendItem.structure,
      body[data-chart-control-structure="0"] #chartView [data-agent-display-group="structure"] {
        display:none !important;
      }
      body[data-chart-control-price="0"] #chartView .chartViewLegendItem.price {
        display:none !important;
      }
      body[data-chart-control-panes="0"] #chartView .chartViewLegendItem.chart,
      body[data-chart-control-panes="0"] #chartView #indicatorChartSettings {
        display:none !important;
      }
      body[data-chart-control-status="0"] #chartView .chartViewLegendItem.status,
      body[data-chart-control-status="0"] #chartView #directAgentChartStatusPanel {
        display:none !important;
      }
      body[data-chart-control-debug="0"] #chartView #chartViewCapabilityPanel {
        display:none !important;
      }
      @media (max-width:1300px) {
        #chartView .chartViewControlGrid {
          grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
        }
      }
      @media (max-width:760px) {
        #chartView .chartViewControlGrid {
          grid-template-columns:1fr !important;
        }
        #chartView .chartViewControlHeader {
          flex-direction:column !important;
        }
        #chartView .chartViewControlHeader span {
          text-align:left !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function installHooks() {
    document.addEventListener('click', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const button = target.closest('[data-chart-control]');
      if (!button) return;
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      button.closest('#chartViewControlPanel')?.remove();
      return;
      const key = button.getAttribute('data-chart-control');
      setControlEnabled(key, !controlEnabled(key));
      if (key === 'panes' || key === 'price') {
        const reload = document.getElementById('reloadChart');
        if (reload) window.setTimeout(() => reload.click(), 120);
      }
    }, true);

    ['click', 'change'].forEach(type => {
      document.addEventListener(type, event => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (target.closest('#chartViewButton, #reloadChart, #chartAsset, #chartTimeframe, #chartCandleLimit, #chartSetupButton')) {
          window.setTimeout(refreshControls, 160);
          window.setTimeout(refreshControls, 600);
          window.setTimeout(refreshControls, 1400);
        }
      }, true);
    });
  }

  function refreshControls() {
    upsertControlPanel();
    applyControls();
  }

  function install() {
    installStyles();
    installHooks();
    refreshControls();
    window.setTimeout(refreshControls, 350);
    window.setTimeout(refreshControls, 1200);
    window.setTimeout(refreshControls, 2500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
