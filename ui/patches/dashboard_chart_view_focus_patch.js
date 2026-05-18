// ==================================================
// dashboard_chart_view_focus_patch.js
// ==================================================
// CHART VIEW FOCUS PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-18-chart-view-focus-v2-plugin-capabilities';
  const MODES = ['clean', 'analyse', 'debug', 'compact'];

  function runtimeStatus() {
    try {
      if (typeof latestStatusData !== 'undefined' && latestStatusData) return latestStatusData;
    } catch (_) {}
    return window.latestStatusData || null;
  }

  function chartInstance() {
    if (window.__klineChartInstance) return window.__klineChartInstance;
    try {
      if (typeof window.initKlineChart === 'function') return window.initKlineChart();
    } catch (_) {}
    return null;
  }

  function apiInstance() {
    return window.klinecharts || window.KLineCharts || window.KLineChart || null;
  }

  function currentAsset() {
    const value = document.getElementById('chartAsset')?.value || document.getElementById('assetFilter')?.value || '-';
    return String(value || '-').replace('.P', '');
  }

  function currentTimeframe() {
    const select = document.getElementById('chartTimeframe');
    if (!select) return '-';
    const option = select.options[select.selectedIndex];
    return option?.textContent || select.value || '-';
  }

  function chartMode() {
    const saved = String(localStorage.getItem('botChartViewMode') || 'analyse').toLowerCase();
    return MODES.includes(saved) ? saved : 'analyse';
  }

  function setChartMode(mode) {
    const value = MODES.includes(mode) ? mode : 'analyse';
    localStorage.setItem('botChartViewMode', value);
    document.body.dataset.chartViewMode = value;
    refreshChartFocus();
  }

  function activeIndicatorText() {
    const status = String(document.getElementById('chartPluginStatus')?.textContent || '');
    const direct = status.split('Agent-Indikatoren').pop() || '';
    const cleaned = direct.replace('bereit', '').trim();
    if (cleaned) return cleaned;
    const meta = String(document.getElementById('indicatorChartSettings')?.textContent || '').trim();
    return meta || '-';
  }

  function chartStateText() {
    return String(document.getElementById('chartStatus')?.textContent || 'Noch nicht geladen').trim() || 'Noch nicht geladen';
  }

  function scanSummaryText() {
    const meta = String(document.getElementById('chartMeta')?.textContent || '').trim();
    if (meta) return meta;
    const status = runtimeStatus();
    const running = status?.running;
    if (running === true) return 'Scanner aktiv · warte auf Chart-Metadaten';
    if (running === false) return 'Scanner gestoppt · Chart kann trotzdem geladen werden';
    return 'Noch keine Chart-Metadaten';
  }

  function pluginCapabilities() {
    const api = apiInstance();
    const chart = chartInstance();
    return [
      {
        key: 'native_panes',
        title: 'Native Indicator-Panes',
        detail: 'MACD, RSI, MFI, Volume und eigene Pane-Höhen.',
        available: !!chart && typeof chart.createIndicator === 'function'
      },
      {
        key: 'custom_indicators',
        title: 'Eigene Indikatoren',
        detail: 'BOT_MFI, BOT_VOLUME_DIRECT und weitere Agent-Indikatoren.',
        available: !!api && typeof api.registerIndicator === 'function'
      },
      {
        key: 'overlays',
        title: 'Preis-Overlays',
        detail: 'VWAP, HMA/SMA/Triple EMA, Breakout Range und Struktur-Linien.',
        available: !!chart && typeof chart.createOverlay === 'function'
      },
      {
        key: 'overlay_remove',
        title: 'Overlay Cleanup',
        detail: 'Linien und Agent-Overlays können vor jedem Draw entfernt werden.',
        available: !!chart && typeof chart.removeOverlay === 'function'
      },
      {
        key: 'resize',
        title: 'Resize / Pane Layout',
        detail: 'Chart-Fläche kann nach aktiven Panes neu berechnet werden.',
        available: !!chart && typeof chart.resize === 'function'
      },
      {
        key: 'style_runtime',
        title: 'Runtime Styling',
        detail: 'Dark Layout, Grid, Panels und Statusbereiche werden dynamisch gesetzt.',
        available: true
      }
    ];
  }

  function upsertModeToolbar() {
    const chartView = document.getElementById('chartView');
    const card = chartView?.querySelector(':scope > .card');
    const header = card?.querySelector('.chartViewHeader');
    if (!card || !header) return;

    let toolbar = document.getElementById('chartViewModeToolbar');
    if (!toolbar) {
      toolbar = document.createElement('div');
      toolbar.id = 'chartViewModeToolbar';
      toolbar.className = 'chartViewModeToolbar';
      header.insertAdjacentElement('afterend', toolbar);
    }
    const active = chartMode();
    toolbar.innerHTML = `
      <div class="chartViewModeTitle">
        <strong>Darstellung</strong>
        <span>Plugin-Modus für Übersicht und Debug</span>
      </div>
      <div class="chartViewModeButtons">
        <button type="button" data-chart-view-mode="clean" class="${active === 'clean' ? 'active' : ''}">Clean</button>
        <button type="button" data-chart-view-mode="analyse" class="${active === 'analyse' ? 'active' : ''}">Analyse</button>
        <button type="button" data-chart-view-mode="debug" class="${active === 'debug' ? 'active' : ''}">Agent Debug</button>
        <button type="button" data-chart-view-mode="compact" class="${active === 'compact' ? 'active' : ''}">Kompakt</button>
      </div>
    `;
    document.body.dataset.chartViewMode = active;
  }

  function upsertSummaryPanel() {
    const chartView = document.getElementById('chartView');
    const card = chartView?.querySelector(':scope > .card');
    const toolbar = card?.querySelector('.chartToolbar');
    if (!card || !toolbar) return;

    let panel = document.getElementById('chartViewFocusPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'chartViewFocusPanel';
      panel.className = 'chartViewFocusPanel';
      toolbar.insertAdjacentElement('afterend', panel);
    }

    panel.innerHTML = `
      <div class="chartViewFocusCard asset"><span>Asset</span><strong>${currentAsset()}</strong></div>
      <div class="chartViewFocusCard timeframe"><span>Timeframe</span><strong>${currentTimeframe()}</strong></div>
      <div class="chartViewFocusCard candles"><span>Kerzen</span><strong>${document.getElementById('chartCandleLimit')?.value || '-'}</strong></div>
      <div class="chartViewFocusCard indicators"><span>Aktive Chart-Anzeigen</span><strong>${activeIndicatorText()}</strong></div>
      <div class="chartViewFocusCard status"><span>Chart Status</span><strong>${chartStateText()}</strong></div>
    `;
  }

  function upsertLegendPanel() {
    const chartView = document.getElementById('chartView');
    const card = chartView?.querySelector(':scope > .card');
    const focus = document.getElementById('chartViewFocusPanel');
    if (!card || !focus) return;

    let legend = document.getElementById('chartViewLegendPanel');
    if (!legend) {
      legend = document.createElement('div');
      legend.id = 'chartViewLegendPanel';
      legend.className = 'chartViewLegendPanel';
      focus.insertAdjacentElement('afterend', legend);
    }

    legend.innerHTML = `
      <div class="chartViewLegendHeader"><strong>Chart View Übersicht</strong><span>${scanSummaryText()}</span></div>
      <div class="chartViewLegendGrid">
        <div class="chartViewLegendItem structure"><b>Struktur Overlay</b><span>BOS/CHoCH · LL/HH Box · Swing Labels · Support/Resistance</span></div>
        <div class="chartViewLegendItem chart"><b>Indikator Fenster</b><span>MACD · MFI · RSI · Volume · HMA/SMA/Triple EMA</span></div>
        <div class="chartViewLegendItem price"><b>Preislinien</b><span>VWAP · HMA · SMA · Triple EMA · Breakout Range</span></div>
        <div class="chartViewLegendItem status"><b>Status Agenten</b><span>Breakout/Fakeout · Volatility Regime · Risk Agent</span></div>
      </div>
    `;
  }

  function upsertCapabilityPanel() {
    const legend = document.getElementById('chartViewLegendPanel');
    const chartView = document.getElementById('chartView');
    const card = chartView?.querySelector(':scope > .card');
    if (!card || !legend) return;

    let panel = document.getElementById('chartViewCapabilityPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'chartViewCapabilityPanel';
      panel.className = 'chartViewCapabilityPanel';
      legend.insertAdjacentElement('afterend', panel);
    }

    const capabilities = pluginCapabilities();
    panel.innerHTML = `
      <div class="chartViewCapabilityHeader">
        <strong>Plugin-Möglichkeiten</strong>
        <span>aus vorhandener KLineCharts-Integration erkannt</span>
      </div>
      <div class="chartViewCapabilityGrid">
        ${capabilities.map(item => `
          <div class="chartViewCapabilityItem ${item.available ? 'ok' : 'missing'}">
            <b>${item.title}</b>
            <span>${item.detail}</span>
            <em>${item.available ? 'verfügbar' : 'nicht aktiv'}</em>
          </div>
        `).join('')}
      </div>
    `;
  }

  function normalizeChartLayout() {
    const chart = document.getElementById('klineChart');
    const wrap = chart?.closest('.chartCanvasWrap');
    const card = document.getElementById('chartView')?.querySelector(':scope > .card');
    const statusPanel = document.getElementById('directAgentChartStatusPanel');
    const meta = document.getElementById('chartMeta');
    if (!chart || !wrap || !card) return;

    wrap.classList.add('chartViewFocusedCanvas');
    chart.classList.add('chartViewFocusedChart');
    if (statusPanel) {
      statusPanel.classList.add('chartViewFocusedStatusPanel');
      if (statusPanel.previousElementSibling !== wrap) card.insertBefore(statusPanel, wrap.nextSibling);
    }
    if (meta && statusPanel && meta.previousElementSibling !== statusPanel) card.insertBefore(meta, statusPanel.nextSibling);

    const text = activeIndicatorText().toLowerCase();
    const paneCount = ['macd', 'mfi', 'rsi', 'volume'].filter(name => text.includes(name)).length;
    const mode = chartMode();
    const base = mode === 'compact' ? 760 : mode === 'clean' ? 900 : mode === 'debug' ? 1040 : 960;
    const step = mode === 'compact' ? 165 : mode === 'debug' ? 240 : 220;
    const minHeight = mode === 'compact' ? 940 : mode === 'clean' ? 1080 : mode === 'debug' ? 1260 : 1180;
    const targetHeight = Math.max(minHeight, Math.min(2100, base + paneCount * step));
    wrap.style.height = `${targetHeight}px`;
    wrap.style.minHeight = `${targetHeight}px`;
    wrap.style.maxHeight = 'none';
    chart.style.height = `${targetHeight}px`;
    chart.style.minHeight = `${targetHeight}px`;
    chart.style.maxHeight = 'none';

    window.setTimeout(() => {
      try { if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart(); } catch (_) {}
      try { if (window.__klineChartInstance && typeof window.__klineChartInstance.resize === 'function') window.__klineChartInstance.resize(); } catch (_) {}
    }, 100);
  }

  function refreshChartFocus() {
    upsertModeToolbar();
    upsertSummaryPanel();
    upsertLegendPanel();
    upsertCapabilityPanel();
    normalizeChartLayout();
  }

  function installStyles() {
    const oldStyle = document.getElementById('chart-view-focus-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'chart-view-focus-style';
    style.textContent = `
      #chartView { width:100% !important; max-width:none !important; }
      #chartView > .card { width:100% !important; max-width:none !important; overflow:visible !important; border-left:5px solid #22d3ee !important; }
      #chartView .chartViewHeader { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:14px !important; padding-bottom:12px !important; border-bottom:1px solid rgba(148,163,184,.18) !important; }
      #chartView .chartSetupHint { margin:10px 0 14px !important; color:var(--muted) !important; font-size:12px !important; }
      #chartView .chartViewModeToolbar { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:14px !important; margin:14px 0 !important; padding:12px 14px !important; border:1px solid var(--line) !important; border-radius:10px !important; background:rgba(15,23,42,.24) !important; }
      #chartView .chartViewModeTitle strong { display:block !important; color:var(--ink) !important; font-size:13px !important; font-weight:900 !important; letter-spacing:.07em !important; text-transform:uppercase !important; }
      #chartView .chartViewModeTitle span { display:block !important; margin-top:4px !important; color:var(--muted) !important; font-size:12px !important; }
      #chartView .chartViewModeButtons { display:flex !important; flex-wrap:wrap !important; gap:8px !important; }
      #chartView .chartViewModeButtons button { min-height:34px !important; padding:7px 11px !important; border:1px solid var(--line) !important; border-radius:999px !important; background:var(--panel-soft) !important; color:var(--muted) !important; font-weight:900 !important; cursor:pointer !important; }
      #chartView .chartViewModeButtons button.active { border-color:#22d3ee !important; color:#67e8f9 !important; background:rgba(8,145,178,.18) !important; }
      #chartView .chartToolbar { display:grid !important; grid-template-columns:minmax(210px, 1.2fr) minmax(130px, .6fr) minmax(130px, .6fr) minmax(150px, .65fr) minmax(220px, 1fr) !important; gap:12px !important; align-items:end !important; padding:14px !important; border:1px solid var(--line) !important; border-radius:10px !important; background:rgba(15,23,42,.26) !important; }
      #chartView .chartToolbar .controlButton, #chartView .chartToolbar select { min-height:42px !important; }
      #chartView .chartStatusText { min-height:42px !important; display:flex !important; align-items:center !important; padding:8px 10px !important; border:1px solid var(--line) !important; border-radius:7px !important; background:rgba(2,6,23,.28) !important; }
      #chartView .chartViewFocusPanel { display:grid !important; grid-template-columns:repeat(5, minmax(0, 1fr)) !important; gap:12px !important; margin:14px 0 !important; }
      #chartView .chartViewFocusCard { min-height:86px !important; padding:12px !important; border:1px solid var(--line) !important; border-radius:9px !important; background:rgba(15,23,42,.32) !important; overflow:hidden !important; }
      #chartView .chartViewFocusCard.asset { border-left:4px solid #2dd4bf !important; }
      #chartView .chartViewFocusCard.timeframe { border-left:4px solid #60a5fa !important; }
      #chartView .chartViewFocusCard.candles { border-left:4px solid #818cf8 !important; }
      #chartView .chartViewFocusCard.indicators { border-left:4px solid #22d3ee !important; }
      #chartView .chartViewFocusCard.status { border-left:4px solid #f59e0b !important; }
      #chartView .chartViewFocusCard span { display:block !important; color:var(--muted) !important; font-size:11px !important; font-weight:800 !important; letter-spacing:.05em !important; text-transform:uppercase !important; }
      #chartView .chartViewFocusCard strong { display:block !important; margin-top:8px !important; color:var(--ink) !important; font-size:14px !important; font-weight:900 !important; line-height:1.35 !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      #chartView .chartViewFocusCard.indicators strong, #chartView .chartViewFocusCard.status strong { font-size:12px !important; white-space:normal !important; display:-webkit-box !important; -webkit-line-clamp:2 !important; -webkit-box-orient:vertical !important; }
      #chartView .chartViewLegendPanel, #chartView .chartViewCapabilityPanel { margin:0 0 16px !important; padding:14px !important; border:1px solid var(--line) !important; border-radius:10px !important; background:rgba(15,23,42,.22) !important; }
      #chartView .chartViewLegendHeader, #chartView .chartViewCapabilityHeader { display:flex !important; align-items:flex-start !important; justify-content:space-between !important; gap:14px !important; margin-bottom:12px !important; padding-bottom:10px !important; border-bottom:1px solid rgba(148,163,184,.18) !important; }
      #chartView .chartViewLegendHeader strong, #chartView .chartViewCapabilityHeader strong { color:var(--ink) !important; font-size:13px !important; font-weight:900 !important; letter-spacing:.075em !important; text-transform:uppercase !important; }
      #chartView .chartViewLegendHeader span, #chartView .chartViewCapabilityHeader span { color:var(--muted) !important; font-size:12px !important; text-align:right !important; max-width:58% !important; }
      #chartView .chartViewLegendGrid { display:grid !important; grid-template-columns:repeat(4, minmax(0, 1fr)) !important; gap:10px !important; }
      #chartView .chartViewCapabilityGrid { display:grid !important; grid-template-columns:repeat(3, minmax(0, 1fr)) !important; gap:10px !important; }
      #chartView .chartViewLegendItem, #chartView .chartViewCapabilityItem { min-height:82px !important; padding:11px !important; border:1px solid var(--line) !important; border-radius:8px !important; background:rgba(30,41,59,.52) !important; }
      #chartView .chartViewLegendItem.structure { border-left:4px solid #14b8a6 !important; }
      #chartView .chartViewLegendItem.chart { border-left:4px solid #22d3ee !important; }
      #chartView .chartViewLegendItem.price { border-left:4px solid #f472b6 !important; }
      #chartView .chartViewLegendItem.status { border-left:4px solid #a78bfa !important; }
      #chartView .chartViewCapabilityItem.ok { border-left:4px solid #22c55e !important; }
      #chartView .chartViewCapabilityItem.missing { border-left:4px solid #f97316 !important; opacity:.78 !important; }
      #chartView .chartViewLegendItem b, #chartView .chartViewCapabilityItem b { display:block !important; color:var(--ink) !important; font-size:12px !important; font-weight:900 !important; letter-spacing:.045em !important; text-transform:uppercase !important; }
      #chartView .chartViewLegendItem span, #chartView .chartViewCapabilityItem span { display:block !important; margin-top:6px !important; color:var(--muted) !important; font-size:12px !important; line-height:1.35 !important; }
      #chartView .chartViewCapabilityItem em { display:inline-flex !important; margin-top:9px !important; padding:3px 7px !important; border-radius:999px !important; background:rgba(148,163,184,.16) !important; color:var(--muted) !important; font-size:11px !important; font-style:normal !important; font-weight:900 !important; text-transform:uppercase !important; }
      #chartView #indicatorChartSettings, #chartView #chartMeta { margin:0 0 12px !important; padding:10px 12px !important; border:1px solid rgba(148,163,184,.18) !important; border-radius:8px !important; background:rgba(2,6,23,.30) !important; color:var(--muted) !important; overflow-wrap:anywhere !important; }
      #chartView .chartViewFocusedCanvas { position:relative !important; display:block !important; width:100% !important; margin:0 0 24px !important; border:1px solid var(--line) !important; border-radius:10px !important; background:#020617 !important; overflow:hidden !important; }
      #chartView .chartViewFocusedChart { display:block !important; width:100% !important; }
      body[data-chart-view-mode="clean"] #chartView #directAgentChartStatusPanel, body[data-chart-view-mode="clean"] #chartView .chartViewCapabilityPanel { display:none !important; }
      body[data-chart-view-mode="compact"] #chartView .chartViewLegendPanel, body[data-chart-view-mode="compact"] #chartView .chartViewCapabilityPanel, body[data-chart-view-mode="compact"] #chartView #indicatorChartSettings { display:none !important; }
      body[data-chart-view-mode="debug"] #chartView .chartViewCapabilityPanel { display:block !important; }
      @media (max-width:1300px) { #chartView .chartViewFocusPanel, #chartView .chartViewLegendGrid, #chartView .chartViewCapabilityGrid { grid-template-columns:repeat(2, minmax(0, 1fr)) !important; } #chartView .chartToolbar { grid-template-columns:repeat(2, minmax(0, 1fr)) !important; } }
      @media (max-width:760px) { #chartView .chartViewFocusPanel, #chartView .chartViewLegendGrid, #chartView .chartViewCapabilityGrid, #chartView .chartToolbar { grid-template-columns:1fr !important; } #chartView .chartViewLegendHeader, #chartView .chartViewCapabilityHeader, #chartView .chartViewModeToolbar { flex-direction:column !important; } #chartView .chartViewLegendHeader span, #chartView .chartViewCapabilityHeader span { max-width:none !important; text-align:left !important; } }
    `;
    document.head.appendChild(style);
  }

  function installHooks() {
    ['click', 'change'].forEach(type => {
      document.addEventListener(type, event => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const modeButton = target.closest('[data-chart-view-mode]');
        if (modeButton) {
          setChartMode(modeButton.dataset.chartViewMode);
          return;
        }
        if (target.closest('#chartViewButton, #reloadChart, #chartAsset, #chartTimeframe, #chartCandleLimit, #chartSetupButton')) {
          window.setTimeout(refreshChartFocus, 80);
          window.setTimeout(refreshChartFocus, 350);
          window.setTimeout(refreshChartFocus, 1200);
        }
      }, true);
    });
  }

  function install() {
    installStyles();
    installHooks();
    document.body.dataset.chartViewMode = chartMode();
    refreshChartFocus();
    window.setTimeout(refreshChartFocus, 350);
    window.setTimeout(refreshChartFocus, 1200);
    window.setTimeout(refreshChartFocus, 2500);
    document.body.dataset.chartViewFocusPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  window.addEventListener('resize', refreshChartFocus);
})();
