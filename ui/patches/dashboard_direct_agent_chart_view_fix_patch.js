// ==================================================
// dashboard_direct_agent_chart_view_fix_patch.js
// ==================================================
// DIRECT AGENT CHART VIEW FIX PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-direct-agent-chart-view-fix-v2-layout-stable';
  let originalDrawChart = null;
  let originalClearKlineChart = null;

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

  function candleNumber(candle, key) {
    const number = Number(candle?.[key]);
    return Number.isFinite(number) ? number : 0;
  }

  function candleTime(candle) {
    const number = Number(candle?.timestamp ?? candle?.time ?? candle?.openTime);
    if (!Number.isFinite(number)) return null;
    return number > 1000000000000 ? Math.floor(number / 1000) : number;
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
    const height = Math.max(760, Math.min(1220, 620 + paneCount * 145));
    wrap.style.height = `${height}px`;
    wrap.style.minHeight = `${height}px`;
    chartEl.style.height = `${height}px`;
    chartEl.style.minHeight = `${height}px`;
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
    window.__botDirectAgentChartView = window.__botDirectAgentChartView || {};

    if (boolConfig('agent_rsi_enabled', false) || boolConfig('indicator_show_rsi', false)) {
      const period = Math.max(1, Math.floor(numberConfig('agent_rsi_period', numberConfig('indicator_rsi_period', 14))));
      createIndicatorSafe('rsi', { name: 'RSI', calcParams: [period] }, 'bot_direct_rsi_pane', 90, 130);
    }

    if (boolConfig('agent_volume_enabled', false) || boolConfig('indicator_show_volume', false)) {
      createIndicatorSafe('volume', 'VOL', 'bot_direct_volume_pane', 100, 120);
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

  function renameDirectAgentSetupText() {
    const view = document.getElementById('agentSetupView');
    if (!view) return;
    view.querySelectorAll('.settingsGroup').forEach(block => {
      const title = block.querySelector(':scope > h3');
      const label = block.querySelector(':scope > .label');
      const titleText = String(title?.textContent || '').trim();
      if (!title || !/Direkte Agenten|Agenten ohne eigene Hauptchart-Linie/i.test(titleText)) return;
      title.textContent = 'Direkte Agenten / Chart View';
      if (label) {
        label.textContent = 'RSI, VWAP und Volume besitzen Chart-View-Funktion. Breakout/Fakeout, Volatility und Risk bleiben reine Bewertungsagenten ohne eigenes Chart-Pane.';
      }
    });
  }

  function injectLayoutStyles() {
    const oldStyle = document.getElementById('direct-agent-chart-view-layout-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'direct-agent-chart-view-layout-style';
    style.textContent = `
      #chartView .chartCanvasWrap {
        min-height:760px !important;
        height:760px;
        overflow:hidden !important;
      }
      #chartView #klineChart {
        min-height:760px !important;
        height:760px;
      }
      #agentSetupView .configModalBody {
        align-items:start !important;
        grid-auto-flow:row dense !important;
      }
      #agentSetupView .settingsGroup,
      #agentSetupView .agentIndicatorGroup,
      #agentSetupView .agentDirectGroup,
      #agentSetupView .agentUtilityGroup {
        align-content:start !important;
        contain:layout style !important;
      }
      #agentSetupView .settingsGroupGrid {
        align-items:start !important;
      }
    `;
    document.head.appendChild(style);
  }

  function patchDrawChart() {
    if (window.drawChart?.__directAgentChartViewFixPatchedV2) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedDirectAgentChartViewDrawChart(candles, overlay, indicatorData) {
      clearDirectAgentChartView();
      const result = originalDrawChart.apply(this, arguments);
      ensureDirectAgentChartView(candles || []);
      renameDirectAgentSetupText();
      return result;
    };
    window.drawChart.__directAgentChartViewFixPatchedV2 = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__directAgentChartViewFixClearPatchedV2) return;
    originalClearKlineChart = window.clearKlineChart;
    if (typeof originalClearKlineChart !== 'function') return;
    window.clearKlineChart = function patchedDirectAgentChartViewClearChart() {
      clearDirectAgentChartView();
      return originalClearKlineChart.apply(this, arguments);
    };
    window.clearKlineChart.__directAgentChartViewFixClearPatchedV2 = true;
  }

  function install() {
    injectLayoutStyles();
    patchDrawChart();
    patchClearChart();
    renameDirectAgentSetupText();
    window.setTimeout(renameDirectAgentSetupText, 250);
    window.setTimeout(renameDirectAgentSetupText, 1000);
    document.body.dataset.directAgentChartViewFixPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
