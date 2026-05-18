// ==================================================
// dashboard_agent_setup_final_order_patch.js
// ==================================================
// FINAL AGENT SETUP ORDER PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-18-agent-setup-final-order-v2-real-groups';
  const CHART_VIEW_SECTIONS = ['hma', 'sma', 'triple_ema', 'macd', 'mfi', 'rsi', 'vwap', 'volume'];
  const CHART_STATUS_SECTIONS = ['breakout_fakeout', 'volatility_regime', 'risk'];
  let orderScheduled = false;

  function setupView() {
    return document.getElementById('agentSetupView') || null;
  }

  function setupBody() {
    return setupView()?.querySelector('.configModalBody') || null;
  }

  function sectionGroup(section) {
    return setupView()?.querySelector(`[data-agent-section="${section}"]`) || null;
  }

  function directHeaderBlocks(body) {
    return Array.from(body?.querySelectorAll(':scope > .settingsGroup') || []).filter(block => {
      if (block.dataset.agentSection) return false;
      const title = String(block.querySelector(':scope > h3')?.textContent || '').trim();
      return /Direkte Agenten|Agenten ohne eigene Hauptchart-Linie|Nur Bewertungsagenten/i.test(title);
    });
  }

  function baseReference(body) {
    const tabs = body.querySelector(':scope > .settingsTabsBar');
    const firstNormalGroup = Array.from(body.children).find(child => {
      if (child.id === 'agentSetupChartViewGroup') return false;
      if (child.id === 'agentSetupChartStatusGroup') return false;
      if (child.classList?.contains('settingsTabsBar')) return false;
      return child.classList?.contains('settingsGroup') && !child.dataset.agentSection;
    });
    return firstNormalGroup || tabs || body.firstElementChild;
  }

  function createShell(id, mode, title, detail) {
    let shell = document.getElementById(id);
    if (!shell) {
      shell = document.createElement('section');
      shell.id = id;
      shell.className = `agentSetupFinalGroup ${mode}`;
      shell.innerHTML = `
        <div class="agentSetupFinalGroupHeader">
          <div>
            <strong>${title}</strong>
            <span>${detail}</span>
          </div>
        </div>
        <div class="agentSetupFinalCards"></div>
      `;
    }
    return shell;
  }

  function cardsContainer(shell) {
    return shell.querySelector('.agentSetupFinalCards');
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

  function removeLegacyHeaders(body) {
    directHeaderBlocks(body).forEach(block => block.remove());
    document.getElementById('agentSetupChartViewAgentsHeader')?.remove();
    document.getElementById('agentSetupChartStatusAgentsHeader')?.remove();
    document.getElementById('agentSetupEvaluationAgentsHeader')?.remove();
  }

  function moveGroupsIntoShell(sections, shell, mode, label) {
    const cards = cardsContainer(shell);
    if (!cards) return;
    sections.map(sectionGroup).filter(Boolean).forEach(group => {
      markGroup(group, mode, label);
      cards.appendChild(group);
    });
  }

  function applyFinalOrder() {
    orderScheduled = false;
    const body = setupBody();
    if (!body) return;

    const tabs = body.querySelector(':scope > .settingsTabsBar');
    if (tabs && tabs !== body.firstElementChild) body.insertBefore(tabs, body.firstElementChild);

    removeLegacyHeaders(body);

    const chartShell = createShell(
      'agentSetupChartViewGroup',
      'chart',
      'Chart View Agenten',
      'HMA, SMA, Triple EMA, MACD, MFI, RSI, VWAP und Volume werden im Chart dargestellt.'
    );
    const statusShell = createShell(
      'agentSetupChartStatusGroup',
      'status',
      'Chart Status Agenten',
      'Breakout/Fakeout, Volatility und Risk erscheinen als Statusbereich im Chartfenster.'
    );

    const reference = baseReference(body);
    insertAfter(reference, chartShell);
    insertAfter(chartShell, statusShell);

    moveGroupsIntoShell(CHART_VIEW_SECTIONS, chartShell, 'chart', 'Chart View');
    moveGroupsIntoShell(CHART_STATUS_SECTIONS, statusShell, 'status', 'Chart Status');

    chartShell.hidden = cardsContainer(chartShell)?.children.length <= 0;
    statusShell.hidden = cardsContainer(statusShell)?.children.length <= 0;

    document.body.dataset.agentSetupFinalOrderPatch = PATCH_VERSION;
  }

  function scheduleFinalOrder(delay = 40) {
    if (orderScheduled) return;
    orderScheduled = true;
    window.setTimeout(applyFinalOrder, delay);
  }

  function installStyles() {
    const oldStyle = document.getElementById('agent-setup-final-order-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'agent-setup-final-order-style';
    style.textContent = `
      #agentSetupView {
        position:relative !important;
        z-index:80 !important;
        isolation:isolate !important;
        background:var(--bg) !important;
      }
      #agentSetupView.hidden {
        display:none !important;
      }
      #agentSetupView > .card {
        position:relative !important;
        z-index:90 !important;
        width:100% !important;
        max-width:none !important;
        overflow:visible !important;
        box-shadow:0 18px 45px rgba(0,0,0,.28) !important;
      }
      #agentSetupView .configModalBody {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(390px, 1fr)) !important;
        gap:18px !important;
        align-items:start !important;
        overflow:visible !important;
      }
      #agentSetupView .settingsTabsBar,
      #agentSetupView .settingsGroup:not([data-agent-section]),
      #agentSetupView .agentSetupFinalGroup {
        grid-column:1 / -1 !important;
      }
      #agentSetupView .agentSetupFinalGroup {
        display:block !important;
        padding:14px !important;
        border:1px solid var(--line) !important;
        border-radius:10px !important;
        background:rgba(15,23,42,.22) !important;
      }
      #agentSetupView .agentSetupFinalGroup.chart {
        border-left:6px solid #22d3ee !important;
      }
      #agentSetupView .agentSetupFinalGroup.status {
        border-left:6px solid #a78bfa !important;
      }
      #agentSetupView .agentSetupFinalGroupHeader {
        display:flex !important;
        align-items:center !important;
        justify-content:space-between !important;
        min-height:56px !important;
        margin:0 0 14px !important;
        padding:4px 2px 12px !important;
        border-bottom:1px solid rgba(148,163,184,.18) !important;
      }
      #agentSetupView .agentSetupFinalGroupHeader strong {
        display:block !important;
        color:var(--ink) !important;
        font-size:15px !important;
        font-weight:900 !important;
        letter-spacing:.07em !important;
        text-transform:uppercase !important;
      }
      #agentSetupView .agentSetupFinalGroupHeader span {
        display:block !important;
        margin-top:5px !important;
        color:var(--muted) !important;
        font-size:12px !important;
        line-height:1.35 !important;
      }
      #agentSetupView .agentSetupFinalCards {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(390px, 1fr)) !important;
        gap:16px !important;
        align-items:stretch !important;
      }
      #agentSetupView .agentSetupFinalCards > .settingsGroup,
      #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup,
      #agentSetupView .agentSetupFinalCards > .agentDirectGroup,
      #agentSetupView .agentSetupFinalCards > .agentUtilityGroup {
        min-height:238px !important;
        height:238px !important;
        max-height:238px !important;
        display:flex !important;
        flex-direction:column !important;
        overflow:hidden !important;
        margin:0 !important;
      }
      #agentSetupView .agentSetupFinalCards > .settingsGroup > h3,
      #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup > h3,
      #agentSetupView .agentSetupFinalCards > .agentDirectGroup > h3,
      #agentSetupView .agentSetupFinalCards > .agentUtilityGroup > h3 {
        min-height:24px !important;
        margin-bottom:8px !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
        white-space:nowrap !important;
      }
      #agentSetupView .agentSetupFinalCards .settingsGroupGrid {
        flex:1 1 auto !important;
        display:grid !important;
        grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
        gap:10px 12px !important;
        align-content:start !important;
        overflow:hidden !important;
      }
      #agentSetupView .agentSetupFinalCards .label.fullWidth,
      #agentSetupView .agentSetupFinalCards .fullWidth {
        grid-column:1 / -1 !important;
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
      #agentSetupView .modalActions {
        position:sticky !important;
        bottom:0 !important;
        z-index:110 !important;
        background:linear-gradient(180deg, rgba(17,24,39,.92), rgba(17,24,39,.99)) !important;
        border-top:1px solid var(--line) !important;
        box-shadow:0 -12px 30px rgba(0,0,0,.22) !important;
      }
      @media (max-width:900px) {
        #agentSetupView .configModalBody,
        #agentSetupView .agentSetupFinalCards {
          grid-template-columns:1fr !important;
        }
        #agentSetupView .agentSetupFinalCards > .settingsGroup,
        #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup,
        #agentSetupView .agentSetupFinalCards > .agentDirectGroup,
        #agentSetupView .agentSetupFinalCards > .agentUtilityGroup {
          height:auto !important;
          max-height:none !important;
          min-height:238px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function installHooks() {
    document.addEventListener('click', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest('#agentSetupViewButton, #agentSetupButton, [data-view="agentSetup"], .settingsTabButton')) {
        scheduleFinalOrder(40);
        window.setTimeout(applyFinalOrder, 250);
      }
    }, true);

    const view = setupView();
    if (view && !view.dataset.finalOrderObserver) {
      const observer = new MutationObserver(mutations => {
        if (mutations.some(mutation => Array.from(mutation.addedNodes).some(node => node instanceof Element))) {
          scheduleFinalOrder(60);
        }
      });
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
