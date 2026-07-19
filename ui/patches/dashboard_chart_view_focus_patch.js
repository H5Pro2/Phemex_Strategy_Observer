// ==================================================
// dashboard_chart_view_focus_patch.js
// ==================================================
// CHART VIEW FOCUS PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-06-02-chart-view-focus-v24-three-column-top';

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

  function activeIndicatorText() {
    const status = String(document.getElementById('chartPluginStatus')?.textContent || '');
    const hasSignalList = /Signalquellen|Agent-Indikatoren/i.test(status);
    const direct = hasSignalList ? (status.split('Signalquellen').pop() || status.split('Agent-Indikatoren').pop() || '') : '';
    const cleaned = direct.replace('bereit', '').trim();
    if (cleaned && !/KLineCharts|scrollToRealTime|zoomAtCoordinate|createIndicator|createOverlay|resize/i.test(cleaned)) return compactIndicatorList(cleaned);
    const meta = String(document.getElementById('indicatorChartSettings')?.textContent || '').trim();
    return meta ? compactIndicatorList(meta) : 'Basis-Chart';
  }

  function compactIndicatorList(text) {
    const names = String(text || '')
      .split(/[\/,|]+/)
      .map(part => part.trim())
      .filter(Boolean)
      .map(part => part
        .replace(/Fast|Slow|Split|Main|Direct|Agent|Indikator/gi, '')
        .replace(/[_-]+/g, ' ')
        .trim()
      )
      .filter(Boolean);
    const unique = Array.from(new Set(names.map(name => {
      const lower = name.toLowerCase();
      const fixed = {
        macd: 'MACD',
        mfi: 'MFI',
        hma: 'HMA',
        sma: 'SMA',
        rsi: 'RSI',
        vwap: 'VWAP',
        volume: 'Volume',
        bos: 'BOS',
        choch: 'CHoCH'
      };
      return fixed[lower] || name.replace(/\b\w/g, chr => chr.toUpperCase());
    })));
    if (!unique.length) return '-';
    const shown = unique.slice(0, 4);
    const more = unique.length - shown.length;
    return `${shown.join(', ')}${more > 0 ? ` +${more}` : ''}`;
  }

  function chartStateText() {
    const raw = String(document.getElementById('chartStatus')?.textContent || 'Noch nicht geladen').trim();
    if (!raw) return 'Noch nicht geladen';
    const parts = raw.split('|').map(part => part.trim()).filter(Boolean);
    const filtered = parts.filter(part => {
      if (/^[A-Z0-9]+(?::USDT)?$/i.test(part)) return false;
      if (/^[0-9]+[ ]*m$/i.test(part)) return false;
      if (/^[0-9]+[ ]*Kerzen$/i.test(part)) return false;
      if (/Market Structure/i.test(part)) return false;
      return true;
    });
    return filtered.join(' | ') || parts.slice(-1)[0] || raw;
  }

  function scanSummaryText() {
    const meta = String(document.getElementById('chartMeta')?.textContent || '').trim();
    if (meta) return meta;
    const status = runtimeStatus();
    const running = status?.running;
    if (running === true) return 'Scanner aktiv | warte auf Chart-Metadaten';
    if (running === false) return 'Scanner gestoppt | Chart kann trotzdem geladen werden';
    return 'Noch keine Chart-Metadaten';
  }

  function removeModeToolbar() {
    document.getElementById('chartViewModeToolbar')?.remove();
    delete document.body.dataset.chartViewMode;
  }

  function upsertSummaryPanel() {
    const chartView = document.getElementById('chartView');
    const card = chartView?.querySelector(':scope > .card');
    const toolbar = card?.querySelector('.chartToolbar');
    if (!card || !toolbar) return;

    let top = document.getElementById('chartViewTopControls');
    if (!top) {
      top = document.createElement('div');
      top.id = 'chartViewTopControls';
      top.className = 'chartViewTopControls';
      toolbar.insertAdjacentElement('beforebegin', top);
    }
    if (toolbar.parentElement !== top) top.appendChild(toolbar);

    let panel = document.getElementById('chartViewFocusPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'chartViewFocusPanel';
      panel.className = 'chartViewFocusPanel';
    }
    if (panel.parentElement !== top) top.appendChild(panel);

    panel.innerHTML = `
      <div class="chartViewFocusCard status"><span>Chart Status</span><strong>${chartStateText()}</strong></div>
      <div class="chartViewFocusCard indicators"><span>Aktive Chart-Anzeigen</span><strong>${activeIndicatorText()}</strong></div>
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
    }
    const top = document.getElementById('chartViewTopControls');
    if (top) top.insertAdjacentElement('afterend', legend);
    else focus.insertAdjacentElement('afterend', legend);

    legend.innerHTML = `<div class="chartViewLegendHeader"><strong>Chart</strong><span>${scanSummaryText()}</span></div>`;
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
      statusPanel.style.display = 'none';
    }
    if (meta && statusPanel && meta.previousElementSibling !== statusPanel) card.insertBefore(meta, statusPanel.nextSibling);

    const text = activeIndicatorText().toLowerCase();
    const paneCount = ['macd', 'mfi', 'rsi', 'volume'].filter(name => text.includes(name)).length;
    const targetHeight = Math.max(820, Math.min(1220, 680 + paneCount * 130));
    wrap.style.height = `${targetHeight}px`;
    wrap.style.minHeight = `${targetHeight}px`;
    wrap.style.maxHeight = 'none';
    chart.style.height = `${targetHeight}px`;
    chart.style.minHeight = `${targetHeight}px`;
    chart.style.maxHeight = 'none';

    window.setTimeout(() => {
      try { if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart(); } catch (_) {}
      try { if (chartInstance() && typeof chartInstance().resize === 'function') chartInstance().resize(); } catch (_) {}
    }, 100);
  }

  function refreshChartFocus() {
    removeModeToolbar();
    upsertSummaryPanel();
    upsertLegendPanel();
    normalizeChartLayout();
  }

  function installStyles() {
    const oldStyle = document.getElementById('chart-view-focus-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'chart-view-focus-style';
    style.textContent = `
      #chartView { width:100% !important; max-width:none !important; }
      #chartView > .card { width:100% !important; max-width:none !important; overflow:visible !important; border-left:1px solid var(--line) !important; }
      #chartView .chartViewHeader { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:10px !important; padding-bottom:8px !important; border-bottom:1px solid rgba(148,163,184,.18) !important; }
      #chartView .chartSetupHint { display:none !important; }
      #chartView .chartViewTopControls { display:grid !important; grid-template-columns:minmax(260px, 320px) minmax(260px, .9fr) minmax(300px, 1.1fr) !important; gap:10px !important; align-items:stretch !important; margin:8px 0 !important; }
      #chartView .chartToolbar { display:grid !important; width:min(320px, 100%) !important; max-width:100% !important; box-sizing:border-box !important; grid-template-columns:1fr !important; gap:8px !important; align-items:stretch !important; justify-content:start !important; padding:8px 10px !important; border:1px solid var(--line) !important; border-radius:7px !important; background:rgba(15,23,42,.18) !important; }
      #chartView .chartToolbar > div { min-width:0 !important; max-width:none !important; width:100% !important; }
      #chartView .chartToolbar > div:has(.chartStatusText) { max-width:none !important; }
      #chartView .chartToolbar label { margin-bottom:4px !important; font-size:11px !important; line-height:1.2 !important; }
      #chartView .chartToolbar .controlButton, #chartView .chartToolbar select { width:100% !important; min-height:30px !important; height:30px !important; padding:4px 9px !important; border-radius:5px !important; font-size:12px !important; line-height:1.1 !important; }
      #chartView .chartToolbar .chartStatusText { display:none !important; }
      #chartView .chartStatusText { min-height:30px !important; display:flex !important; align-items:center !important; padding:5px 8px !important; border:1px solid var(--line) !important; border-radius:6px !important; background:rgba(2,6,23,.22) !important; font-size:11px !important; }
      #chartView .chartViewFocusPanel { display:grid !important; grid-template-columns:1fr !important; grid-template-rows:1fr 1fr !important; gap:6px !important; height:100% !important; min-height:0 !important; margin:0 !important; align-content:stretch !important; }
      #chartView .chartViewFocusCard { min-height:0 !important; height:100% !important; display:flex !important; flex-direction:column !important; justify-content:center !important; padding:6px 8px !important; border:1px solid var(--line) !important; border-radius:6px !important; background:rgba(15,23,42,.22) !important; overflow:hidden !important; }
      #chartView .chartViewFocusCard.indicators { border-left:4px solid #22d3ee !important; }
      #chartView .chartViewFocusCard.status { border-left:4px solid #f59e0b !important; }
      #chartView .chartViewFocusCard span { display:block !important; color:var(--muted) !important; font-size:10px !important; line-height:1.1 !important; font-weight:800 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #chartView .chartViewFocusCard strong { display:block !important; margin-top:3px !important; color:var(--ink) !important; font-size:11px !important; font-weight:900 !important; line-height:1.15 !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      #chartView .chartViewFocusCard.indicators strong, #chartView .chartViewFocusCard.status strong { font-size:11.5px !important; white-space:nowrap !important; display:block !important; letter-spacing:0 !important; text-transform:none !important; }
      #chartView .chartViewLegendPanel { margin:0 0 8px !important; padding:8px 10px !important; border:1px solid var(--line) !important; border-radius:7px !important; background:rgba(15,23,42,.16) !important; }
      #chartView .chartViewLegendHeader { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:10px !important; margin:0 !important; padding:0 !important; border:0 !important; }
      #chartView .chartViewLegendHeader strong { color:var(--ink) !important; font-size:12px !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #chartView .chartViewLegendHeader span { color:var(--muted) !important; font-size:11px !important; text-align:right !important; max-width:72% !important; white-space:nowrap !important; overflow:hidden !important; text-overflow:ellipsis !important; }
      #chartView #indicatorChartSettings { display:none !important; }
      #chartView #chartMeta { margin:0 0 8px !important; padding:7px 9px !important; border:1px solid rgba(148,163,184,.18) !important; border-radius:6px !important; background:rgba(2,6,23,.22) !important; color:var(--muted) !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; font-size:11px !important; }
      #chartView .chartViewFocusedCanvas { position:relative !important; display:block !important; width:calc(100% - 28px) !important; margin:0 auto 90px !important; border:1px solid var(--line) !important; border-radius:8px !important; background:#020617 !important; overflow:visible !important; }
      #chartView .chartViewFocusedChart { display:block !important; width:100% !important; }
      #chartView #directAgentChartStatusPanel { display:none !important; }
      #chartView .directAgentChartStatusPanel { display:none !important; }
      @media (max-width:1180px) { #chartView .chartViewTopControls { grid-template-columns:minmax(260px, 320px) minmax(0, 1fr) !important; } #chartView .tvStrategyHud { grid-column:1 / -1 !important; } }
      @media (max-width:900px) { #chartView .chartViewTopControls { grid-template-columns:1fr !important; } #chartView .chartToolbar { width:100% !important; } #chartView .tvStrategyHud { grid-column:auto !important; } }
      @media (max-width:760px) { #chartView .chartViewFocusedCanvas { width:100% !important; margin-left:0 !important; margin-right:0 !important; } #chartView .chartViewLegendHeader { flex-direction:column !important; } #chartView .chartViewLegendHeader span { max-width:none !important; text-align:left !important; } }
    `;
    document.head.appendChild(style);
  }

  function installHooks() {
    ['click', 'change'].forEach(type => {
      document.addEventListener(type, event => {
        const target = event.target;
        if (!(target instanceof Element)) return;
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
    removeModeToolbar();
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
