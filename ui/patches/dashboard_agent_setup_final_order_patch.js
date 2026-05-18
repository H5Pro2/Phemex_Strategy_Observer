// ==================================================
// dashboard_agent_setup_final_order_patch.js
// ==================================================
// FINAL AGENT SETUP ORDER PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-18-agent-setup-final-order-v1';
  const CHART_VIEW_SECTIONS = ['hma', 'sma', 'triple_ema', 'macd', 'mfi', 'rsi', 'vwap', 'volume'];
  const CHART_STATUS_SECTIONS = ['breakout_fakeout', 'volatility_regime', 'risk'];

  function setupBody() {
    return document.getElementById('agentSetupView')?.querySelector('.configModalBody') || null;
  }

  function directHeaderBlocks(body) {
    return Array.from(body?.querySelectorAll('.settingsGroup') || []).filter(block => {
      if (block.dataset.agentSection) return false;
      const title = String(block.querySelector(':scope > h3')?.textContent || '').trim();
      return /Direkte Agenten|Agenten ohne eigene Hauptchart-Linie|Nur Bewertungsagenten/i.test(title);
    });
  }

  function sectionGroup(body, section) {
    return body?.querySelector(`[data-agent-section="${section}"]`) || null;
  }

  function sectionHeader(id, title, detail, mode) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const header = document.createElement('div');
    header.id = id;
    header.className = `agentSetupFinalSectionHeader ${mode}`;
    header.innerHTML = `<div><strong>${title}</strong><span>${detail}</span></div>`;
    return header;
  }

  function insertAfter(reference, node) {
    if (!reference || !node || !reference.parentNode) return reference;
    reference.parentNode.insertBefore(node, reference.nextSibling);
    return node;
  }

  function markGroup(group, mode, label) {
    if (!group) return;
    group.dataset.agentDisplayGroup = mode;
    group.dataset.chartView = 'true';
    group.querySelectorAll('.agentChartModeBadge, .agentSetupFinalBadge').forEach(badge => badge.remove());
    const grid = group.querySelector('.settingsGroupGrid');
    if (!grid) return;
    const badge = document.createElement('div');
    badge.className = 'agentSetupFinalBadge fullWidth';
    badge.textContent = label;
    grid.insertBefore(badge, grid.firstChild);
  }

  function applyFinalOrder() {
    const body = setupBody();
    if (!body) return;

    const tabs = body.querySelector('.settingsTabsBar');
    if (tabs && tabs !== body.firstElementChild) body.insertBefore(tabs, body.firstElementChild);

    directHeaderBlocks(body).forEach(block => block.remove());
    document.getElementById('agentSetupEvaluationAgentsHeader')?.remove();

    const chartGroups = CHART_VIEW_SECTIONS.map(section => sectionGroup(body, section)).filter(Boolean);
    const statusGroups = CHART_STATUS_SECTIONS.map(section => sectionGroup(body, section)).filter(Boolean);

    chartGroups.forEach(group => markGroup(group, 'chart', 'Chart View'));
    statusGroups.forEach(group => markGroup(group, 'status', 'Chart Status'));

    const firstNormalGroup = Array.from(body.children).find(child => {
      if (child.classList?.contains('settingsTabsBar')) return false;
      if (child.classList?.contains('agentSetupFinalSectionHeader')) return false;
      return child.classList?.contains('settingsGroup') && !child.dataset.agentSection;
    });

    const reference = firstNormalGroup || tabs || body.firstElementChild;
    const chartHeader = sectionHeader(
      'agentSetupChartViewAgentsHeader',
      'Chart View Agenten',
      'HMA, SMA, Triple EMA, MACD, MFI, RSI, VWAP und Volume werden im Chart dargestellt.',
      'chart'
    );
    const statusHeader = sectionHeader(
      'agentSetupChartStatusAgentsHeader',
      'Chart Status Agenten',
      'Breakout/Fakeout, Volatility und Risk erscheinen als Statusbereich im Chartfenster.',
      'status'
    );

    body.insertBefore(chartHeader, reference?.nextSibling || body.firstChild);
    let cursor = chartHeader;
    chartGroups.forEach(group => { cursor = insertAfter(cursor, group); });
    cursor = insertAfter(cursor, statusHeader);
    statusGroups.forEach(group => { cursor = insertAfter(cursor, group); });

    document.body.dataset.agentSetupFinalOrderPatch = PATCH_VERSION;
  }

  function installStyles() {
    const oldStyle = document.getElementById('agent-setup-final-order-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'agent-setup-final-order-style';
    style.textContent = `
      #agentSetupView .configModalBody {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)) !important;
        gap:16px !important;
        align-items:start !important;
      }
      #agentSetupView .settingsTabsBar,
      #agentSetupView .settingsGroup:not([data-agent-section]),
      #agentSetupView .agentSetupFinalSectionHeader {
        grid-column:1 / -1 !important;
      }
      #agentSetupView .agentSetupFinalSectionHeader {
        min-height:66px !important;
        display:flex !important;
        align-items:center !important;
        padding:14px 16px !important;
        border:1px solid var(--line) !important;
        border-radius:8px !important;
        background:rgba(15,23,42,.28) !important;
      }
      #agentSetupView .agentSetupFinalSectionHeader.chart {
        border-left:5px solid #22d3ee !important;
      }
      #agentSetupView .agentSetupFinalSectionHeader.status {
        border-left:5px solid #a78bfa !important;
      }
      #agentSetupView .agentSetupFinalSectionHeader strong {
        display:block !important;
        color:var(--ink) !important;
        font-size:15px !important;
        font-weight:900 !important;
        letter-spacing:.07em !important;
        text-transform:uppercase !important;
      }
      #agentSetupView .agentSetupFinalSectionHeader span {
        display:block !important;
        margin-top:5px !important;
        color:var(--muted) !important;
        font-size:12px !important;
      }
      #agentSetupView [data-agent-display-group="chart"] {
        border-left:4px solid #22d3ee !important;
      }
      #agentSetupView [data-agent-display-group="status"] {
        border-left:4px solid #a78bfa !important;
      }
      #agentSetupView .agentSetupFinalBadge {
        display:inline-flex !important;
        align-items:center !important;
        width:max-content !important;
        min-height:24px !important;
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
      #agentSetupView [data-agent-display-group="chart"] .agentSetupFinalBadge {
        color:#67e8f9 !important;
        border-color:#0891b2 !important;
        background:rgba(8,145,178,.14) !important;
      }
      #agentSetupView [data-agent-display-group="status"] .agentSetupFinalBadge {
        color:#ddd6fe !important;
        border-color:#7c3aed !important;
        background:rgba(124,58,237,.14) !important;
      }
    `;
    document.head.appendChild(style);
  }

  function installHooks() {
    document.addEventListener('click', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest('#agentSetupButton, [data-view="agentSetup"], .settingsTabButton')) {
        window.setTimeout(applyFinalOrder, 40);
        window.setTimeout(applyFinalOrder, 250);
      }
    }, true);

    const view = document.getElementById('agentSetupView');
    if (view && !view.dataset.finalOrderObserver) {
      const observer = new MutationObserver(() => window.requestAnimationFrame(applyFinalOrder));
      observer.observe(view, { childList: true, subtree: true });
      view.dataset.finalOrderObserver = '1';
    }
  }

  function install() {
    installStyles();
    installHooks();
    applyFinalOrder();
    window.setTimeout(applyFinalOrder, 250);
    window.setTimeout(applyFinalOrder, 1000);
    window.setTimeout(applyFinalOrder, 2000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
