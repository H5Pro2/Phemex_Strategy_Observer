// ==================================================
// dashboard_bot_view_layout_patch.js
// ==================================================
// BOT VIEW LAYOUT PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-31-bot-view-collapse-v16-open-header-state';
  const MODE_STORAGE_KEY = 'botViewMode';
  const EXPERT_ONLY_GROUPS = new Set(['debug', 'cycle']);

  function botView() {
    return document.getElementById('dashboardView') || null;
  }

  function botViewMode() {
    try {
      return window.localStorage.getItem(MODE_STORAGE_KEY) === 'expert' ? 'expert' : 'simple';
    } catch (_) {
      return 'simple';
    }
  }

  function setBotViewMode(mode) {
    const next = mode === 'expert' ? 'expert' : 'simple';
    try {
      window.localStorage.setItem(MODE_STORAGE_KEY, next);
    } catch (_) {}
    applyBotViewMode();
  }

  function applyBotViewMode() {
    const view = botView();
    if (!view) return;
    const mode = botViewMode();
    view.dataset.botViewMode = mode;
    document.querySelectorAll('[data-bot-view-mode]').forEach(button => {
      const active = button.dataset.botViewMode === mode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    document.querySelectorAll('#dashboardView .botViewSectionHeader').forEach(header => {
      const expertOnly = EXPERT_ONLY_GROUPS.has(header.dataset.collapseKey || '');
      header.hidden = mode !== 'expert' && expertOnly;
    });
    Object.entries(collapseGroups(view)).forEach(([key, group]) => {
      if (!EXPERT_ONLY_GROUPS.has(key)) return;
      group.targets().filter(Boolean).forEach(target => {
        const header = document.getElementById(group.headerId);
        target.hidden = mode !== 'expert' || !!header?.classList.contains('collapsed');
      });
    });
  }

  function createHeader(id, title, detail, mode) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const header = document.createElement('div');
    header.id = id;
    header.className = `botViewSectionHeader ${mode || ''}`.trim();
    header.dataset.collapseKey = mode || id;
    header.tabIndex = 0;
    header.setAttribute('role', 'button');
    header.setAttribute('aria-expanded', 'true');
    header.innerHTML = `<div><strong>${title}</strong><span>${detail}</span></div>`;
    return header;
  }

  function collapseStorageKey(key) {
    return `botViewCollapsed:${key}`;
  }

  function isCollapsed(key) {
    try {
      return window.localStorage.getItem(collapseStorageKey(key)) === '1';
    } catch (_) {
      return false;
    }
  }

  function storeCollapsed(key, collapsed) {
    try {
      window.localStorage.setItem(collapseStorageKey(key), collapsed ? '1' : '0');
    } catch (_) {}
  }

  function statusData() {
    try {
      if (typeof latestStatusData !== 'undefined' && latestStatusData) return latestStatusData;
    } catch (_) {}
    return window.latestStatusData || null;
  }

  function money(value) {
    const number = Number(value || 0);
    if (!Number.isFinite(number) || number <= 0) return '$0.00000';
    return `$${number.toFixed(5)}`;
  }

  function shortNumber(value) {
    const number = Number(value || 0);
    if (!Number.isFinite(number)) return '0';
    return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 0 }).format(number);
  }

  function llmCostStats() {
    const data = statusData();
    const history = Array.isArray(data?.llm_analysis_history) ? data.llm_analysis_history : [];
    const now = new Date();
    const dayKey = now.toISOString().slice(0, 10);
    const monthKey = now.toISOString().slice(0, 7);
    const stats = {
      runs: 0,
      todayRuns: 0,
      monthRuns: 0,
      todayCost: 0,
      monthCost: 0,
      totalTokens: 0,
      last: null,
    };
    history.forEach(item => {
      const usage = item?.usage_estimate || {};
      const provider = String(item?.provider || usage.provider || '').toLowerCase();
      const type = String(item?.type || '').toLowerCase();
      const cost = Number(usage.cost_usd);
      if (provider !== 'openai' || type !== 'completed' || !Number.isFinite(cost)) return;
      const timestamp = Number(item?.time || 0) * 1000;
      const date = Number.isFinite(timestamp) && timestamp > 0 ? new Date(timestamp) : null;
      const iso = date ? date.toISOString() : '';
      stats.runs += 1;
      stats.totalTokens += Number(usage.total_tokens || 0);
      stats.last = item;
      if (iso.startsWith(dayKey)) {
        stats.todayRuns += 1;
        stats.todayCost += cost;
      }
      if (iso.startsWith(monthKey)) {
        stats.monthRuns += 1;
        stats.monthCost += cost;
      }
    });
    return stats;
  }

  function activeSymbolFromStatus(data) {
    const cfg = data?.config || {};
    try {
      if (typeof selectedAgentAsset !== 'undefined' && selectedAgentAsset) return selectedAgentAsset;
    } catch (_) {}
    try {
      if (typeof selectedAsset !== 'undefined' && selectedAsset) return selectedAsset;
    } catch (_) {}
    return (Array.isArray(cfg.symbols) && cfg.symbols[0]) || 'BTCUSDT';
  }

  function llmLayerFromStatus(data) {
    const symbol = activeSymbolFromStatus(data);
    const board = data?.cycle?.agents?.[symbol] || data?.cycle?.symbols?.[symbol]?.agents || null;
    const brain = data?.cycle?.brains?.[symbol] || data?.cycle?.symbols?.[symbol]?.brain || null;
    return board?.llm_layer || brain?.llm_layer || null;
  }

  function llmStatusSummary(data, provider, model) {
    const cfg = data?.config || {};
    const layer = llmLayerFromStatus(data);
    const trace = layer?.context_trace || layer?.input_context || null;
    const roles = Array.isArray(layer?.roles) ? layer.roles : [];
    const decision = String(layer?.decision || layer?.judge?.decision || '-').toUpperCase();
    const message = String(layer?.message || layer?.advice || layer?.risk_note || '').toLowerCase();
    const keyMissing = provider === 'openai' && window.latestEnvSettings?.openai_key_present === false;
    const providerEnabled = provider === 'ollama' ? !!cfg.ollama_enabled : !!cfg.openai_enabled;
    if (!cfg.llm_role_team_enabled) return { label: 'Deaktiviert', detail: 'LLM-Rollenteam ist ausgeschaltet.', decision: '-', tone: 'muted' };
    if (keyMissing) return { label: 'Key fehlt', detail: 'OPENAI_API_KEY fehlt oder wurde nicht geladen.', decision: '-', tone: 'bad' };
    if (!providerEnabled) return { label: 'Provider aus', detail: `${provider === 'ollama' ? 'Ollama' : 'OpenAI'} ist nicht aktiv.`, decision: '-', tone: 'bad' };
    if (String(layer?.verdict || '').toUpperCase() === 'ERROR' || /error|fehler|timeout|failed|exception/.test(message)) {
      return { label: 'Fehler', detail: layer?.message || layer?.advice || 'LLM-Lauf ist fehlgeschlagen.', decision, tone: 'bad' };
    }
    if (trace && roles.length > 0) {
      return { label: 'Antwort erhalten', detail: `${roles.length} Rollenberichte | ${trace.symbol || activeSymbolFromStatus(data)} | ${model}`, decision, tone: 'good' };
    }
    if (trace) return { label: 'Eingabedaten vorhanden', detail: 'Trace vorhanden, aber noch keine Rollenberichte.', decision, tone: 'wait' };
    return { label: 'Wartet auf Kandidat', detail: 'Noch kein Trade-Kandidat wurde an das LLM-Rollenteam übergeben.', decision: '-', tone: 'wait' };
  }

  function upsertLlmCostCard(view) {
    if (!view) return null;
    let section = document.getElementById('llmCostSummarySection');
    if (!section) {
      section = document.createElement('section');
      section.id = 'llmCostSummarySection';
      section.className = 'card botViewLlmCostCard';
      section.innerHTML = '<h2>LLM Status / Kosten</h2><div id="llmCostSummary"></div>';
    }
    const auditCard = view.querySelector(':scope > .botViewAuditCard') || document.getElementById('llmAuditSummarySection');
    const pipelineCard = document.getElementById('liveAnalysisFlowSection');
    if (auditCard?.parentNode === view && section.previousElementSibling !== auditCard) {
      view.insertBefore(section, auditCard.nextSibling);
    } else if (pipelineCard?.parentNode === view && section.parentNode !== view) {
      view.insertBefore(section, pipelineCard);
    } else if (section.parentNode !== view) {
      view.appendChild(section);
    }
    renderLlmCostSummary();
    return section;
  }

  function renderLlmCostSummary() {
    const panel = document.getElementById('llmCostSummary');
    if (!panel) return;
    const data = statusData();
    const cfg = data?.config || {};
    const provider = String(cfg.llm_provider || 'openai').toLowerCase();
    const model = provider === 'ollama' ? String(cfg.ollama_model || '-') : String(cfg.openai_model || 'gpt-4.1-mini');
    const stats = llmCostStats();
    const status = llmStatusSummary(data, provider, model);
    const last = stats.last;
    const lastUsage = last?.usage_estimate || {};
    const lastCost = provider === 'ollama' ? 'lokal' : (last ? money(lastUsage.cost_usd) : '$0.00000');
    const note = provider === 'ollama'
      ? 'Lokaler Provider: keine OpenAI API-Kosten. Strom/Hardware werden nicht berechnet.'
      : 'Schätzung aus Textlänge und Modellpreis. Die echte OpenAI-Abrechnung kann leicht abweichen.';
    panel.innerHTML = `
      <div class="botViewLlmCostGrid compact">
        <div class="wide status ${status.tone}"><span>LLM Status</span><strong>${status.label}</strong><small>${status.detail}</small></div>
        <div><span>CEO/Judge</span><strong>${status.decision}</strong><small>${provider} / ${model}</small></div>
        <div><span>Letzter Lauf</span><strong>${lastCost}</strong><small>${last?.time_utc || 'Noch kein OpenAI-Lauf'}</small></div>
        <div><span>Heute</span><strong>${money(stats.todayCost)}</strong><small>${shortNumber(stats.todayRuns)} Läufe</small></div>
        <div><span>Monat</span><strong>${money(stats.monthCost)}</strong><small>~${shortNumber(stats.totalTokens)} Tokens</small></div>
      </div>
      <div class="botViewLlmCostNote">${note}</div>
    `;
  }

  function setTargetsCollapsed(header, targets, collapsed) {
    if (!header) return;
    header.classList.toggle('collapsed', collapsed);
    header.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    targets.filter(Boolean).forEach(target => {
      target.classList.toggle('botViewCollapsedTarget', collapsed);
      target.hidden = !!collapsed;
    });
  }

  function upsertDashboardShellHeader(view) {
    if (!view) return null;
    let header = document.getElementById('botViewShellHeader');
    if (!header) {
      header = document.createElement('div');
      header.id = 'botViewShellHeader';
      header.className = 'botViewShellHeader';
      header.innerHTML = `
        <div><h2>Dashboard</h2><span>Live-Analyse, LLM-Rollenteam, Kosten, Trades und Bot-Daten auf einen Blick.</span></div>
        <div class="botViewModeSwitch" role="group" aria-label="Dashboard Modus">
          <button type="button" data-bot-view-mode="simple" aria-pressed="true">Simple</button>
          <button type="button" data-bot-view-mode="expert" aria-pressed="false">Expert</button>
        </div>
      `;
    }
    if (header.parentNode !== view || view.firstElementChild !== header) {
      view.insertBefore(header, view.firstElementChild);
    }
    return header;
  }

  function collapseGroups(view) {
    return {
      overview: {
        headerId: 'botViewOverviewHeader',
        targets: () => [view.querySelector(':scope > .botViewKpiGrid')],
      },
      control: {
        headerId: 'botViewControlHeader',
        targets: () => [view.querySelector(':scope > .botViewControlCard')],
      },
      llm: {
        headerId: 'botViewLlmHeader',
        targets: () => [view.querySelector(':scope > .botViewAuditCard')],
      },
      cost: {
        headerId: 'botViewCostHeader',
        targets: () => [view.querySelector(':scope > .botViewLlmCostCard')],
      },
      pipeline: {
        headerId: 'botViewPipelineHeader',
        targets: () => [document.getElementById('liveAnalysisFlowSection')],
      },
      trades: {
        headerId: 'botViewTradesHeader',
        targets: () => [view.querySelector(':scope > .botViewTradeDataGroup')],
      },
      debug: {
        headerId: 'botViewDebugHeader',
        targets: () => [view.querySelector(':scope > .botViewDebugCard'), view.querySelector(':scope > .botViewMemoryCard')],
      },
      cycle: {
        headerId: 'botViewCycleHeader',
        targets: () => [view.querySelector(':scope > .botViewCycleCard')],
      },
    };
  }

  function wireCollapsibleSections() {
    const view = botView();
    if (!view) return;
    Object.entries(collapseGroups(view)).forEach(([key, group]) => {
      const header = document.getElementById(group.headerId);
      if (!header) return;
      const apply = collapsed => setTargetsCollapsed(header, group.targets(), collapsed);
      apply(isCollapsed(key));
      if (header.dataset.collapseReady === PATCH_VERSION) return;
      const toggle = () => {
        const next = !header.classList.contains('collapsed');
        storeCollapsed(key, next);
        apply(next);
      };
      header.addEventListener('click', event => {
        if (event.target.closest('button, a, input, select, textarea, summary')) return;
        toggle();
      });
      header.addEventListener('keydown', event => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        toggle();
      });
      header.dataset.collapseReady = PATCH_VERSION;
    });
    applyBotViewMode();
  }

  function toggleHeader(header) {
    const view = botView();
    if (!view || !header) return;
    const key = header.dataset.collapseKey;
    const group = collapseGroups(view)[key];
    if (!key || !group) return;
    const next = !header.classList.contains('collapsed');
    storeCollapsed(key, next);
    setTargetsCollapsed(header, group.targets(), next);
    applyBotViewMode();
  }

  function installGlobalCollapseHandler() {
    if (document.body.dataset.botViewGlobalCollapseHandler === PATCH_VERSION) return;
    document.body.dataset.botViewGlobalCollapseHandler = PATCH_VERSION;
    document.addEventListener('click', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const header = target.closest('#dashboardView .botViewSectionHeader');
      if (!header || target.closest('button, a, input, select, textarea, summary')) return;
      event.preventDefault();
      event.stopPropagation();
      toggleHeader(header);
    }, true);
    document.addEventListener('keydown', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const header = target.closest('#dashboardView .botViewSectionHeader');
      if (!header || (event.key !== 'Enter' && event.key !== ' ')) return;
      event.preventDefault();
      toggleHeader(header);
    }, true);
  }

  function tagElements() {
    const view = botView();
    if (!view) return;

    const kpiGrid = view.querySelector(':scope > .grid');
    if (kpiGrid) kpiGrid.classList.add('botViewKpiGrid');

    const sections = Array.from(view.querySelectorAll(':scope > section.card, :scope > section.row'));
    sections.forEach(section => {
      const title = String(section.querySelector(':scope h2')?.textContent || '').trim().toLowerCase();
      if (section.classList.contains('settingsCard')) section.classList.add('botViewControlCard');
      if (section.id === 'llmAuditSummarySection') section.classList.add('botViewAuditCard');
      if (section.id === 'llmCostSummarySection') section.classList.add('botViewLlmCostCard');
      if (section.id === 'liveAnalysisFlowSection') section.classList.add('botViewLiveFlowCard');
      if (section.classList.contains('row')) section.classList.add('botViewTradeDataGroup');
      if (title.includes('scan debug')) section.classList.add('botViewDebugCard');
      if (title.includes('lernspeicher')) section.classList.add('botViewMemoryCard');
      if (title.includes('letzter zyklus')) section.classList.add('botViewCycleCard');
    });

    view.querySelector('.botDataCard')?.classList.add('botViewDataCard');
  }

  function insertHeaders() {
    const view = botView();
    if (!view) return;
    upsertDashboardShellHeader(view);
    tagElements();
    document.getElementById('botViewTradeHeader')?.remove();

    const kpiGrid = view.querySelector(':scope > .botViewKpiGrid');
    const controlCard = view.querySelector(':scope > .botViewControlCard');
    const auditCard = view.querySelector(':scope > .botViewAuditCard');
    const costCard = upsertLlmCostCard(view);
    const pipelineCard = document.getElementById('liveAnalysisFlowSection');
    const tradeGroup = view.querySelector(':scope > .botViewTradeDataGroup');
    const debugCard = view.querySelector(':scope > .botViewDebugCard');
    const cycleCard = view.querySelector(':scope > .botViewCycleCard');

    if (kpiGrid) view.insertBefore(createHeader('botViewOverviewHeader', 'Bot Übersicht', 'Kontostand, Paper-Ergebnis, Winrate und aktuelle Steuerung.', 'overview'), kpiGrid);
    if (controlCard) view.insertBefore(createHeader('botViewControlHeader', 'Bot Steuerung', 'Start, Stop, Reload und Asset-Ansicht.', 'control'), controlCard);
    if (auditCard) view.insertBefore(createHeader('botViewLlmHeader', 'LLM Rollenteam', 'Verbindung, Rollenberichte, CEO/Judge und Eingabedaten.', 'llm'), auditCard);
    if (costCard) view.insertBefore(createHeader('botViewCostHeader', 'LLM Status / Kosten', 'Kompakter Verbindungsstatus, letzter Rollenlauf und geschätzte Kosten.', 'cost'), costCard);
    if (pipelineCard) view.insertBefore(createHeader('botViewPipelineHeader', 'Live-Analyse Pipeline', 'Signalquellen, Trade Planner, LLM Rollen, CEO/Judge und Economic Gate.', 'pipeline'), pipelineCard);
    if (tradeGroup) view.insertBefore(createHeader('botViewTradesHeader', 'Trades / Bot Daten', 'Trade-History und kompakte Runtime-Werte nebeneinander.', 'trades'), tradeGroup);
    if (debugCard) view.insertBefore(createHeader('botViewDebugHeader', 'Debug / Lernspeicher', 'Scan-Debug und gelernte Formation-Buckets.', 'debug'), debugCard);
    if (cycleCard) view.insertBefore(createHeader('botViewCycleHeader', 'Letzter Zyklus', 'Rohdaten des letzten Bot-Zyklus separat unten.', 'cycle'), cycleCard);
    wireCollapsibleSections();
  }

  function installStyles() {
    const oldStyle = document.getElementById('bot-view-layout-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'bot-view-layout-style';
    style.textContent = `
      #dashboardView {
        width:min(100%, 1440px) !important;
        max-width:1440px !important;
        margin:0 auto !important;
        display:grid !important;
        grid-template-columns:1fr !important;
        gap:8px !important;
        padding:10px 12px 12px !important;
        border:1px solid var(--line) !important;
        border-radius:7px !important;
        background:var(--panel) !important;
        overflow-x:hidden !important;
      }
      #dashboardView.hidden {
        display:none !important;
      }
      #dashboardView,
      #dashboardView * {
        min-width:0 !important;
      }
      #dashboardView .botViewShellHeader {
        display:grid !important;
        grid-template-columns:minmax(260px, 1fr) auto !important;
        align-items:center !important;
        gap:16px !important;
        min-height:58px !important;
        padding:14px 20px !important;
        margin:0 0 4px !important;
        border-bottom:1px solid var(--line) !important;
        background:var(--panel) !important;
      }
      #dashboardView .botViewShellHeader h2 {
        margin:0 !important;
        color:var(--ink) !important;
        font-size:16px !important;
        line-height:1.2 !important;
        font-weight:900 !important;
        letter-spacing:0 !important;
        text-transform:none !important;
      }
      #dashboardView .botViewShellHeader span {
        color:var(--muted) !important;
        font-size:12px !important;
        line-height:1.25 !important;
        letter-spacing:.04em !important;
        text-transform:uppercase !important;
      }
      #dashboardView .botViewModeSwitch {
        justify-self:end !important;
        display:inline-grid !important;
        grid-template-columns:1fr 1fr !important;
        gap:3px !important;
        padding:3px !important;
        border:1px solid rgba(148,163,184,.20) !important;
        border-radius:6px !important;
        background:rgba(2,6,23,.24) !important;
      }
      #dashboardView .botViewModeSwitch button {
        min-width:74px !important;
        min-height:30px !important;
        padding:5px 10px !important;
        border:0 !important;
        border-radius:4px !important;
        background:transparent !important;
        color:var(--muted) !important;
        font-size:12px !important;
        font-weight:900 !important;
        cursor:pointer !important;
      }
      #dashboardView .botViewModeSwitch button.active {
        background:#0f766e !important;
        color:#ecfeff !important;
      }
      #dashboardView[data-bot-view-mode="simple"] .botViewSectionHeader.debug,
      #dashboardView[data-bot-view-mode="simple"] .botViewSectionHeader.cycle,
      #dashboardView[data-bot-view-mode="simple"] .botViewDebugCard,
      #dashboardView[data-bot-view-mode="simple"] .botViewMemoryCard,
      #dashboardView[data-bot-view-mode="simple"] .botViewCycleCard {
        display:none !important;
      }
      #dashboardView .botViewSectionHeader {
        display:flex !important;
        align-items:center !important;
        justify-content:space-between !important;
        cursor:pointer !important;
        user-select:none !important;
        min-height:48px !important;
        padding:9px 14px !important;
        border:1px solid var(--line) !important;
        border-radius:7px !important;
        background:rgba(15,23,42,.18) !important;
        box-shadow:none !important;
      }
      #dashboardView .botViewCollapseButton {
        display:none !important;
      }
      #dashboardView .botViewSectionHeader.collapsed {
        border-bottom:1px solid var(--line) !important;
        border-radius:7px !important;
        margin-bottom:0 !important;
      }
      #dashboardView .botViewCollapsedTarget {
        display:none !important;
      }
      #dashboardView .botViewKpiGrid.botViewCollapsedTarget,
      #dashboardView .botViewControlCard.botViewCollapsedTarget,
      #dashboardView .botViewAuditCard.botViewCollapsedTarget,
      #dashboardView .botViewLlmCostCard.botViewCollapsedTarget,
      #dashboardView .botViewLiveFlowCard.botViewCollapsedTarget,
      #dashboardView .botViewTradeDataGroup.botViewCollapsedTarget,
      #dashboardView .botViewDebugCard.botViewCollapsedTarget,
      #dashboardView .botViewMemoryCard.botViewCollapsedTarget,
      #dashboardView .botViewCycleCard.botViewCollapsedTarget,
      #dashboardView #liveAnalysisFlowSection.botViewCollapsedTarget {
        display:none !important;
      }
      #dashboardView .botViewSectionHeader.overview { border-left:4px solid rgba(45,212,191,.52) !important; background:linear-gradient(90deg, rgba(45,212,191,.035), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.control { border-left:4px solid rgba(96,165,250,.52) !important; background:linear-gradient(90deg, rgba(96,165,250,.04), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.llm { border-left:4px solid rgba(34,211,238,.52) !important; background:linear-gradient(90deg, rgba(34,211,238,.035), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.cost { border-left:4px solid rgba(56,189,248,.48) !important; background:linear-gradient(90deg, rgba(56,189,248,.03), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.pipeline { border-left:4px solid rgba(245,158,11,.54) !important; background:linear-gradient(90deg, rgba(245,158,11,.04), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.trades { border-left:4px solid rgba(20,184,166,.48) !important; background:linear-gradient(90deg, rgba(20,184,166,.03), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.debug { border-left:4px solid rgba(249,115,22,.52) !important; background:linear-gradient(90deg, rgba(249,115,22,.035), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.cycle { border-left:4px solid rgba(167,139,250,.54) !important; background:linear-gradient(90deg, rgba(167,139,250,.04), rgba(15,23,42,.12) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.overview { border-left-color:#2dd4bf !important; background:linear-gradient(90deg, rgba(45,212,191,.10), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.control { border-left-color:#60a5fa !important; background:linear-gradient(90deg, rgba(96,165,250,.11), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.llm { border-left-color:#22d3ee !important; background:linear-gradient(90deg, rgba(34,211,238,.10), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.cost { border-left-color:#38bdf8 !important; background:linear-gradient(90deg, rgba(56,189,248,.09), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.pipeline { border-left-color:#f59e0b !important; background:linear-gradient(90deg, rgba(245,158,11,.11), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.trades { border-left-color:#14b8a6 !important; background:linear-gradient(90deg, rgba(20,184,166,.09), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.debug { border-left-color:#f97316 !important; background:linear-gradient(90deg, rgba(249,115,22,.10), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.collapsed.cycle { border-left-color:#a78bfa !important; background:linear-gradient(90deg, rgba(167,139,250,.11), rgba(15,23,42,.18) 42%) !important; }
      #dashboardView .botViewSectionHeader.overview,
      #dashboardView .botViewSectionHeader.control,
      #dashboardView .botViewSectionHeader.llm,
      #dashboardView .botViewSectionHeader.cost,
      #dashboardView .botViewSectionHeader.pipeline,
      #dashboardView .botViewSectionHeader.trades,
      #dashboardView .botViewSectionHeader.debug,
      #dashboardView .botViewSectionHeader.cycle {
        margin-bottom:0 !important;
        border-bottom:0 !important;
        border-radius:7px 7px 0 0 !important;
      }
      #dashboardView .botViewSectionHeader.collapsed {
        margin-bottom:0 !important;
        border-bottom:1px solid var(--line) !important;
        border-radius:7px !important;
      }
      #dashboardView .botViewSectionHeader strong {
        display:block !important;
        color:var(--ink) !important;
        font-size:13px !important;
        font-weight:900 !important;
        letter-spacing:.045em !important;
        text-transform:uppercase !important;
      }
      #dashboardView .botViewSectionHeader span {
        display:block !important;
        margin-top:3px !important;
        color:var(--muted) !important;
        font-size:11px !important;
        line-height:1.25 !important;
      }
      #dashboardView .botViewKpiGrid {
        display:grid !important;
        grid-template-columns:repeat(4, minmax(0, 1fr)) !important;
        grid-auto-flow:row !important;
        gap:10px !important;
        margin-top:0 !important;
        padding:12px !important;
        border:1px solid var(--line) !important;
        border-top:0 !important;
        border-radius:0 0 7px 7px !important;
        background:rgba(15,23,42,.10) !important;
      }
      #dashboardView .botViewKpiGrid > .card {
        grid-column:auto !important;
        width:auto !important;
        min-height:78px !important;
        display:flex !important;
        flex-direction:column !important;
        justify-content:center !important;
        padding:12px 14px !important;
        border-left:3px solid #2dd4bf !important;
        border-radius:7px !important;
        background:rgba(15,23,42,.16) !important;
      }
      #dashboardView .botViewKpiGrid > .card h3,
      #dashboardView .botViewKpiGrid > .card .label {
        margin:0 0 8px !important;
        font-size:11px !important;
        line-height:1.2 !important;
        letter-spacing:.04em !important;
      }
      #dashboardView .botViewKpiGrid > .card strong,
      #dashboardView .botViewKpiGrid > .card .value {
        font-size:20px !important;
        line-height:1.1 !important;
      }
      #dashboardView .botViewControlCard,
      #dashboardView .botViewAuditCard,
      #dashboardView .botViewLlmCostCard,
      #dashboardView .botViewLiveFlowCard,
      #dashboardView .botViewDebugCard,
      #dashboardView .botViewMemoryCard,
      #dashboardView .botViewCycleCard {
        width:100% !important;
        max-width:none !important;
        overflow:visible !important;
        margin-top:0 !important;
        padding:12px !important;
        border-radius:7px !important;
        border-top:1px solid var(--line) !important;
      }
      #dashboardView .botViewControlCard {
        border-top:0 !important;
        border-radius:0 0 7px 7px !important;
      }
      #dashboardView .botViewAuditCard {
        margin-top:0 !important;
        border-top:0 !important;
        border-radius:0 0 7px 7px !important;
      }
      #dashboardView .botViewLlmCostCard {
        margin-top:0 !important;
        border-top:0 !important;
        border-radius:0 0 7px 7px !important;
      }
      #dashboardView .botViewLiveFlowCard {
        margin-top:0 !important;
        border-top:0 !important;
        border-radius:0 0 7px 7px !important;
      }
      #dashboardView .botViewAuditCard > h2,
      #dashboardView .botViewLlmCostCard > h2,
      #dashboardView .botViewLiveFlowCard > h2 {
        display:none !important;
      }
      #dashboardView .botViewLlmCostGrid {
        display:grid !important;
        grid-template-columns:repeat(5, minmax(0, 1fr)) !important;
        gap:8px !important;
      }
      #dashboardView .botViewLlmCostGrid.compact {
        grid-template-columns:minmax(280px, 1.6fr) minmax(150px, .9fr) minmax(150px, .9fr) minmax(120px, .7fr) minmax(120px, .7fr) !important;
      }
      #dashboardView .botViewLlmCostGrid > .wide {
        min-width:0 !important;
      }
      #dashboardView .botViewLlmCostGrid > div {
        min-height:64px !important;
        padding:9px 10px !important;
        border:1px solid var(--line) !important;
        border-radius:6px !important;
        background:rgba(15,23,42,.18) !important;
      }
      #dashboardView .botViewLlmCostGrid > .status.good {
        border-left:3px solid #22c55e !important;
      }
      #dashboardView .botViewLlmCostGrid > .status.wait {
        border-left:3px solid #f59e0b !important;
      }
      #dashboardView .botViewLlmCostGrid > .status.bad {
        border-left:3px solid #ef4444 !important;
      }
      #dashboardView .botViewLlmCostGrid span {
        display:block !important;
        color:var(--muted) !important;
        font-size:10px !important;
        font-weight:900 !important;
        letter-spacing:.055em !important;
        text-transform:uppercase !important;
      }
      #dashboardView .botViewLlmCostGrid strong {
        display:block !important;
        margin-top:5px !important;
        color:var(--ink) !important;
        font-size:13px !important;
        line-height:1.2 !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
        white-space:nowrap !important;
      }
      #dashboardView .botViewLlmCostGrid small {
        display:block !important;
        margin-top:3px !important;
        color:var(--muted) !important;
        font-size:10px !important;
        line-height:1.2 !important;
        overflow:hidden !important;
        text-overflow:ellipsis !important;
        white-space:nowrap !important;
      }
      #dashboardView .botViewLlmCostNote {
        margin-top:8px !important;
        color:var(--muted) !important;
        font-size:11px !important;
        line-height:1.35 !important;
      }
      #dashboardView .botViewControlCard h2 {
        margin:0 0 12px !important;
        font-size:14px !important;
        line-height:1.2 !important;
      }
      #dashboardView .botViewControlCard .controls {
        display:grid !important;
        grid-template-columns:repeat(4, minmax(120px, 160px)) minmax(210px, 290px) minmax(190px, 240px) !important;
        justify-content:start !important;
        gap:8px !important;
        align-items:end !important;
        max-width:1190px !important;
      }
      #dashboardView .botViewControlCard .controlButton {
        width:100% !important;
        min-height:36px !important;
        padding:7px 10px !important;
        font-size:12px !important;
      }
      #dashboardView .botViewControlCard #controlStatus {
        min-height:36px !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        text-align:center !important;
        padding:7px 10px !important;
        font-size:12px !important;
        line-height:1.25 !important;
      }
      #dashboardView .botViewControlCard label {
        font-size:11px !important;
        line-height:1.2 !important;
        margin-bottom:4px !important;
      }
      #dashboardView .botViewControlCard select {
        min-height:36px !important;
        padding:7px 10px !important;
        font-size:12px !important;
      }
      #dashboardView .botViewTradeDataGroup {
        display:grid !important;
        grid-template-columns:minmax(0, 2fr) minmax(320px, .85fr) !important;
        gap:16px !important;
        align-items:stretch !important;
        margin-top:0 !important;
        padding:12px !important;
        border:1px solid var(--line) !important;
        border-top:0 !important;
        border-radius:0 0 7px 7px !important;
        background:rgba(15,23,42,.10) !important;
      }
      #dashboardView .botViewTradeDataGroup > .card {
        min-height:430px !important;
        height:100% !important;
        overflow:hidden !important;
      }
      #dashboardView .botViewTradeDataGroup .tradeTableWrap,
      #dashboardView .botViewDebugCard,
      #dashboardView .botViewMemoryCard {
        overflow:auto !important;
      }
      #dashboardView .botViewDataCard table,
      #dashboardView .botViewDebugCard table,
      #dashboardView .botViewMemoryCard table {
        width:100% !important;
      }
      #dashboardView .botViewDebugCard,
      #dashboardView .botViewMemoryCard {
        min-height:260px !important;
      }
      #dashboardView .botViewDebugCard {
        border-radius:0 0 7px 7px !important;
        border-top:0 !important;
      }
      #dashboardView .botViewMemoryCard {
        min-height:220px !important;
      }
      #dashboardView .botViewCycleCard {
        border-radius:0 0 7px 7px !important;
        border-top:0 !important;
      }
      #dashboardView .botViewCycleCard pre {
        max-height:460px !important;
        overflow:auto !important;
        border:1px solid rgba(148,163,184,.18) !important;
        border-radius:8px !important;
        padding:12px !important;
        background:rgba(2,6,23,.38) !important;
      }
      @media (max-width:1200px) {
        #dashboardView .botViewKpiGrid {
          grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
        }
        #dashboardView .botViewControlCard .controls {
          grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
          max-width:none !important;
        }
        #dashboardView .botViewLlmCostGrid {
          grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
        }
        #dashboardView .botViewTradeDataGroup {
          grid-template-columns:1fr !important;
        }
      }
      @media (max-width:760px) {
        #dashboardView .botViewShellHeader {
          grid-template-columns:1fr !important;
          gap:4px !important;
        }
        #dashboardView .botViewShellHeader span {
          justify-self:start !important;
          text-align:left !important;
        }
        #dashboardView .botViewModeSwitch {
          justify-self:start !important;
          width:100% !important;
        }
        #dashboardView .botViewKpiGrid {
          grid-template-columns:1fr !important;
        }
        #dashboardView .botViewLlmCostGrid {
          grid-template-columns:1fr !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function install() {
    installStyles();
    installGlobalCollapseHandler();
    insertHeaders();
    wireCollapsibleSections();
    applyBotViewMode();
    window.setTimeout(() => { insertHeaders(); wireCollapsibleSections(); applyBotViewMode(); }, 250);
    window.setTimeout(() => { insertHeaders(); wireCollapsibleSections(); applyBotViewMode(); }, 1000);
    window.setInterval(() => { renderLlmCostSummary(); wireCollapsibleSections(); applyBotViewMode(); }, 2500);
    document.body.dataset.botViewLayoutPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  document.addEventListener('click', event => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const button = target.closest('[data-bot-view-mode]');
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    setBotViewMode(button.dataset.botViewMode);
  }, true);
})();
