// ==================================================
// dashboard_kline_native_indicators_patch.js
// ==================================================
// KLINECHARTS NATIVE INDICATOR PANE PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-kline-native-indicators-v4-direct-agent-display';
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

  function indicatorNames(indicatorData) {
    return (indicatorData?.lines || []).map(line => String(line?.name || line?.label || '').toUpperCase());
  }

  function hasIndicatorLine(indicatorData, needle) {
    const text = String(needle || '').toUpperCase();
    return indicatorNames(indicatorData).some(name => name.includes(text));
  }

  function shouldShowDirectIndicator(indicatorData, lineName, indicatorKey, agentKey, defaultValue = false) {
    if (hasIndicatorLine(indicatorData, lineName)) return true;
    const explicitIndicatorValue = configValue(indicatorKey, undefined);
    if (explicitIndicatorValue !== undefined) return boolConfig(indicatorKey, defaultValue);
    return boolConfig(agentKey, defaultValue);
  }

  function candleNumber(candle, key) {
    const value = candle?.[key];
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function candleTime(candle) {
    const value = candle?.timestamp ?? candle?.time ?? candle?.openTime;
    const number = Number(value);
    if (!Number.isFinite(number)) return null;
    return number > 1000000000000 ? Math.floor(number / 1000) : number;
  }

  function registerMfiIndicator() {
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
            const positiveFlow = positive.slice(start, index + 1).reduce((sum, value) => sum + value, 0);
            const negativeFlow = negative.slice(start, index + 1).reduce((sum, value) => sum + value, 0);
            if (positiveFlow <= 0 && negativeFlow <= 0) return { mfi: 50 };
            if (negativeFlow <= 0) return { mfi: 100 };
            const ratio = positiveFlow / negativeFlow;
            return { mfi: 100 - (100 / (1 + ratio)) };
          });
        }
      });
      mfiRegistered = true;
    } catch (_) {
      mfiRegistered = true;
    }
  }

  function paneOptions(id, order, height) {
    return {
      id,
      height,
      minHeight: 96,
      dragEnabled: true,
      order,
      state: 'normal',
      axis: {
        name: 'right',
        position: 'right',
        inside: false,
        scrollZoomEnabled: true,
        gap: { top: 0.12, bottom: 0.12 }
      }
    };
  }

  function createIndicatorSafe(chart, indicator, paneId, order, height) {
    if (!chart || typeof chart.createIndicator !== 'function') return null;
    try {
      return chart.createIndicator(indicator, false, paneOptions(paneId, order, height));
    } catch (_) {
      return null;
    }
  }

  function removeTrackedChartItem(chart, value) {
    if (!value || value === 'attempted') return;
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

  function clearBotIndicators() {
    const chart = chartInstance();
    const active = window.__botNativeIndicators || {};
    if (!chart) {
      window.__botNativeIndicators = {};
      return;
    }
    Object.values(active).forEach(value => removeTrackedChartItem(chart, value));
    window.__botNativeIndicators = {};
  }

  function createOverlaySafe(chart, id, points, color) {
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

  function addPriceLineFromData(indicatorData, names) {
    const chart = chartInstance();
    if (!chart || typeof chart.createOverlay !== 'function') return 'attempted';
    const lines = (indicatorData?.lines || []).filter(line => names.some(name => String(line?.name || '').toUpperCase().includes(name)));
    let created = null;
    lines.forEach(line => {
      const points = (line.series || []).map(point => ({ timestamp: point.timestamp, value: point.value })).filter(point => Number.isFinite(Number(point.value)));
      if (!points.length) return;
      const id = `bot_${String(line.name).toLowerCase()}_line`;
      created = createOverlaySafe(chart, id, points, line.color || '#94a3b8') || created;
    });
    return created || null;
  }

  function vwapPointsFromCandles(candles) {
    const lookback = Math.max(1, Math.floor(numberConfig('agent_vwap_lookback_candles', numberConfig('indicator_vwap_lookback_candles', 96))));
    const result = [];
    const typed = Array.isArray(candles) ? candles : [];
    for (let index = 0; index < typed.length; index += 1) {
      const start = Math.max(0, index - lookback + 1);
      let volumeSum = 0;
      let weightedSum = 0;
      for (let pos = start; pos <= index; pos += 1) {
        const candle = typed[pos];
        const high = candleNumber(candle, 'high');
        const low = candleNumber(candle, 'low');
        const close = candleNumber(candle, 'close');
        const volume = candleNumber(candle, 'volume');
        if (volume <= 0) continue;
        weightedSum += ((high + low + close) / 3) * volume;
        volumeSum += volume;
      }
      const timestamp = candleTime(typed[index]);
      if (timestamp !== null && volumeSum > 0) {
        result.push({ timestamp, value: weightedSum / volumeSum });
      }
    }
    return result;
  }

  function addVwapOverlay(candles, indicatorData) {
    const fromData = addPriceLineFromData(indicatorData, ['VWAP']);
    if (fromData) return fromData;
    const chart = chartInstance();
    const color = colorConfig('indicator_vwap_color', 'agent_vwap_color', '#14b8a6');
    const points = vwapPointsFromCandles(candles);
    return createOverlaySafe(chart, 'bot_vwap_agent_line', points, color) || 'attempted';
  }

  function ensureNativeIndicators(candles, indicatorData) {
    const chart = chartInstance();
    if (!chart || typeof chart.createIndicator !== 'function') return;
    window.__botNativeIndicators = window.__botNativeIndicators || {};

    const showMacd = hasIndicatorLine(indicatorData, 'MACD');
    const showMfi = hasIndicatorLine(indicatorData, 'MFI');
    const showRsi = shouldShowDirectIndicator(indicatorData, 'RSI', 'indicator_show_rsi', 'agent_rsi_enabled', false);
    const showVolume = shouldShowDirectIndicator(indicatorData, 'VOLUME', 'indicator_show_volume', 'agent_volume_enabled', false);
    const showVwap = shouldShowDirectIndicator(indicatorData, 'VWAP', 'indicator_show_vwap', 'agent_vwap_enabled', false);

    if (showMacd && !window.__botNativeIndicators.macd) {
      window.__botNativeIndicators.macd = createIndicatorSafe(chart, 'MACD', 'bot_macd_pane', 50, 150) || 'attempted';
    }
    if (showRsi && !window.__botNativeIndicators.rsi) {
      const period = Math.max(1, Math.floor(numberConfig('agent_rsi_period', numberConfig('indicator_rsi_period', 14))));
      window.__botNativeIndicators.rsi = createIndicatorSafe(chart, { name: 'RSI', calcParams: [period] }, 'bot_rsi_pane', 60, 130) || 'attempted';
    }
    if (showMfi && !window.__botNativeIndicators.mfi) {
      registerMfiIndicator();
      const period = Math.max(1, Math.floor(numberConfig('agent_mfi_period', numberConfig('indicator_mfi_period', 14))));
      window.__botNativeIndicators.mfi = createIndicatorSafe(chart, { name: 'BOT_MFI', id: 'BOT_MFI_MAIN', calcParams: [period] }, 'bot_mfi_pane', 70, 130) || 'attempted';
    }
    if (showVolume && !window.__botNativeIndicators.volume) {
      window.__botNativeIndicators.volume = createIndicatorSafe(chart, 'VOL', 'bot_volume_pane', 80, 120) || 'attempted';
    }
    if (showVwap && !window.__botNativeIndicators.vwap) {
      window.__botNativeIndicators.vwap = addVwapOverlay(candles, indicatorData) || 'attempted';
    }

    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const active = Object.keys(window.__botNativeIndicators).filter(key => window.__botNativeIndicators[key]).join(' / ');
      status.textContent = `KLineCharts · Indikatoren ${active || 'bereit'}`;
    }
  }

  function patchDrawChart() {
    if (window.drawChart?.__nativeIndicatorPatchedV4) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedNativeIndicatorDrawChart(candles, overlay, indicatorData) {
      clearBotIndicators();
      const result = originalDrawChart.apply(this, arguments);
      ensureNativeIndicators(candles, indicatorData);
      return result;
    };
    window.drawChart.__nativeIndicatorPatchedV4 = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__nativeIndicatorClearPatchedV4) return;
    originalClearKlineChart = window.clearKlineChart;
    if (typeof originalClearKlineChart !== 'function') return;
    window.clearKlineChart = function patchedClearKlineChart() {
      clearBotIndicators();
      return originalClearKlineChart.apply(this, arguments);
    };
    window.clearKlineChart.__nativeIndicatorClearPatchedV4 = true;
  }

  function install() {
    patchDrawChart();
    patchClearChart();
    document.body.dataset.klineNativeIndicatorPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();