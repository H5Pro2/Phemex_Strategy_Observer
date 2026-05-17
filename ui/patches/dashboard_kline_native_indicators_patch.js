// ==================================================
// dashboard_kline_native_indicators_patch.js
// ==================================================
// KLINECHARTS NATIVE INDICATOR PANE PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-kline-native-indicators-v1';
  let originalDrawChart = null;
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

  function hasIndicatorLine(indicatorData, needle) {
    const text = String(needle || '').toUpperCase();
    return (indicatorData?.lines || []).some(line => String(line?.name || line?.label || '').toUpperCase().includes(text));
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
        figures: [
          { key: 'mfi', title: 'MFI: ', type: 'line' }
        ],
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

  function createIndicatorSafe(chart, indicator, isStack, paneOptions) {
    if (!chart || typeof chart.createIndicator !== 'function') return null;
    try {
      return chart.createIndicator(indicator, isStack, paneOptions);
    } catch (_) {
      return null;
    }
  }

  function ensureNativeIndicators(indicatorData) {
    const chart = chartInstance();
    if (!chart || typeof chart.createIndicator !== 'function') return;
    const paneOptions = {
      id: 'bot_indicator_pane',
      height: 170,
      minHeight: 110,
      dragEnabled: true,
      order: 50,
      state: 'normal',
      axis: {
        name: 'right',
        position: 'right',
        inside: false,
        scrollZoomEnabled: true,
        gap: { top: 0.12, bottom: 0.12 }
      }
    };

    window.__botNativeIndicators = window.__botNativeIndicators || {};

    if (hasIndicatorLine(indicatorData, 'MACD') && !window.__botNativeIndicators.macd) {
      window.__botNativeIndicators.macd = createIndicatorSafe(chart, 'MACD', true, paneOptions) || 'attempted';
    }
    if (hasIndicatorLine(indicatorData, 'RSI') && !window.__botNativeIndicators.rsi) {
      window.__botNativeIndicators.rsi = createIndicatorSafe(chart, 'RSI', true, paneOptions) || 'attempted';
    }
    if (hasIndicatorLine(indicatorData, 'MFI') && !window.__botNativeIndicators.mfi) {
      registerMfiIndicator();
      window.__botNativeIndicators.mfi = createIndicatorSafe(chart, { name: 'BOT_MFI', id: 'BOT_MFI_MAIN', calcParams: [14] }, true, paneOptions) || 'attempted';
    }

    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const active = Object.keys(window.__botNativeIndicators).filter(key => window.__botNativeIndicators[key]).join(' / ');
      status.textContent = `KLineCharts · native Pane ${active || 'bereit'}`;
    }
  }

  function patchDrawChart() {
    if (window.drawChart?.__nativeIndicatorPatched) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedNativeIndicatorDrawChart(candles, overlay, indicatorData) {
      const result = originalDrawChart.apply(this, arguments);
      ensureNativeIndicators(indicatorData);
      return result;
    };
    window.drawChart.__nativeIndicatorPatched = true;
  }

  function install() {
    patchDrawChart();
    document.body.dataset.klineNativeIndicatorPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install);
  } else {
    install();
  }
})();
