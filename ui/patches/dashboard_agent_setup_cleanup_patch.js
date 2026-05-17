// ==================================================
// dashboard_agent_setup_cleanup_patch.js
// ==================================================
// AGENT SETUP STRUCTURE CLEANUP PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-agent-setup-cleanup-v1';
  const CHART_AGENT_KEYS = new Set(['rsi', 'vwap', 'volume']);
  const STRUCTURE_AGENT_KEYS = new Set(['breakout_fakeout']);
  const TRUE_DIRECT_AGENT_KEYS = new Set(['volatility_regime', 'risk']);

  function ensureInfoBlock(container, title, label, id) {
    let block = document.getElementById(id);
    if (block) return block;
    block = document.createElement('div');
    block.id = id;
    block.className = 'settingsGroup agentSetupInfoBlock';
    block.innerHTML = `<h3>${title}</h3><div class="label">${label}</div>`;
    container.appendChild(block);
    return block;
  }

  function ensureGroup(container, id, title, label) {
    let group = document.getElementById(id);
    if (group) return group;
    ensureInfoBlock(container, title, label, `${id}Info`);
    group = document.createElement('div');
    group.id = id;
    group.className = 'agentSetupReclassifiedGroup';
    container.appendChild(group);
    return group;
  }

  function moveCards(container, group, keys) {
    keys.forEach(key => {
      const card = container.querySelector(`.agentDirectGroup[data-agent-section="${key}"]`);
      if (!card || card.parentNode === group) return;
      card.classList.add('agentReclassifiedCard');
      group.appendChild(card);
    });
  }

  function cleanupDirectTitle(container) {
    const infoBlocks = Array.from(container.querySelectorAll(':scope > .settingsGroup'));
    infoBlocks.forEach(block => {
      const title = block.querySelector(':scope > h3');
      const label = block.querySelector(':scope > .label');
      const titleText = String(title?.textContent || '').trim();
      if (titleText !== 'Direkte Agenten ohne Chart-Indikator') return;
      title.textContent = 'Bewertungsagenten ohne eigene Chart-Pane';
      if (label) label.textContent = 'Nur Agenten ohne eigene Chart-Pane oder Preislinie bleiben in diesem Bereich.';
      block.dataset.agentSetupCleanup = PATCH_VERSION;
    });
  }

  function markTrueDirectCards(container) {
    container.querySelectorAll('.agentDirectGroup').forEach(card => {
      const key = String(card.dataset.agentSection || '');
      card.classList.toggle('agentTrueDirectCard', TRUE_DIRECT_AGENT_KEYS.has(key));
    });
  }

  function installStyles() {
    const oldStyle = document.getElementById('agent-setup-cleanup-style');
    if (oldStyle && oldStyle.parentNode) oldStyle.parentNode.removeChild(oldStyle);
    const style = document.createElement('style');
    style.id = 'agent-setup-cleanup-style';
    style.textContent = `
      .agentSetupInfoBlock { margin-top:12px; border-radius:4px !important; }
      .agentSetupReclassifiedGroup { display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:14px; margin:12px 0 14px; }
      .agentReclassifiedCard { border-left:3px solid var(--agent-card-color, #38bdf8) !important; }
      .agentTrueDirectCard { border-left:3px solid var(--agent-card-color, #f97316) !important; }
      #agentChartIndicatorGroup .agentDirectGroup .label.fullWidth::after { content:' · Chart-Darstellung aktiv'; color:#67e8f9; }
      #agentStructureSignalGroup .agentDirectGroup .label.fullWidth::after { content:' · Struktur-/Signalbewertung'; color:#f9a8d4; }
    `;
    document.head.appendChild(style);
  }

  function cleanupAgentSetup() {
    const container = document.getElementById('agentSettingsGroups');
    if (!container) return;
    const cards = container.querySelectorAll('.agentDirectGroup');
    if (!cards.length) return;

    installStyles();

    const chartGroup = ensureGroup(
      container,
      'agentChartIndicatorGroup',
      'Chart-Indikator-Agenten',
      'Diese Agenten haben jetzt eine Chart-Darstellung: RSI eigene Pane, Volume eigene Pane, VWAP Preislinie.'
    );
    const structureGroup = ensureGroup(
      container,
      'agentStructureSignalGroup',
      'Struktur- und Signalagenten',
      'Diese Agenten bewerten Chart-Struktur oder Ereignisse, sind aber keine klassischen Oszillator-Panes.'
    );

    moveCards(container, chartGroup, CHART_AGENT_KEYS);
    moveCards(container, structureGroup, STRUCTURE_AGENT_KEYS);
    cleanupDirectTitle(container);
    markTrueDirectCards(container);
    document.body.dataset.agentSetupCleanupPatch = PATCH_VERSION;
  }

  function install() {
    cleanupAgentSetup();
    const target = document.getElementById('agentSetupView') || document.body;
    if (!window.__agentSetupCleanupObserver && target) {
      window.__agentSetupCleanupObserver = new MutationObserver(() => cleanupAgentSetup());
      window.__agentSetupCleanupObserver.observe(target, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
