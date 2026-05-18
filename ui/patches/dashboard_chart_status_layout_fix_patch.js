// ==================================================
// dashboard_chart_status_layout_fix_patch.js
// ==================================================
// CHART STATUS PANEL LAYOUT FIX PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-18-chart-status-layout-fix-v1';

  function chartPaneCountFromStatus() {
    const text = String(document.getElementById('chartPluginStatus')?.textContent || '').toLowerCase();
    return ['macd', 'mfi', 'rsi', 'volume'].filter(name => text.includes(name)).length;
  }

  function applyChartCanvasSpacing() {
    const chart = document.getElementById('klineChart');
    const wrap = chart?.closest('.chartCanvasWrap');
    if (!chart || !wrap) return;

    const paneCount = chartPaneCountFromStatus();
    const height = Math.max(1120, Math.min(1840, 860 + paneCount * 210));
    wrap.style.height = `${height}px`;
    wrap.style.minHeight = `${height}px`;
    wrap.style.maxHeight = 'none';
    wrap.style.overflow = 'hidden';
    chart.style.height = `${height}px`;
    chart.style.minHeight = `${height}px`;
    chart.style.maxHeight = 'none';

    window.setTimeout(() => {
      try {
        if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart();
      } catch (_) {}
      try {
        if (window.__klineChartInstance && typeof window.__klineChartInstance.resize === 'function') window.__klineChartInstance.resize();
      } catch (_) {}
    }, 80);
  }

  function placeStatusPanel() {
    const chartView = document.getElementById('chartView');
    const chartCard = chartView?.querySelector(':scope > .card');
    const wrap = chartCard?.querySelector('.chartCanvasWrap');
    const panel = document.getElementById('directAgentChartStatusPanel');
    const meta = document.getElementById('chartMeta');
    if (!chartCard || !wrap || !panel) return;

    panel.classList.add('chartStatusPanelDetached');
    if (panel.previousElementSibling !== wrap) {
      chartCard.insertBefore(panel, meta || wrap.nextSibling);
      chartCard.insertBefore(panel, wrap.nextSibling);
    }
    if (meta && meta.previousElementSibling !== panel) {
      chartCard.insertBefore(meta, panel.nextSibling);
    }
  }

  function installStyles() {
    const oldStyle = document.getElementById('chart-status-layout-fix-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'chart-status-layout-fix-style';
    style.textContent = `
      #chartView .chartCanvasWrap {
        display:block !important;
        position:relative !important;
        width:100% !important;
        margin:0 0 26px !important;
        border-bottom:1px solid var(--line) !important;
        overflow:hidden !important;
      }
      #chartView #klineChart {
        display:block !important;
        width:100% !important;
      }
      #chartView #directAgentChartStatusPanel.chartStatusPanelDetached {
        display:block !important;
        position:relative !important;
        z-index:5 !important;
        clear:both !important;
        width:100% !important;
        margin:0 0 18px !important;
        padding:14px !important;
        border:1px solid var(--line) !important;
        border-left:6px solid #a78bfa !important;
        border-radius:9px !important;
        background:rgba(15,23,42,.94) !important;
        box-shadow:0 10px 24px rgba(0,0,0,.22) !important;
      }
      #chartView #directAgentChartStatusPanel .directAgentChartStatusHead {
        display:flex !important;
        align-items:flex-start !important;
        justify-content:space-between !important;
        gap:14px !important;
        margin:0 0 12px !important;
        padding:0 0 10px !important;
        border-bottom:1px solid rgba(148,163,184,.18) !important;
      }
      #chartView #directAgentChartStatusPanel .directAgentChartStatusHead strong {
        color:var(--ink) !important;
        font-size:13px !important;
        font-weight:900 !important;
        letter-spacing:.075em !important;
        text-transform:uppercase !important;
        white-space:normal !important;
      }
      #chartView #directAgentChartStatusPanel .directAgentChartStatusHead span {
        color:var(--muted) !important;
        font-size:12px !important;
        white-space:nowrap !important;
      }
      #chartView #directAgentChartStatusPanel .directAgentChartGrid {
        display:grid !important;
        grid-template-columns:repeat(3, minmax(0, 1fr)) !important;
        gap:12px !important;
      }
      #chartView #directAgentChartStatusPanel .directAgentChartTile {
        min-height:118px !important;
        padding:14px !important;
        border:1px solid var(--line) !important;
        border-radius:8px !important;
        background:rgba(30,41,59,.72) !important;
      }
      #chartView #chartMeta {
        position:relative !important;
        z-index:4 !important;
        clear:both !important;
        margin-top:0 !important;
        padding-top:8px !important;
      }
      @media (max-width:1100px) {
        #chartView #directAgentChartStatusPanel .directAgentChartGrid {
          grid-template-columns:1fr !important;
        }
        #chartView #directAgentChartStatusPanel .directAgentChartStatusHead {
          flex-direction:column !important;
          align-items:flex-start !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function refreshLayout() {
    applyChartCanvasSpacing();
    placeStatusPanel();
  }

  function installHooks() {
    ['click', 'change'].forEach(type => {
      document.addEventListener(type, event => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (target.closest('#chartViewButton, #reloadChart, #chartAsset, #chartTimeframe, #chartCandleLimit')) {
          window.setTimeout(refreshLayout, 80);
          window.setTimeout(refreshLayout, 350);
          window.setTimeout(refreshLayout, 1200);
        }
      }, true);
    });
  }

  function install() {
    installStyles();
    installHooks();
    refreshLayout();
    window.setTimeout(refreshLayout, 350);
    window.setTimeout(refreshLayout, 1200);
    window.setTimeout(refreshLayout, 2500);
    document.body.dataset.chartStatusLayoutFixPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  window.addEventListener('resize', refreshLayout);
})();
