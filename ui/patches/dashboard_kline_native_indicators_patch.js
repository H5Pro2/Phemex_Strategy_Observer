// ==================================================
// dashboard_kline_native_indicators_patch.js
// ==================================================
// KLINECHARTS NATIVE INDICATOR PANE PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-kline-native-indicators-v3-full';
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

  function indicatorNames(indicatorData) {
    return (indicatorData?.lines || []).map(line => String(line?.name || line?.label || '').toUpperCase());
  }

  function hasIndicatorLine(indicatorData, needle) {
    const text = String(needle || '').toUpperCase();
    return indicatorNames(indicatorData).some(name => name.includes(text));
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

  function clearBotIndicators() {
    const chart = chartInstance();
    const active = window.__botNativeIndicators || {};
    if (!chart || typeof chart.removeIndicator !== 'function') {
      window.__botNativeIndicators = {};
      return;
    }
    Object.values(active).forEach(value => {
      if (!value || value === 'attempted') return;
      try { chart.removeIndicator(value); } catch (_) {}
    });
    window.__botNativeIndicators = {};
  }

  function addPriceLineFromData(indicatorData, names) {
    const chart = chartInstance();
    if (!chart || typeof chart.createOverlay !== 'function') return 'attempted';
    const lines = (indicatorData?.lines || []).filter(line => names.some(name => String(line?.name || '').toUpperCase().includes(name)));
    lines.forEach(line => {
      const points = (line.series || []).map(point => ({ timestamp: point.timestamp, value: point.value })).filter(point => Number.isFinite(Number(point.value)));
      if (!points.length) return;
      try {
        chart.createOverlay({ name: 'segment', id: `bot_${String(line.name).toLowerCase()}_line`, points, styles: { line: { color: line.color || '#94a3b8', size: 1 } } });
      } catch (_) {}
    });
    return lines.length ? 'overlay' : null;
  }

  function ensureNativeIndicators(indicatorData) {
    const chart = chartInstance();
    if (!chart || typeof chart.createIndicator !== 'function') return;
    window.__botNativeIndicators = window.__botNativeIndicators || {};

    if (hasIndicatorLine(indicatorData, 'MACD') && !window.__botNativeIndicators.macd) {
      window.__botNativeIndicators.macd = createIndicatorSafe(chart, 'MACD', 'bot_macd_pane', 50, 150) || 'attempted';
    }
    if (hasIndicatorLine(indicatorData, 'RSI') && !window.__botNativeIndicators.rsi) {
      window.__botNativeIndicators.rsi = createIndicatorSafe(chart, 'RSI', 'bot_rsi_pane', 60, 130) || 'attempted';
    }
    if (hasIndicatorLine(indicatorData, 'MFI') && !window.__botNativeIndicators.mfi) {
      registerMfiIndicator();
      window.__botNativeIndicators.mfi = createIndicatorSafe(chart, { name: 'BOT_MFI', id: 'BOT_MFI_MAIN', calcParams: [14] }, 'bot_mfi_pane', 70, 130) || 'attempted';
    }
    if (hasIndicatorLine(indicatorData, 'VOLUME') && !window.__botNativeIndicators.volume) {
      window.__botNativeIndicators.volume = createIndicatorSafe(chart, 'VOL', 'bot_volume_pane', 80, 120) || 'attempted';
    }
    if (hasIndicatorLine(indicatorData, 'VWAP') && !window.__botNativeIndicators.vwap) {
      window.__botNativeIndicators.vwap = addPriceLineFromData(indicatorData, ['VWAP']) || 'attempted';
    }

    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const active = Object.keys(window.__botNativeIndicators).filter(key => window.__botNativeIndicators[key]).join(' / ');
      status.textContent = `KLineCharts · Indikatoren ${active || 'bereit'}`;
    }
  }

  function patchDrawChart() {
    if (window.drawChart?.__nativeIndicatorPatchedV3) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedNativeIndicatorDrawChart(candles, overlay, indicatorData) {
      clearBotIndicators();
      const result = originalDrawChart.apply(this, arguments);
      ensureNativeIndicators(indicatorData);
      return result;
    };
    window.drawChart.__nativeIndicatorPatchedV3 = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__nativeIndicatorClearPatched) return;
    originalClearKlineChart = window.clearKlineChart;
    if (typeof originalClearKlineChart !== 'function') return;
    window.clearKlineChart = function patchedClearKlineChart() {
      clearBotIndicators();
      return originalClearKlineChart.apply(this, arguments);
    };
    window.clearKlineChart.__nativeIndicatorClearPatched = true;
  }

  function install() {
    patchDrawChart();
    patchClearChart();
    document.body.dataset.klineNativeIndicatorPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
