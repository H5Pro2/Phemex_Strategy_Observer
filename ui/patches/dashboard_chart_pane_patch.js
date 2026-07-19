// ==================================================
// dashboard_chart_pane_patch.js
// ==================================================
// CHART CONTROL PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-chart-controls-v2-tech';
  const STORAGE_KEY_AUTOSCROLL = 'tradingBotChartAutoScroll';
  let originalDrawChart = null;
  let originalInitKlineChart = null;

  function enabled(value, fallback = true) {
    const text = String(value ?? '').toLowerCase();
    if (text === 'false' || text === '0' || text === 'off') return false;
    if (text === 'true' || text === '1' || text === 'on') return true;
    return fallback;
  }

  function autoScrollEnabled() {
    return enabled(localStorage.getItem(STORAGE_KEY_AUTOSCROLL), true);
  }

  function setAutoScroll(active) {
    localStorage.setItem(STORAGE_KEY_AUTOSCROLL, active ? 'true' : 'false');
    updateToolbarState();
  }

  function chartInstance() {
    if (window.__klineChartInstance) return window.__klineChartInstance;
    try {
      if (typeof window.initKlineChart === 'function') return window.initKlineChart();
    } catch (_) {}
    return null;
  }

  function callChart(method, ...args) {
    const chart = chartInstance();
    if (!chart || typeof chart[method] !== 'function') return false;
    try {
      chart[method](...args);
      return true;
    } catch (_) {
      return false;
    }
  }

  function applyAutoScroll() {
    if (!autoScrollEnabled()) return;
    if (callChart('scrollToRealTime')) return;
    callChart('setOffsetRightDistance', 8);
  }

  function deleteOldCanvasPane() {
    ['chartOscillatorPane', 'chartOscillatorCanvas', 'chartOscillatorLegend'].forEach(id => {
      const element = document.getElementById(id);
      if (element && element.parentNode) element.parentNode.removeChild(element);
    });
  }

  function ensureToolbar() {
    if (document.getElementById('chartTechnicalToolbar')) return;
    const chart = document.getElementById('klineChart');
    if (!chart) return;
    const toolbar = document.createElement('div');
    toolbar.id = 'chartTechnicalToolbar';
    toolbar.className = 'chartTechnicalToolbar';
    toolbar.innerHTML = [
      '<div class="chartTechTitle">Chart Bedienung</div>',
      '<button type="button" id="chartAutoScrollToggle" class="chartTechButton">Auto-Scroll</button>',
      '<button type="button" id="chartRealtimeButton" class="chartTechButton">Realtime</button>',
      '<button type="button" id="chartZoomInButton" class="chartTechButton">Zoom +</button>',
      '<button type="button" id="chartZoomOutButton" class="chartTechButton">Zoom -</button>',
      '<button type="button" id="chartResizeButton" class="chartTechButton">Fit</button>',
      '<span id="chartPluginStatus" class="chartPluginStatus">KLineCharts</span>'
    ].join('');
    chart.parentNode.insertBefore(toolbar, chart);

    document.getElementById('chartAutoScrollToggle')?.addEventListener('click', () => {
      setAutoScroll(!autoScrollEnabled());
      applyAutoScroll();
    });
    document.getElementById('chartRealtimeButton')?.addEventListener('click', () => {
      setAutoScroll(true);
      applyAutoScroll();
    });
    document.getElementById('chartResizeButton')?.addEventListener('click', () => {
      if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart();
      applyAutoScroll();
    });
    document.getElementById('chartZoomInButton')?.addEventListener('click', () => {
      if (!callChart('zoomAtCoordinate', 1.18, { x: Math.floor((document.getElementById('klineChart')?.clientWidth || 800) / 2), y: 160 })) callChart('zoom', 1.18);
    });
    document.getElementById('chartZoomOutButton')?.addEventListener('click', () => {
      if (!callChart('zoomAtCoordinate', 0.84, { x: Math.floor((document.getElementById('klineChart')?.clientWidth || 800) / 2), y: 160 })) callChart('zoom', 0.84);
    });
    updateToolbarState();
  }

  function updateToolbarState() {
    const auto = document.getElementById('chartAutoScrollToggle');
    if (auto) {
      auto.classList.toggle('active', autoScrollEnabled());
      auto.textContent = autoScrollEnabled() ? 'Auto-Scroll AN' : 'Auto-Scroll AUS';
    }
    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const chart = chartInstance();
      const methods = ['scrollToRealTime', 'zoomAtCoordinate', 'resize', 'createIndicator', 'createOverlay'].filter(name => typeof chart?.[name] === 'function');
      status.textContent = `KLineCharts | ${methods.length ? methods.join(' / ') : 'Basis'}`;
    }
  }

  function injectStyles() {
    const oldStyle = document.getElementById('chart-pane-technical-style');
    if (oldStyle && oldStyle.parentNode) oldStyle.parentNode.removeChild(oldStyle);
    const style = document.createElement('style');
    style.id = 'chart-pane-technical-style';
    style.textContent = '.chartTechnicalToolbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0 10px;padding:8px;border:1px solid rgba(148,163,184,.18);border-radius:4px;background:rgba(15,23,42,.10)}.chartTechTitle{font-size:10px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-right:4px}.chartTechButton{min-height:28px;padding:5px 8px;border-radius:3px;font-size:11px;font-family:Arial,sans-serif;background:rgba(30,41,59,.72);color:#cbd5e1;border:1px solid rgba(148,163,184,.22)}.chartTechButton.active{color:#ecfeff;border-color:#0f766e;background:#0f766e}.chartPluginStatus{display:none}';
    document.head.appendChild(style);
  }

  function patchInitKlineChart() {
    if (window.initKlineChart?.__chartControlsPatched) return;
    originalInitKlineChart = window.initKlineChart;
    if (typeof originalInitKlineChart !== 'function') return;
    window.initKlineChart = function patchedInitKlineChart(...args) {
      const chart = originalInitKlineChart.apply(this, args);
      window.__klineChartInstance = chart;
      updateToolbarState();
      return chart;
    };
    window.initKlineChart.__chartControlsPatched = true;
  }

  function patchDrawChart() {
    if (window.drawChart?.__chartControlsPatched) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedDrawChart() {
      const result = originalDrawChart.apply(this, arguments);
      ensureToolbar();
      deleteOldCanvasPane();
      applyAutoScroll();
      return result;
    };
    window.drawChart.__chartControlsPatched = true;
  }

  function install() {
    injectStyles();
    deleteOldCanvasPane();
    ensureToolbar();
    patchInitKlineChart();
    patchDrawChart();
    document.body.dataset.chartPanePatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
