// ==================================================
// dashboard_agent_setup_layout_fix_patch.js
// ==================================================
// AGENT SETUP AND CHART VIEW LAYOUT FIX PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-agent-setup-layout-fix-v1';
  const CHART_VIEW_SECTIONS = ['rsi', 'vwap', 'volume'];
  const EVALUATION_ONLY_SECTIONS = ['breakout_fakeout', 'volatility_regime', 'risk'];

  function injectLayoutStyles() {
    const oldStyle = document.getElementById('agent-setup-layout-fix-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'agent-setup-layout-fix-style';
    style.textContent = `
      main {
        max-width:none !important;
        width:100% !important;
      }
      #chartView,
      #agentSetupView {
        width:100% !important;
        max-width:none !important;
      }
      #chartView > .card,
      #agentSetupView > .card {
        width:100% !important;
        max-width:none !important;
        overflow:visible !important;
      }
      #chartView .chartCanvasWrap {
        width:100% !important;
        min-height:820px !important;
        overflow:hidden !important;
      }
      #chartView #klineChart {
        width:100% !important;
        min-height:820px !important;
      }
      #agentSetupView .configModalBody {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)) !important;
        gap:16px !important;
        align-items:start !important;
        grid-auto-flow:row dense !important;
        overflow:visible !important;
        padding:16px 14px !important;
      }
      #agentSetupView .settingsTabsBar {
        grid-column:1 / -1 !important;
        width:100% !important;
        display:flex !important;
        flex-wrap:wrap !important;
        align-items:center !important;
        gap:8px !important;
        margin:0 0 10px !important;
        padding:0 0 14px !important;
        border-bottom:1px solid var(--line) !important;
      }
      #agentSetupView .settingsTabButton {
        min-width:128px !important;
        justify-content:center !important;
      }
      #agentSetupView .settingsGroup:not([data-agent-section]),
      #agentSetupView .agentSetupSectionTitle,
      #agentSetupView .agentSetupDirectHeader {
        grid-column:1 / -1 !important;
      }
      #agentSetupView .agentSetupDirectHeader {
        margin-top:4px !important;
      }
      #agentSetupView .agentSetupSectionTitle {
        display:flex !important;
        align-items:center !important;
        justify-content:space-between !important;
        gap:12px !important;
        min-height:44px !important;
        padding:12px 14px !important;
        border:1px solid var(--line) !important;
        border-left:4px solid var(--accent) !important;
        border-radius:7px !important;
        background:rgba(15,23,42,.18) !important;
        color:var(--ink) !important;
        font-weight:900 !important;
        letter-spacing:.07em !important;
        text-transform:uppercase !important;
      }
      #agentSetupView .agentSetupSectionTitle small {
        color:var(--muted) !important;
        font-size:11px !important;
        font-weight:700 !important;
        letter-spacing:.02em !important;
        text-transform:none !important;
      }
      #agentSetupView .agentDirectGroup[data-chart-view="true"] {
        border-left:4px solid #22d3ee !important;
      }
      #agentSetupView .agentDirectGroup[data-chart-view="false"] {
        border-left:4px solid #fb923c !important;
      }
      #agentSetupView .agentChartModeBadge {
        display:inline-flex !important;
        align-items:center !important;
        min-height:24px !important;
        width:max-content !important;
        padding:3px 8px !important;
        border:1px solid var(--line) !important;
        border-radius:999px !important;
        background:var(--panel-soft) !important;
        color:var(--muted) !important;
        font-size:11px !important;
        font-weight:900 !important;
        letter-spacing:.04em !important;
        text-transform:uppercase !important;
      }
      #agentSetupView .agentDirectGroup[data-chart-view="true"] .agentChartModeBadge {
        color:#67e8f9 !important;
        border-color:#0891b2 !important;
        background:rgba(8,145,178,.14) !important;
      }
      #agentSetupView .agentDirectGroup[data-chart-view="false"] .agentChartModeBadge {
        color:#fdba74 !important;
        border-color:#c2410c !important;
        background:rgba(194,65,12,.14) !important;
      }
      #agentSetupView .agentIndicatorGroup,
      #agentSetupView .agentDirectGroup {
        min-height:0 !important;
        height:auto !important;
        contain:layout style !important;
      }
      #agentSetupView .settingsGroupGrid {
        align-items:start !important;
      }
      @media (max-width:900px) {
        main { padding:16px 12px 32px !important; }
        #agentSetupView .configModalBody {
          grid-template-columns:1fr !important;
          padding:12px 0 !important;
        }
        #agentSetupView .settingsTabButton {
          flex:1 1 140px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function directHeaderBlock(view) {
    return Array.from(view.querySelectorAll('.settingsGroup')).find(block => {
      if (block.dataset.agentSection) return false;
      const text = String(block.querySelector(':scope > h3')?.textContent || '').trim();
      return /Direkte Agenten|Agenten ohne eigene Hauptchart-Linie/i.test(text);
    });
  }

  function makeSectionTitle(id, title, subtitle) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const element = document.createElement('div');
    element.id = id;
    element.className = 'agentSetupSectionTitle';
    element.innerHTML = `<span>${title}</span><small>${subtitle}</small>`;
    return element;
  }

  function markDirectGroup(group, chartView) {
    if (!group) return;
    group.dataset.chartView = chartView ? 'true' : 'false';
    const grid = group.querySelector('.settingsGroupGrid');
    if (!grid || grid.querySelector('.agentChartModeBadge')) return;
    const badge = document.createElement('div');
    badge.className = 'agentChartModeBadge fullWidth';
    badge.textContent = chartView ? 'Chart View aktivierbar' : 'Nur Bewertung / Risiko';
    grid.insertBefore(badge, grid.firstChild);
  }

  function layoutAgentSetup() {
    const view = document.getElementById('agentSetupView');
    const body = view?.querySelector('.configModalBody');
    if (!view || !body) return;

    const tabs = body.querySelector('.settingsTabsBar');
    if (tabs && tabs !== body.firstElementChild) body.insertBefore(tabs, body.firstElementChild);

    const header = directHeaderBlock(view);
    if (header) {
      header.classList.add('agentSetupDirectHeader');
      const title = header.querySelector(':scope > h3');
      const label = header.querySelector(':scope .label');
      if (title) title.textContent = 'Direkte Agenten';
      if (label) label.textContent = 'RSI, VWAP und Volume haben Chart-View-Funktion. Breakout/Fakeout, Volatility und Risk bleiben Bewertungsagenten ohne eigenes Chart-Pane.';
    }

    const chartGroups = CHART_VIEW_SECTIONS
      .map(section => body.querySelector(`.agentDirectGroup[data-agent-section="${section}"]`))
      .filter(Boolean);
    const evaluationGroups = EVALUATION_ONLY_SECTIONS
      .map(section => body.querySelector(`.agentDirectGroup[data-agent-section="${section}"]`))
      .filter(Boolean);

    chartGroups.forEach(group => markDirectGroup(group, true));
    evaluationGroups.forEach(group => markDirectGroup(group, false));

    if (chartGroups.length) {
      const title = makeSectionTitle('agentSetupChartViewAgentsTitle', 'Chart View Agenten', 'RSI / VWAP / Volume werden im Chart angezeigt');
      body.insertBefore(title, chartGroups[0]);
      chartGroups.forEach(group => body.insertBefore(group, title.nextSibling));
    }

    if (evaluationGroups.length) {
      const firstReference = evaluationGroups[0];
      const title = makeSectionTitle('agentSetupEvaluationAgentsTitle', 'Nur Bewertungsagenten', 'Signal-, Regime- und Risiko-Auswertung ohne eigenes Chart-Pane');
      body.insertBefore(title, firstReference);
      evaluationGroups.forEach(group => body.insertBefore(group, title.nextSibling));
    }

    document.body.dataset.agentSetupLayoutFixed = PATCH_VERSION;
  }

  function applyChartAreaSizing() {
    const chart = document.getElementById('klineChart');
    const wrap = chart?.closest('.chartCanvasWrap');
    if (!chart || !wrap) return;
    const paneText = String(document.getElementById('chartPluginStatus')?.textContent || '');
    const activePaneCount = ['macd', 'mfi', 'rsi', 'volume'].filter(name => paneText.toLowerCase().includes(name)).length;
    const targetHeight = Math.max(820, Math.min(1280, 660 + activePaneCount * 145));
    wrap.style.height = `${targetHeight}px`;
    wrap.style.minHeight = `${targetHeight}px`;
    chart.style.height = `${targetHeight}px`;
    chart.style.minHeight = `${targetHeight}px`;
    window.setTimeout(() => {
      try {
        if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart();
      } catch (_) {}
      try {
        if (window.__klineChartInstance && typeof window.__klineChartInstance.resize === 'function') window.__klineChartInstance.resize();
      } catch (_) {}
    }, 120);
  }

  function install() {
    injectLayoutStyles();
    layoutAgentSetup();
    applyChartAreaSizing();
    window.setTimeout(layoutAgentSetup, 250);
    window.setTimeout(layoutAgentSetup, 1000);
    window.setTimeout(applyChartAreaSizing, 350);
    window.setTimeout(applyChartAreaSizing, 1200);
    document.body.dataset.agentSetupLayoutFixPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  window.addEventListener('resize', applyChartAreaSizing);
})();
