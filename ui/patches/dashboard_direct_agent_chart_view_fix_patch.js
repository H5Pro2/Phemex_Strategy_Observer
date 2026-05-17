// ==================================================
// dashboard_direct_agent_chart_view_fix_patch.js
// ==================================================
// DIRECT AGENT CHART VIEW FIX PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-direct-agent-chart-view-fix-v5-separate-volume-pane';
  let originalDrawChart = null;
  let originalClearKlineChart = null;
  let directVolumeRegistered = false;

  function runtimeConfig() {
    try {
      if (typeof latestConfig !== 'undefined' && latestConfig) return latestConfig;
    } catch (_) {}
    try {
      if (typeof latestStatusData !== 'undefined' && latestStatusData?.config) return latestStatusData.config;
    } catch (_) {}
    if (window.latestConfig) return window.latestConfig;
    if (window.latestStatusData?.config) return window.latestStatusData.config;
    return {};
  }

  function configValue(key, fallback = undefined) {
    const cfg = runtimeConfig();
    if (Object.prototype.hasOwnProperty.call(cfg, key)) return cfg[key];
    return fallback;
  }

  function boolConfig(key, fallback = false) {
    const value = configValue(key, fallback);
    if (typeof value === 'boolean') return value;
    const text = String(value ?? '').trim().toLowerCase();
    if (['1', 'true', 'yes', 'on', 'aktiv', 'active'].includes(text)) return true;
    if (['0', 'false', 'no', 'off', 'aus', 'inactive'].includes(text)) return false;
    return !!fallback;
  }

  function numberConfig(key, fallback) {
    const value = Number(configValue(key, fallback));
    return Number.isFinite(value) ? value : fallback;
  }

  function colorConfig(primaryKey, fallbackKey, fallback) {
    return String(configValue(primaryKey, configValue(fallbackKey, fallback)) || fallback);
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

  function candleNumber(candle, key) {
    const number = Number(candle?.[key]);
    return Number.isFinite(number) ? number : 0;
  }

  function candleTime(candle) {
    const number = Number(candle?.timestamp ?? candle?.time ?? candle?.openTime);
    if (!Number.isFinite(number)) return null;
    return number > 1000000000000 ? Math.floor(number / 1000) : number;
  }

  function registerDirectVolumeIndicator() {
    if (directVolumeRegistered) return;
    const api = apiInstance();
    if (!api || typeof api.registerIndicator !== 'function') return;
    try {
      api.registerIndicator({
        name: 'BOT_VOLUME_DIRECT',
        shortName: 'Volume',
        series: 'volume',
        precision: 0,
        calcParams: [],
        figures: [{ key: 'volume', title: 'VOLUME: ', type: 'bar' }],
        calc: dataList => dataList.map(k => ({ volume: Number(k.volume || 0) }))
      });
      directVolumeRegistered = true;
    } catch (_) {
      directVolumeRegistered = true;
    }
  }

  function createIndicatorSafe(storageKey, indicator, paneId, order, height) {
    const chart = chartInstance();
    if (!chart || typeof chart.createIndicator !== 'function') return;
    window.__botDirectAgentChartView = window.__botDirectAgentChartView || {};
    if (window.__botDirectAgentChartView[storageKey]) return;
    try {
      window.__botDirectAgentChartView[storageKey] = chart.createIndicator(indicator, false, {
        id: paneId,
        height,
        minHeight: 96,
        dragEnabled: true,
        order,
        state: 'normal',
        axis: { name: 'right', position: 'right', inside: false, scrollZoomEnabled: true, gap: { top: 0.12, bottom: 0.12 } }
      }) || 'attempted';
    } catch (_) {
      window.__botDirectAgentChartView[storageKey] = 'attempted';
    }
  }

  function createOverlaySafe(id, points, color) {
    const chart = chartInstance();
    if (!chart || typeof chart.createOverlay !== 'function' || !points.length) return null;
    try {
      chart.createOverlay({
        name: 'segment',
        id,
        points,
        styles: { line: { color: color || '#14b8a6', size: 1 } }
      });
      return { type: 'overlay', id };
    } catch (_) {
      return null;
    }
  }

  function removeChartItem(value) {
    const chart = chartInstance();
    if (!chart || !value || value === 'attempted') return;
    if (typeof value === 'object' && value.type === 'overlay') {
      if (typeof chart.removeOverlay === 'function') {
        try { chart.removeOverlay({ id: value.id }); return; } catch (_) {}
        try { chart.removeOverlay(value.id); return; } catch (_) {}
      }
      return;
    }
    if (typeof chart.removeIndicator === 'function') {
      try { chart.removeIndicator(value); } catch (_) {}
    }
  }

  function removeNativeDirectAgentItems() {
    const nativeItems = window.__botNativeIndicators || {};
    ['rsi', 'volume', 'vwap'].forEach(key => {
      if (!nativeItems[key]) return;
      removeChartItem(nativeItems[key]);
      delete nativeItems[key];
    });
  }

  function clearDirectAgentChartView() {
    Object.values(window.__botDirectAgentChartView || {}).forEach(removeChartItem);
    window.__botDirectAgentChartView = {};
  }

  function vwapPoints(candles) {
    const typed = Array.isArray(candles) ? candles : [];
    const lookback = Math.max(1, Math.floor(numberConfig('agent_vwap_lookback_candles', numberConfig('indicator_vwap_lookback_candles', 96))));
    const points = [];
    for (let index = 0; index < typed.length; index += 1) {
      const start = Math.max(0, index - lookback + 1);
      let volumeSum = 0;
      let weightedSum = 0;
      for (let pos = start; pos <= index; pos += 1) {
        const candle = typed[pos];
        const volume = candleNumber(candle, 'volume');
        if (volume <= 0) continue;
        weightedSum += ((candleNumber(candle, 'high') + candleNumber(candle, 'low') + candleNumber(candle, 'close')) / 3) * volume;
        volumeSum += volume;
      }
      const timestamp = candleTime(typed[index]);
      if (timestamp !== null && volumeSum > 0) points.push({ timestamp, value: weightedSum / volumeSum });
    }
    return points;
  }

  function directPaneCount() {
    let count = 0;
    if (boolConfig('agent_rsi_enabled', false) || boolConfig('indicator_show_rsi', false)) count += 1;
    if (boolConfig('agent_volume_enabled', false) || boolConfig('indicator_show_volume', false)) count += 1;
    return count;
  }

  function nativePaneCount() {
    let count = 0;
    if (boolConfig('agent_macd_enabled', false) || boolConfig('indicator_show_macd', false)) count += 1;
    if (boolConfig('agent_mfi_enabled', false) || boolConfig('indicator_show_mfi', false)) count += 1;
    return count;
  }

  function applyChartHeight() {
    const chartEl = document.getElementById('klineChart');
    const wrap = chartEl?.closest('.chartCanvasWrap');
    if (!chartEl || !wrap) return;
    const paneCount = directPaneCount() + nativePaneCount();
    const height = Math.max(980, Math.min(1680, 760 + paneCount * 185));
    wrap.style.height = `${height}px`;
    wrap.style.minHeight = `${height}px`;
    wrap.style.maxHeight = 'none';
    wrap.style.overflow = 'visible';
    chartEl.style.height = `${height}px`;
    chartEl.style.minHeight = `${height}px`;
    chartEl.style.maxHeight = 'none';
    document.body.dataset.directAgentChartHeight = String(height);
    window.setTimeout(() => {
      try {
        if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart();
      } catch (_) {}
      try {
        const chart = chartInstance();
        if (chart && typeof chart.resize === 'function') chart.resize();
      } catch (_) {}
    }, 80);
  }

  function ensureDirectAgentChartView(candles) {
    const chart = chartInstance();
    if (!chart) return;
    removeNativeDirectAgentItems();
    window.__botDirectAgentChartView = window.__botDirectAgentChartView || {};

    if (boolConfig('agent_rsi_enabled', false) || boolConfig('indicator_show_rsi', false)) {
      const period = Math.max(1, Math.floor(numberConfig('agent_rsi_period', numberConfig('indicator_rsi_period', 14))));
      createIndicatorSafe('rsi', { name: 'RSI', calcParams: [period] }, 'bot_direct_rsi_pane', 90, 130);
    }

    if (boolConfig('agent_volume_enabled', false) || boolConfig('indicator_show_volume', false)) {
      registerDirectVolumeIndicator();
      createIndicatorSafe('volume', { name: 'BOT_VOLUME_DIRECT', id: 'BOT_VOLUME_DIRECT_MAIN' }, 'bot_direct_volume_pane', 100, 130);
    }

    if (boolConfig('agent_vwap_enabled', false) || boolConfig('indicator_show_vwap', false)) {
      if (!window.__botDirectAgentChartView.vwap) {
        const color = colorConfig('indicator_vwap_color', 'agent_vwap_color', '#14b8a6');
        window.__botDirectAgentChartView.vwap = createOverlaySafe('bot_direct_vwap_line', vwapPoints(candles), color) || 'attempted';
      }
    }

    applyChartHeight();

    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const base = Object.keys(window.__botNativeIndicators || {}).filter(key => window.__botNativeIndicators[key]);
      const direct = Object.keys(window.__botDirectAgentChartView || {}).filter(key => window.__botDirectAgentChartView[key]);
      const active = Array.from(new Set(base.concat(direct)));
      status.textContent = `KLineCharts · Agent-Indikatoren ${active.length ? active.join(' / ') : 'bereit'}`;
    }
  }

  function markDirectAgentGroups() {
    const view = document.getElementById('agentSetupView');
    const body = view?.querySelector('.configModalBody');
    if (!view || !body) return;
    const chartSections = ['rsi', 'vwap', 'volume'];
    const pureSections = ['breakout_fakeout', 'volatility_regime', 'risk'];
    chartSections.concat(pureSections).forEach(section => {
      const group = body.querySelector(`.agentDirectGroup[data-agent-section="${section}"]`);
      if (!group) return;
      const isChart = chartSections.includes(section);
      group.dataset.chartView = isChart ? 'true' : 'false';
      const grid = group.querySelector('.settingsGroupGrid');
      if (grid && !grid.querySelector('.agentChartModeBadge')) {
        const badge = document.createElement('div');
        badge.className = 'agentChartModeBadge fullWidth';
        badge.textContent = isChart ? 'Chart View aktivierbar' : 'Nur Bewertung / Risiko';
        grid.insertBefore(badge, grid.firstChild);
      }
    });
  }

  function renameDirectAgentSetupText() {
    const view = document.getElementById('agentSetupView');
    if (!view) return;
    view.querySelectorAll('.settingsGroup').forEach(block => {
      const title = block.querySelector(':scope > h3');
      const label = block.querySelector(':scope > .label');
      const titleText = String(title?.textContent || '').trim();
      if (!title || !/Direkte Agenten|Agenten ohne eigene Hauptchart-Linie/i.test(titleText)) return;
      title.textContent = 'Direkte Agenten';
      block.classList.add('agentSetupDirectHeader');
      if (label) {
        label.textContent = 'Chartfähig: RSI, VWAP, Volume. Nur Bewertung: Breakout/Fakeout, Volatility Regime, Risk.';
      }
    });
    markDirectAgentGroups();
  }

  function injectLayoutStyles() {
    const oldStyle = document.getElementById('direct-agent-chart-view-layout-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'direct-agent-chart-view-layout-style';
    style.textContent = `
      main { max-width:none !important; width:100% !important; }
      #chartView, #agentSetupView { width:100% !important; max-width:none !important; }
      #chartView > .card, #agentSetupView > .card { width:100% !important; max-width:none !important; overflow:visible !important; }
      #chartView .chartCanvasWrap { width:100% !important; min-height:980px !important; height:980px; max-height:none !important; overflow:visible !important; }
      #chartView #klineChart { width:100% !important; min-height:980px !important; height:980px; max-height:none !important; }
      #chartView #chartMeta { clear:both !important; margin-top:14px !important; }
      #agentSetupView .configModalBody { display:grid !important; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)) !important; gap:16px !important; align-items:start !important; grid-auto-flow:row dense !important; overflow:visible !important; padding:16px 14px 84px !important; }
      #agentSetupView .settingsTabsBar { grid-column:1 / -1 !important; width:100% !important; display:flex !important; flex-wrap:wrap !important; align-items:center !important; gap:8px !important; margin:0 0 10px !important; padding:0 0 14px !important; border-bottom:1px solid var(--line) !important; }
      #agentSetupView .settingsTabButton { min-width:128px !important; justify-content:center !important; }
      #agentSetupView .settingsGroup:not([data-agent-section]), #agentSetupView .agentSetupDirectHeader { grid-column:1 / -1 !important; }
      #agentSetupView .agentSetupDirectHeader { margin-top:4px !important; border-left:4px solid var(--accent) !important; }
      #agentSetupView .agentDirectGroup[data-chart-view="true"] { border-left:4px solid #22d3ee !important; }
      #agentSetupView .agentDirectGroup[data-chart-view="false"] { border-left:4px solid #fb923c !important; }
      #agentSetupView .agentChartModeBadge { display:inline-flex !important; align-items:center !important; min-height:24px !important; width:max-content !important; padding:3px 8px !important; border:1px solid var(--line) !important; border-radius:999px !important; background:var(--panel-soft) !important; color:var(--muted) !important; font-size:11px !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #agentSetupView .agentDirectGroup[data-chart-view="true"] .agentChartModeBadge { color:#67e8f9 !important; border-color:#0891b2 !important; background:rgba(8,145,178,.14) !important; }
      #agentSetupView .agentDirectGroup[data-chart-view="false"] .agentChartModeBadge { color:#fdba74 !important; border-color:#c2410c !important; background:rgba(194,65,12,.14) !important; }
      #agentSetupView .settingsGroup, #agentSetupView .agentIndicatorGroup, #agentSetupView .agentDirectGroup, #agentSetupView .agentUtilityGroup { min-height:0 !important; height:auto !important; align-content:start !important; contain:layout style !important; }
      #agentSetupView .settingsGroupGrid { align-items:start !important; }
      #agentSetupView .modalActions { position:sticky !important; bottom:0 !important; z-index:50 !important; display:flex !important; justify-content:flex-end !important; gap:10px !important; margin:0 -16px -16px !important; padding:16px 24px !important; border-top:1px solid var(--line) !important; background:linear-gradient(180deg, rgba(17,24,39,.90), rgba(17,24,39,.98)) !important; backdrop-filter:blur(8px) !important; }
      #agentSetupView .modalActions #saveAgentSettings { min-width:230px !important; box-shadow:0 -6px 20px rgba(0,0,0,.18) !important; }
      @media (max-width:900px) { main { padding:16px 12px 32px !important; } #agentSetupView .configModalBody { grid-template-columns:1fr !important; padding:12px 0 90px !important; } #agentSetupView .settingsTabButton { flex:1 1 140px !important; } #agentSetupView .modalActions { margin:0 -16px -16px !important; padding:12px 14px !important; } #agentSetupView .modalActions #saveAgentSettings { width:100% !important; } }
    `;
    document.head.appendChild(style);
  }

  function patchDrawChart() {
    if (window.drawChart?.__directAgentChartViewFixPatchedV5) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedDirectAgentChartViewDrawChart(candles, overlay, indicatorData) {
      clearDirectAgentChartView();
      const result = originalDrawChart.apply(this, arguments);
      ensureDirectAgentChartView(candles || []);
      renameDirectAgentSetupText();
      return result;
    };
    window.drawChart.__directAgentChartViewFixPatchedV5 = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__directAgentChartViewFixClearPatchedV5) return;
    originalClearKlineChart = window.clearKlineChart;
    if (typeof originalClearKlineChart !== 'function') return;
    window.clearKlineChart = function patchedDirectAgentChartViewClearChart() {
      clearDirectAgentChartView();
      return originalClearKlineChart.apply(this, arguments);
    };
    window.clearKlineChart.__directAgentChartViewFixClearPatchedV5 = true;
  }

  function install() {
    injectLayoutStyles();
    patchDrawChart();
    patchClearChart();
    renameDirectAgentSetupText();
    applyChartHeight();
    window.setTimeout(renameDirectAgentSetupText, 250);
    window.setTimeout(renameDirectAgentSetupText, 1000);
    window.setTimeout(applyChartHeight, 350);
    window.setTimeout(applyChartHeight, 1200);
    document.body.dataset.directAgentChartViewFixPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  window.addEventListener('resize', applyChartHeight);
})();
