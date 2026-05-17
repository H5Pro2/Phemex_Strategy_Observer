// ==================================================
// dashboard_agent_setup_cleanup_patch.js
// ==================================================
// AGENT SETUP STRUCTURE CLEANUP PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-agent-setup-cleanup-v2-tech';
  const CHART_AGENT_KEYS = new Set(['rsi', 'vwap', 'volume']);
  const STRUCTURE_AGENT_KEYS = new Set(['breakout_fakeout']);
  const TRUE_DIRECT_AGENT_KEYS = new Set(['volatility_regime', 'risk']);

  function ensureInfoBlock(container, title, label, id, type) {
    let block = document.getElementById(id);
    if (!block) {
      block = document.createElement('div');
      block.id = id;
      block.className = `settingsGroup agentSetupInfoBlock ${type || ''}`;
      container.appendChild(block);
    }
    block.innerHTML = `<div class="agentSetupInfoHead"><strong>${title}</strong><span>${type || 'GROUP'}</span></div><div class="label">${label}</div>`;
    block.dataset.agentSetupCleanup = PATCH_VERSION;
    return block;
  }

  function ensureGroup(container, id, title, label, type) {
    let group = document.getElementById(id);
    ensureInfoBlock(container, title, label, `${id}Info`, type);
    if (!group) {
      group = document.createElement('div');
      group.id = id;
      group.className = `agentSetupReclassifiedGroup ${type || ''}`;
      container.appendChild(group);
    }
    group.dataset.agentSetupCleanup = PATCH_VERSION;
    return group;
  }

  function moveCards(container, group, keys) {
    keys.forEach(key => {
      const card = container.querySelector(`.agentDirectGroup[data-agent-section="${key}"]`);
      if (!card || card.parentNode === group) return;
      card.classList.add('agentReclassifiedCard');
      card.dataset.agentSetupClassified = PATCH_VERSION;
      group.appendChild(card);
    });
  }

  function cleanupDirectTitle(container) {
    const infoBlocks = Array.from(container.querySelectorAll(':scope > .settingsGroup'));
    infoBlocks.forEach(block => {
      const title = block.querySelector(':scope > h3');
      const label = block.querySelector(':scope > .label');
      const titleText = String(title?.textContent || '').trim();
      if (titleText !== 'Direkte Agenten ohne Chart-Indikator' && titleText !== 'Bewertungsagenten ohne eigene Chart-Pane') return;
      block.classList.add('agentSetupInfoBlock', 'direct');
      block.innerHTML = '<div class="agentSetupInfoHead"><strong>Bewertungsagenten ohne eigene Chart-Pane</strong><span>DIRECT</span></div><div class="label">Nur Risk- und Regime-Logik bleibt hier. Klassische Chart-Indikatoren werden in Chart-Indikator-Agenten einsortiert.</div>';
      block.dataset.agentSetupCleanup = PATCH_VERSION;
    });
  }

  function markTrueDirectCards(container) {
    container.querySelectorAll('.agentDirectGroup').forEach(card => {
      const key = String(card.dataset.agentSection || '');
      card.classList.toggle('agentTrueDirectCard', TRUE_DIRECT_AGENT_KEYS.has(key));
      card.classList.toggle('agentChartClassifiedCard', CHART_AGENT_KEYS.has(key));
      card.classList.toggle('agentStructureClassifiedCard', STRUCTURE_AGENT_KEYS.has(key));
    });
  }

  function installStyles() {
    const oldStyle = document.getElementById('agent-setup-cleanup-style');
    if (oldStyle && oldStyle.parentNode) oldStyle.parentNode.removeChild(oldStyle);
    const style = document.createElement('style');
    style.id = 'agent-setup-cleanup-style';
    style.textContent = `
      .agentSetupInfoBlock {
        margin-top:12px;
        padding:10px 12px !important;
        border-radius:4px !important;
        border:1px solid rgba(148,163,184,.24) !important;
        background:rgba(15,23,42,.16) !important;
        box-shadow:none !important;
      }
      .agentSetupInfoBlock h3 { display:none !important; }
      .agentSetupInfoHead {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:5px;
      }
      .agentSetupInfoHead strong {
        font-size:11px;
        font-weight:900;
        line-height:1.2;
        letter-spacing:.10em;
        text-transform:uppercase;
      }
      .agentSetupInfoHead span {
        font:10px/1.2 "JetBrains Mono", "Cascadia Code", Consolas, monospace;
        color:var(--muted);
        border:1px solid rgba(148,163,184,.22);
        border-radius:3px;
        padding:2px 6px;
      }
      .agentSetupInfoBlock .label {
        font-size:11px !important;
        line-height:1.4;
        color:var(--muted);
        text-transform:none !important;
        letter-spacing:.02em;
      }
      .agentSetupInfoBlock.chart { border-left:3px solid #38bdf8 !important; }
      .agentSetupInfoBlock.structure { border-left:3px solid #f472b6 !important; }
      .agentSetupInfoBlock.direct { border-left:3px solid #f97316 !important; }
      .agentSetupReclassifiedGroup {
        display:grid;
        grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));
        gap:12px;
        margin:10px 0 14px;
      }
      .agentReclassifiedCard {
        border-radius:4px !important;
        box-shadow:none !important;
      }
      .agentChartClassifiedCard { border-left:3px solid #38bdf8 !important; }
      .agentStructureClassifiedCard { border-left:3px solid #f472b6 !important; }
      .agentTrueDirectCard { border-left:3px solid #f97316 !important; }
      #agentChartIndicatorGroup .agentDirectGroup .label.fullWidth::after { content:' · Chart-Pane / Preislinie aktiv'; color:#67e8f9; }
      #agentStructureSignalGroup .agentDirectGroup .label.fullWidth::after { content:' · Struktur-/Signalbewertung'; color:#f9a8d4; }
      .agentDirectGroup[data-agent-section="volatility_regime"] .label.fullWidth::after,
      .agentDirectGroup[data-agent-section="risk"] .label.fullWidth::after { content:' · Bewertungslogik ohne Chart-Pane'; color:#fdba74; }
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
      'Diese Agenten haben eine Chart-Darstellung: RSI eigene Pane, Volume eigene Pane, VWAP Preislinie.',
      'chart'
    );
    const structureGroup = ensureGroup(
      container,
      'agentStructureSignalGroup',
      'Struktur- und Signalagenten',
      'Diese Agenten bewerten Chart-Struktur oder Ereignisse, sind aber keine klassischen Oszillator-Panes.',
      'structure'
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
