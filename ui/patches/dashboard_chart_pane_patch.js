// ==================================================
// dashboard_chart_pane_patch.js
// ==================================================
// CHART SECOND-PANE / CONTROL PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-chart-pane-v1-tech';
  const STORAGE_KEY_AUTOSCROLL = 'tradingBotChartAutoScroll';
  const STORAGE_KEY_OSC = 'tradingBotChartOscillatorPane';
  let originalDrawChart = null;
  let originalInitKlineChart = null;

  function chartPatchEnabled(value, fallback = true) {
    const text = String(value ?? '').toLowerCase();
    if (text === 'false' || text === '0' || text === 'off') return false;
    if (text === 'true' || text === '1' || text === 'on') return true;
    return fallback;
  }

  function autoScrollEnabled() {
    return chartPatchEnabled(localStorage.getItem(STORAGE_KEY_AUTOSCROLL), true);
  }

  function oscillatorPaneEnabled() {
    return chartPatchEnabled(localStorage.getItem(STORAGE_KEY_OSC), true);
  }

  function setAutoScrollEnabled(active) {
    localStorage.setItem(STORAGE_KEY_AUTOSCROLL, active ? 'true' : 'false');
    updateToolbarState();
  }

  function setOscillatorPaneEnabled(active) {
    localStorage.setItem(STORAGE_KEY_OSC, active ? 'true' : 'false');
    updateToolbarState();
    if (window.__chartPaneLastRows && window.__chartPaneLastIndicatorData) {
      renderOscillatorPane(window.__chartPaneLastRows, window.__chartPaneLastIndicatorData);
    }
  }

  function chartInstance() {
    if (window.__klineChartInstance) return window.__klineChartInstance;
    try {
      if (typeof window.initKlineChart === 'function') {
        return window.initKlineChart();
      }
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
    const chart = chartInstance();
    if (!chart) return;
    if (callChart('scrollToRealTime')) return;
    if (callChart('setOffsetRightDistance', 8)) return;
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
      '<button type="button" id="chartOscillatorToggle" class="chartTechButton">2. Pane</button>',
      '<span id="chartPluginStatus" class="chartPluginStatus">KLineCharts</span>'
    ].join('');
    chart.parentNode.insertBefore(toolbar, chart);

    document.getElementById('chartAutoScrollToggle')?.addEventListener('click', () => {
      setAutoScrollEnabled(!autoScrollEnabled());
      applyAutoScroll();
    });
    document.getElementById('chartOscillatorToggle')?.addEventListener('click', () => {
      setOscillatorPaneEnabled(!oscillatorPaneEnabled());
    });
    document.getElementById('chartRealtimeButton')?.addEventListener('click', () => {
      setAutoScrollEnabled(true);
      applyAutoScroll();
    });
    document.getElementById('chartResizeButton')?.addEventListener('click', () => {
      if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart();
      renderOscillatorPane(window.__chartPaneLastRows || [], window.__chartPaneLastIndicatorData || null);
      applyAutoScroll();
    });
    document.getElementById('chartZoomInButton')?.addEventListener('click', () => {
      if (!callChart('zoomAtCoordinate', 1.18, { x: Math.floor((document.getElementById('klineChart')?.clientWidth || 800) / 2), y: 160 })) {
        callChart('zoom', 1.18);
      }
    });
    document.getElementById('chartZoomOutButton')?.addEventListener('click', () => {
      if (!callChart('zoomAtCoordinate', 0.84, { x: Math.floor((document.getElementById('klineChart')?.clientWidth || 800) / 2), y: 160 })) {
        callChart('zoom', 0.84);
      }
    });
    updateToolbarState();
  }

  function updateToolbarState() {
    const auto = document.getElementById('chartAutoScrollToggle');
    const osc = document.getElementById('chartOscillatorToggle');
    if (auto) {
      auto.classList.toggle('active', autoScrollEnabled());
      auto.textContent = autoScrollEnabled() ? 'Auto-Scroll AN' : 'Auto-Scroll AUS';
    }
    if (osc) {
      osc.classList.toggle('active', oscillatorPaneEnabled());
      osc.textContent = oscillatorPaneEnabled() ? '2. Pane AN' : '2. Pane AUS';
    }
    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const chart = chartInstance();
      const methods = ['scrollToRealTime', 'zoomAtCoordinate', 'resize', 'createOverlay'].filter(name => typeof chart?.[name] === 'function');
      status.textContent = `KLineCharts · ${methods.length ? methods.join(' / ') : 'Basis'}`;
    }
  }

  function ensureOscillatorPane() {
    let pane = document.getElementById('chartOscillatorPane');
    if (pane) return pane;
    const chart = document.getElementById('klineChart');
    if (!chart) return null;
    pane = document.createElement('div');
    pane.id = 'chartOscillatorPane';
    pane.className = 'chartOscillatorPane';
    pane.innerHTML = '<div class="chartPaneHeader"><strong>Indikator-Pane</strong><span>MACD / MFI</span></div><canvas id="chartOscillatorCanvas"></canvas><div id="chartOscillatorLegend" class="chartOscillatorLegend"></div>';
    chart.parentNode.insertBefore(pane, chart.nextSibling);
    return pane;
  }

  function oscillatorLines(indicatorData) {
    return (indicatorData?.lines || [])
      .filter(line => String(line?.pane || '').toLowerCase() === 'oscillator')
      .filter(line => Array.isArray(line.series) && line.series.length > 0);
  }

  function numberOrNull(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function renderOscillatorPane(rows, indicatorData) {
    window.__chartPaneLastRows = rows || [];
    window.__chartPaneLastIndicatorData = indicatorData || null;
    const pane = ensureOscillatorPane();
    if (!pane) return;
    const canvas = document.getElementById('chartOscillatorCanvas');
    const legend = document.getElementById('chartOscillatorLegend');
    const lines = oscillatorLines(indicatorData);
    pane.style.display = oscillatorPaneEnabled() && lines.length ? '' : 'none';
    if (!oscillatorPaneEnabled() || !lines.length || !canvas) {
      if (legend) legend.textContent = 'Keine MACD/MFI-Daten fuer zweite Pane.';
      return;
    }

    const width = Math.max(320, pane.clientWidth || document.getElementById('klineChart')?.clientWidth || 900);
    const height = Math.max(120, Number(localStorage.getItem('tradingBotChartOscillatorHeight') || 150));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const allValues = [];
    lines.forEach(line => (line.series || []).forEach(point => {
      const value = numberOrNull(point.value);
      if (value !== null) allValues.push(value);
    }));
    if (!allValues.length) return;
    let min = Math.min(...allValues);
    let max = Math.max(...allValues);
    if (min === max) {
      min -= 1;
      max += 1;
    }
    if (min > 0 && max <= 100) {
      min = 0;
      max = 100;
    } else {
      const spread = Math.max(0.000001, max - min);
      min -= spread * 0.12;
      max += spread * 0.12;
    }

    const timeValues = (rows || []).map(row => Number(row.timestamp)).filter(Number.isFinite);
    const minTime = timeValues.length ? Math.min(...timeValues) : Math.min(...lines.flatMap(line => line.series.map(point => Number(point.timestamp) * 1000).filter(Number.isFinite)));
    const maxTime = timeValues.length ? Math.max(...timeValues) : Math.max(...lines.flatMap(line => line.series.map(point => Number(point.timestamp) * 1000).filter(Number.isFinite)));
    const padLeft = 42;
    const padRight = 10;
    const padTop = 12;
    const padBottom = 20;
    const plotWidth = Math.max(1, width - padLeft - padRight);
    const plotHeight = Math.max(1, height - padTop - padBottom);
    const x = timestamp => padLeft + ((Number(timestamp) * 1000 - minTime) / Math.max(1, maxTime - minTime)) * plotWidth;
    const y = value => padTop + (1 - ((Number(value) - min) / Math.max(0.000001, max - min))) * plotHeight;

    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(148,163,184,.18)';
    ctx.fillStyle = 'rgba(148,163,184,.85)';
    ctx.font = '10px Consolas, monospace';
    [min, (min + max) / 2, max].forEach(value => {
      const yy = y(value);
      ctx.beginPath();
      ctx.moveTo(padLeft, yy);
      ctx.lineTo(width - padRight, yy);
      ctx.stroke();
      ctx.fillText(value.toFixed(Math.abs(value) < 1 ? 4 : 2), 4, yy + 3);
    });

    lines.forEach(line => {
      const name = String(line.name || '').toUpperCase();
      const isHistogram = name.includes('HIST');
      ctx.strokeStyle = line.color || '#94a3b8';
      ctx.fillStyle = line.color || '#94a3b8';
      ctx.lineWidth = isHistogram ? 1 : 1.4;
      if (isHistogram) {
        const zeroY = y(0);
        const barWidth = Math.max(1, plotWidth / Math.max(20, (rows || []).length) * 0.75);
        (line.series || []).forEach(point => {
          const value = numberOrNull(point.value);
          if (value === null) return;
          const xx = x(point.timestamp);
          const yy = y(value);
          ctx.globalAlpha = 0.65;
          ctx.fillRect(xx - barWidth / 2, Math.min(yy, zeroY), barWidth, Math.max(1, Math.abs(zeroY - yy)));
          ctx.globalAlpha = 1;
        });
        return;
      }
      ctx.beginPath();
      let started = false;
      (line.series || []).forEach(point => {
        const value = numberOrNull(point.value);
        if (value === null) return;
        const xx = x(point.timestamp);
        const yy = y(value);
        if (!started) {
          ctx.moveTo(xx, yy);
          started = true;
        } else {
          ctx.lineTo(xx, yy);
        }
      });
      if (started) ctx.stroke();
    });

    if (legend) {
      legend.innerHTML = lines.map(line => `<span><b style="background:${line.color || '#94a3b8'}"></b>${String(line.label || line.name || '-')}</span>`).join('');
    }
  }

  function injectStyles() {
    const styleId = 'chart-pane-technical-style';
    document.getElementById(styleId)?.remove();
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .chartTechnicalToolbar { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:8px 0 10px; padding:8px; border:1px solid rgba(148,163,184,.25); border-radius:4px; background:rgba(15,23,42,.14); }
      .chartTechTitle { font-size:10px; font-weight:900; letter-spacing:.10em; text-transform:uppercase; color:var(--muted); margin-right:4px; }
      .chartTechButton { min-height:28px; padding:5px 8px; border-radius:3px; font-size:11px; font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; background:rgba(30,41,59,.84); color:#cbd5e1; border:1px solid rgba(148,163,184,.25); }
      .chartTechButton.active { color:#ecfeff; border-color:#0f766e; background:#0f766e; }
      .chartPluginStatus { margin-left:auto; font-size:10px; color:var(--muted); font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; }
      .chartOscillatorPane { margin-top:6px; border:1px solid rgba(148,163,184,.25); border-radius:4px; background:rgba(15,23,42,.16); overflow:hidden; }
      .chartPaneHeader { display:flex; justify-content:space-between; gap:8px; align-items:center; padding:6px 8px; border-bottom:1px solid rgba(148,163,184,.18); }
      .chartPaneHeader strong { font-size:10px; font-weight:900; letter-spacing:.10em; text-transform:uppercase; }
      .chartPaneHeader span { font-size:10px; color:var(--muted); font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; }
      #chartOscillatorCanvas { display:block; width:100%; height:150px; }
      .chartOscillatorLegend { display:flex; flex-wrap:wrap; gap:8px; padding:6px 8px; border-top:1px solid rgba(148,163,184,.18); font-size:10px; color:var(--muted); font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; }
      .chartOscillatorLegend span { display:inline-flex; align-items:center; gap:5px; }
      .chartOscillatorLegend b { display:inline-block; width:10px; height:3px; border-radius:0; }
    `;
    document.head.appendChild(style);
  }

  function patchInitKlineChart() {
    if (window.initKlineChart?.__chartPanePatched) return;
    originalInitKlineChart = window.initKlineChart;
    if (typeof originalInitKlineChart !== 'function') return;
    window.initKlineChart = function patchedInitKlineChart(...args) {
      const chart = originalInitKlineChart.apply(this, args);
      window.__klineChartInstance = chart;
      updateToolbarState();
      return chart;
    };
    window.initKlineChart.__chartPanePatched = true;
  }

  function patchDrawChart() {
    if (window.drawChart?.__chartPanePatched) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedDrawChart(candles, overlay, indicatorData) {
      const result = originalDrawChart.apply(this, arguments);
      const rows = (candles || []).map(candle => ({
        timestamp: Number(candle.timestamp) * 1000,
        open: Number(candle.open),
        high: Number(candle.high),
        low: Number(candle.low),
        close: Number(candle.close),
        volume: Number(candle.volume || 0),
      })).filter(row => Number.isFinite(row.timestamp));
      ensureToolbar();
      renderOscillatorPane(rows, indicatorData);
      applyAutoScroll();
      return result;
    };
    window.drawChart.__chartPanePatched = true;
  }

  function install() {
    injectStyles();
    ensureToolbar();
    patchInitKlineChart();
    patchDrawChart();
    window.addEventListener('resize', () => renderOscillatorPane(window.__chartPaneLastRows || [], window.__chartPaneLastIndicatorData || null));
    document.body.dataset.chartPanePatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install);
  } else {
    install();
  }
})();
