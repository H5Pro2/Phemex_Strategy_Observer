// ==================================================
// dashboard_all_agent_indicators_patch.js
// ==================================================
// ALL DISPLAYABLE AGENT INDICATORS PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-all-agent-indicators-v1-safe';
  let originalDrawChart = null;
  let originalClearKlineChart = null;
  let mfiRegistered = false;

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

  function configValue(key, fallback = undefined) {
    if (window.latestConfig && Object.prototype.hasOwnProperty.call(window.latestConfig, key)) return window.latestConfig[key];
    if (window.latestStatusData?.config && Object.prototype.hasOwnProperty.call(window.latestStatusData.config, key)) return window.latestStatusData.config[key];
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

  function lineNames(indicatorData) {
    return (indicatorData?.lines || []).map(line => String(line?.name || line?.label || '').toUpperCase());
  }

  function hasLine(indicatorData, needle) {
    const text = String(needle || '').toUpperCase();
    return lineNames(indicatorData).some(name => name.includes(text));
  }

  function getLine(indicatorData, names) {
    const wanted = (names || []).map(name => String(name || '').toUpperCase());
    return (indicatorData?.lines || []).find(line => wanted.some(name => String(line?.name || '').toUpperCase().includes(name)));
  }

  function showIndicator(indicatorData, lineName, indicatorKey, agentKey, fallback = false) {
    if (hasLine(indicatorData, lineName)) return true;
    if (configValue(indicatorKey, undefined) !== undefined) return boolConfig(indicatorKey, fallback);
    return boolConfig(agentKey, fallback);
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

  function closeValues(candles) {
    return (Array.isArray(candles) ? candles : []).map(candle => candleNumber(candle, 'close'));
  }

  function ema(values, period) {
    const safe = Math.max(1, Math.floor(Number(period) || 1));
    const alpha = 2 / (safe + 1);
    let current = null;
    return values.map((value, index) => {
      current = current === null ? Number(value) : (Number(value) * alpha) + (current * (1 - alpha));
      return index + 1 >= safe ? current : null;
    });
  }

  function sma(values, period) {
    const safe = Math.max(1, Math.floor(Number(period) || 1));
    return values.map((_value, index) => {
      if (index + 1 < safe) return null;
      const windowValues = values.slice(index - safe + 1, index + 1);
      return windowValues.reduce((sum, value) => sum + Number(value), 0) / safe;
    });
  }

  function wma(values, period) {
    const safe = Math.max(1, Math.floor(Number(period) || 1));
    const denominator = safe * (safe + 1) / 2;
    return values.map((_value, index) => {
      if (index + 1 < safe) return null;
      const windowValues = values.slice(index - safe + 1, index + 1);
      return windowValues.reduce((sum, value, offset) => sum + Number(value) * (offset + 1), 0) / denominator;
    });
  }

  function hma(values, period) {
    const safe = Math.max(1, Math.floor(Number(period) || 1));
    const half = wma(values, Math.max(1, Math.floor(safe / 2)));
    const full = wma(values, safe);
    const raw = values.map((_value, index) => half[index] === null || full[index] === null ? null : (2 * half[index]) - full[index]);
    const rawSource = raw.map((value, index) => value === null ? values[index] : value);
    const result = wma(rawSource, Math.max(1, Math.floor(Math.sqrt(safe))));
    return result.map((value, index) => raw[index] === null ? null : value);
  }

  function tripleEma(values, period) {
    const safe = Math.max(1, Math.floor(Number(period) || 1));
    const ema1 = ema(values, safe);
    const ema1Source = ema1.map((value, index) => value === null ? values[index] : value);
    const ema2 = ema(ema1Source, safe);
    const ema2Source = ema2.map((value, index) => value === null ? ema1Source[index] : value);
    const ema3 = ema(ema2Source, safe);
    return values.map((_value, index) => {
      if (index + 1 < safe * 3 || ema1[index] === null || ema2[index] === null || ema3[index] === null) return null;
      return (3 * ema1[index]) - (3 * ema2[index]) + ema3[index];
    });
  }

  function pointsFromValues(candles, values) {
    const typed = Array.isArray(candles) ? candles : [];
    return typed.map((candle, index) => {
      const timestamp = candleTime(candle);
      const value = Number(values[index]);
      if (timestamp === null || !Number.isFinite(value)) return null;
      return { timestamp, value };
    }).filter(Boolean);
  }

  function createOverlay(chart, id, points, color) {
    if (!chart || typeof chart.createOverlay !== 'function' || !points.length) return null;
    try {
      chart.createOverlay({
        name: 'segment',
        id,
        points,
        styles: { line: { color: color || '#94a3b8', size: 1 } }
      });
      return { type: 'overlay', id };
    } catch (_) {
      return null;
    }
  }

  function removeItem(chart, value) {
    if (!value || value === 'attempted') return;
    if (Array.isArray(value)) {
      value.forEach(item => removeItem(chart, item));
      return;
    }
    if (typeof value === 'object' && value.type === 'overlay') {
      if (typeof chart?.removeOverlay === 'function') {
        try { chart.removeOverlay({ id: value.id }); return; } catch (_) {}
        try { chart.removeOverlay(value.id); return; } catch (_) {}
      }
      return;
    }
    if (typeof chart?.removeIndicator === 'function') {
      try { chart.removeIndicator(value); } catch (_) {}
    }
  }

  function removeAllAgentIndicators() {
    const chart = chartInstance();
    const active = window.__botNativeIndicators || {};
    if (!chart) {
      window.__botNativeIndicators = {};
      return;
    }
    Object.values(active).forEach(value => removeItem(chart, value));
    window.__botNativeIndicators = {};
  }

  function overlayFromLine(indicatorData, names, id, color) {
    const chart = chartInstance();
    const line = getLine(indicatorData, names);
    if (!chart || !line) return null;
    const points = (line.series || [])
      .map(point => ({ timestamp: point.timestamp, value: point.value }))
      .filter(point => Number.isFinite(Number(point.value)));
    return createOverlay(chart, id, points, line.color || color);
  }

  function calculatedOverlay(candles, id, values, color) {
    return createOverlay(chartInstance(), id, pointsFromValues(candles, values), color) || 'attempted';
  }

  function addAverage(candles, indicatorData, storageKey, lineNamesList, period, builder, colorKey, agentColorKey, fallbackColor) {
    if (window.__botNativeIndicators?.[storageKey]) return;
    const color = colorConfig(colorKey, agentColorKey, fallbackColor);
    const fromLine = overlayFromLine(indicatorData, lineNamesList, `bot_${storageKey}_line`, color);
    window.__botNativeIndicators[storageKey] = fromLine || calculatedOverlay(candles, `bot_${storageKey}_line`, builder(closeValues(candles), period), color);
  }

  function registerMfi() {
    if (mfiRegistered) return;
    const api = apiInstance();
    if (!api || typeof api.registerIndicator !== 'function') return;
    try {
      api.registerIndicator({
        name: 'BOT_MFI',
        shortName: 'MFI',
        series: 'normal',
        precision: 2,
        calcParams: [14],
        minValue: 0,
        maxValue: 100,
        figures: [{ key: 'mfi', title: 'MFI: ', type: 'line' }],
        calc: (dataList, indicator) => {
          const period = Math.max(1, Number(indicator?.calcParams?.[0] || 14));
          const typical = dataList.map(k => (Number(k.high) + Number(k.low) + Number(k.close)) / 3);
          const flow = dataList.map((k, index) => typical[index] * Number(k.volume || 0));
          const positive = [0];
          const negative = [0];
          for (let index = 1; index < dataList.length; index += 1) {
            if (typical[index] > typical[index - 1]) {
              positive.push(flow[index]);
              negative.push(0);
            } else if (typical[index] < typical[index - 1]) {
              positive.push(0);
              negative.push(flow[index]);
            } else {
              positive.push(0);
              negative.push(0);
            }
          }
          return dataList.map((_k, index) => {
            if (index + 1 < period) return { mfi: null };
            const start = index - period + 1;
            const pos = positive.slice(start, index + 1).reduce((sum, value) => sum + value, 0);
            const neg = negative.slice(start, index + 1).reduce((sum, value) => sum + value, 0);
            if (pos <= 0 && neg <= 0) return { mfi: 50 };
            if (neg <= 0) return { mfi: 100 };
            return { mfi: 100 - (100 / (1 + pos / neg)) };
          });
        }
      });
      mfiRegistered = true;
    } catch (_) {
      mfiRegistered = true;
    }
  }

  function pane(id, order, height) {
    return {
      id,
      height,
      minHeight: 96,
      dragEnabled: true,
      order,
      state: 'normal',
      axis: { name: 'right', position: 'right', inside: false, scrollZoomEnabled: true, gap: { top: 0.12, bottom: 0.12 } }
    };
  }

  function createIndicator(name, storageKey, indicator, paneId, order, height) {
    const chart = chartInstance();
    if (!chart || typeof chart.createIndicator !== 'function' || window.__botNativeIndicators?.[storageKey]) return;
    try {
      window.__botNativeIndicators[storageKey] = chart.createIndicator(indicator || name, false, pane(paneId, order, height)) || 'attempted';
    } catch (_) {
      window.__botNativeIndicators[storageKey] = 'attempted';
    }
  }

  function ensureAllAgentIndicators(candles, indicatorData) {
    const chart = chartInstance();
    if (!chart) return;
    window.__botNativeIndicators = window.__botNativeIndicators || {};

    if (showIndicator(indicatorData, 'HMA', 'indicator_show_hma', 'agent_hma_enabled', false)) {
      addAverage(candles, indicatorData, 'hma', ['HMA'], numberConfig('indicator_hma_period', 20), hma, 'indicator_hma_color', 'agent_hma_color', '#7c3aed');
    }

    if (showIndicator(indicatorData, 'SMA', 'indicator_show_sma', 'agent_sma_enabled', false)) {
      addAverage(candles, indicatorData, 'sma', ['SMA'], numberConfig('indicator_sma_period', numberConfig('agent_sma_period', 50)), sma, 'indicator_sma_color', 'agent_sma_color', '#06b6d4');
    }

    if (showIndicator(indicatorData, 'TRIPLE_EMA', 'indicator_show_triple_ema', 'agent_triple_ema_enabled', false)) {
      addAverage(candles, indicatorData, 'tripleEmaFast', ['TRIPLE_EMA_FAST'], numberConfig('indicator_triple_ema_period', 20), tripleEma, 'indicator_triple_ema_color', 'agent_triple_ema_color', '#d97706');
      addAverage(candles, indicatorData, 'tripleEmaSlow', ['TRIPLE_EMA_SLOW'], numberConfig('indicator_triple_ema_slow_period', 50), tripleEma, 'indicator_triple_ema_slow_color', 'agent_triple_ema_color', '#2563eb');
    }

    if (showIndicator(indicatorData, 'MACD', 'indicator_show_macd', 'agent_macd_enabled', false)) {
      const fast = Math.max(1, Math.floor(numberConfig('indicator_macd_fast_period', 12)));
      const slow = Math.max(fast + 1, Math.floor(numberConfig('indicator_macd_slow_period', 26)));
      const signal = Math.max(1, Math.floor(numberConfig('indicator_macd_signal_period', 9)));
      createIndicator('MACD', 'macd', { name: 'MACD', calcParams: [fast, slow, signal] }, 'bot_macd_pane', 50, 150);
    }

    if (showIndicator(indicatorData, 'RSI', 'indicator_show_rsi', 'agent_rsi_enabled', false)) {
      createIndicator('RSI', 'rsi', { name: 'RSI', calcParams: [Math.max(1, Math.floor(numberConfig('agent_rsi_period', numberConfig('indicator_rsi_period', 14))))] }, 'bot_rsi_pane', 60, 130);
    }

    if (showIndicator(indicatorData, 'MFI', 'indicator_show_mfi', 'agent_mfi_enabled', false)) {
      registerMfi();
      createIndicator('BOT_MFI', 'mfi', { name: 'BOT_MFI', id: 'BOT_MFI_MAIN', calcParams: [Math.max(1, Math.floor(numberConfig('agent_mfi_period', numberConfig('indicator_mfi_period', 14))))] }, 'bot_mfi_pane', 70, 130);
    }

    if (showIndicator(indicatorData, 'VOLUME', 'indicator_show_volume', 'agent_volume_enabled', false)) {
      createIndicator('VOL', 'volume', 'VOL', 'bot_volume_pane', 80, 120);
    }

    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const active = Object.keys(window.__botNativeIndicators).filter(key => window.__botNativeIndicators[key]).join(' / ');
      status.textContent = `KLineCharts · Agent-Indikatoren ${active || 'bereit'}`;
    }
  }

  function patchDrawChart() {
    if (window.drawChart?.__allAgentIndicatorsPatched) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedAllAgentIndicatorsDrawChart(candles, overlay, indicatorData) {
      const result = originalDrawChart.apply(this, arguments);
      ensureAllAgentIndicators(candles, indicatorData);
      return result;
    };
    window.drawChart.__allAgentIndicatorsPatched = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__allAgentIndicatorsClearPatched) return;
    originalClearKlineChart = window.clearKlineChart;
    if (typeof originalClearKlineChart !== 'function') return;
    window.clearKlineChart = function patchedAllAgentIndicatorsClearChart() {
      removeAllAgentIndicators();
      return originalClearKlineChart.apply(this, arguments);
    };
    window.clearKlineChart.__allAgentIndicatorsClearPatched = true;
  }

  function install() {
    patchDrawChart();
    patchClearChart();
    document.body.dataset.allAgentIndicatorsPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();