// ==================================================
// dashboard_agent_setup_final_order_patch.js
// ==================================================
// FINAL AGENT SETUP ORDER PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-31-agent-setup-analyst-groups-v14-header-accent-full';
  const STRUCTURE_SECTIONS = ['bos_choch', 'box', 'swing_labels', 'support_resistance'];
  const CHART_VIEW_SECTIONS = ['hma', 'sma', 'triple_ema', 'macd', 'mfi', 'rsi', 'vwap', 'volume'];
  const CHART_STATUS_SECTIONS = ['breakout_fakeout', 'volatility_regime', 'risk'];
  const BRAIN_OLLAMA_SECTIONS = ['brain_ceo', 'ollama_audit'];
  const ALL_AGENT_SECTIONS = STRUCTURE_SECTIONS.concat(CHART_VIEW_SECTIONS, CHART_STATUS_SECTIONS, BRAIN_OLLAMA_SECTIONS);
  const SECTION_LABELS = {
    bos_choch: 'BOS/CHoCH',
    box: 'LL/HH Box',
    swing_labels: 'HH/LH/HL/LL',
    support_resistance: 'Support/Resistance',
    hma: 'HMA',
    sma: 'SMA',
    triple_ema: 'Triple EMA',
    macd: 'MACD',
    mfi: 'MFI',
    rsi: 'RSI',
    vwap: 'VWAP',
    volume: 'Volume',
    breakout_fakeout: 'Breakout/Fakeout',
    volatility_regime: 'Volatilität',
    risk: 'Risk Gate',
    brain_ceo: 'Trade Planner',
    ollama_audit: 'LLM Rollen'
  };
  const AGENT_TAB_GROUPS = {
    bos_choch: 'structure',
    box: 'structure',
    swing_labels: 'structure',
    support_resistance: 'structure',
    breakout_fakeout: 'structure',
    hma: 'trend',
    sma: 'trend',
    triple_ema: 'trend',
    vwap: 'trend',
    macd: 'oscillator',
    mfi: 'oscillator',
    rsi: 'oscillator',
    volume: 'context',
    volatility_regime: 'context',
    risk: 'context',
    brain_ceo: 'context',
    ollama_audit: 'context'
  };
  let orderScheduled = false;
  let suppressOrderObserverUntil = 0;

  function setupView() {
    return document.getElementById('agentSetupView') || null;
  }

  function setupBody() {
    return setupView()?.querySelector('.configModalBody') || null;
  }

  function sectionGroup(section) {
    const groups = Array.from(setupView()?.querySelectorAll(`[data-agent-section="${section}"]`) || []);
    if (!groups.length) return null;
    const newestRevision = Math.max(...groups.map(group => Number(group.dataset.agentRenderRevision || 0)));
    const candidates = newestRevision > 0 ? groups.filter(group => Number(group.dataset.agentRenderRevision || 0) === newestRevision) : groups;
    const keeper = candidates[0] || groups[0];
    groups.filter(group => group !== keeper).forEach(group => group.remove());
    return keeper;
  }

  function directHeaderBlocks(body) {
    return Array.from(body?.querySelectorAll('.settingsGroup') || []).filter(block => {
      if (block.dataset.agentSection) return false;
      const title = String(block.querySelector(':scope > h3')?.textContent || '').trim();
      const text = String(block.textContent || '').trim();
      return /Direkte Signalquellen|Signalquellen ohne eigene Hauptchart-Linie|Nur Bewertungsquellen|Direkte Agenten|Agenten ohne eigene Hauptchart-Linie|Nur Bewertungsagenten|ohne Chart-Indikator/i.test(title)
        || /keinen eigenen Preis-Indikator|ohne Chart-Indikator/i.test(text);
    });
  }

  function baseReference(body) {
    const firstNormalGroup = Array.from(body.children).find(child => {
      if (child.id === 'agentSetupStructureGroup') return false;
      if (child.id === 'agentSetupChartViewGroup') return false;
      if (child.id === 'agentSetupChartStatusGroup') return false;
      if (child.id === 'agentSetupBrainOllamaGroup') return false;
      if (child.id === 'agentSetupPlannerGroup') return false;
      if (child.id === 'agentSetupLlmRoleGroup') return false;
      if (child.classList?.contains('settingsTabsBar')) return false;
      return child.classList?.contains('settingsGroup') && !child.dataset.agentSection;
    });
    return firstNormalGroup || body.firstElementChild;
  }

  function createShell(id, mode, title, detail) {
    let shell = document.getElementById(id);
    const isNewShell = !shell;
    if (isNewShell) {
      shell = document.createElement('section');
      shell.id = id;
      shell.className = `agentSetupFinalGroup ${mode}`;
      shell.innerHTML = `
        <div class="agentSetupFinalGroupHeader">
          <div>
            <strong>${title}</strong>
            <span>${detail}</span>
            <em class="agentSetupFinalMeta">aktive Datenquellen 0/0</em>
          </div>
        </div>
        <div class="agentSetupFinalCards"></div>
        <div class="agentSetupFinalEmpty" hidden>Keine Quellen in dieser Rolle.</div>
      `;
    }
    const header = shell.querySelector(':scope > .agentSetupFinalGroupHeader');
    header?.querySelector('[data-agent-final-toggle]')?.remove();
    if (header) {
      header.dataset.agentFinalHeaderToggle = id;
      header.tabIndex = 0;
      header.setAttribute('role', 'button');
      header.setAttribute('aria-expanded', shell.classList.contains('agentSetupFinalGroupCollapsed') ? 'false' : 'true');
    }
    shell.dataset.agentCategory = mode;
    if (isNewShell || !shell.dataset.collapseStateReady) restoreShellState(shell);
    shell.dataset.collapseStateReady = '1';
    return shell;
  }

  function ensureDecisionPipeline(shell) {
    if (!shell || shell.id !== 'agentSetupPlannerGroup') return;
    let pipeline = shell.querySelector(':scope > .agentDecisionPipeline');
    if (!pipeline) {
      pipeline = document.createElement('div');
      pipeline.className = 'agentDecisionPipeline';
      pipeline.innerHTML = `
        <span>Signalquellen</span><b>-></b>
        <span>Trade Planner</span><b>-></b>
        <span>LLM Rollen</span><b>-></b>
        <span>CEO/Judge</span><b>-></b>
        <span>Economic Gate</span>
      `;
      const cards = cardsContainer(shell);
      shell.insertBefore(pipeline, cards || shell.firstChild);
    }
  }

  function shellStorageKey(shell) {
    return `agentSetupCategoryCollapsed:${shell.id}`;
  }

  function restoreShellState(shell) {
    const collapsed = localStorage.getItem(shellStorageKey(shell)) === 'true';
    setShellCollapsed(shell, collapsed, false);
  }

  function setShellCollapsed(shell, collapsed, persist = true) {
    if (!shell) return;
    shell.classList.toggle('agentSetupFinalGroupCollapsed', !!collapsed);
    shell.querySelector(':scope > .agentSetupFinalGroupHeader')?.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    if (persist) localStorage.setItem(shellStorageKey(shell), collapsed ? 'true' : 'false');
  }

  function cardsContainer(shell) {
    return shell.querySelector('.agentSetupFinalCards');
  }

  function insertAfter(reference, node) {
    if (!reference || !node || !reference.parentNode) return reference;
    if (reference.nextSibling === node) return node;
    reference.parentNode.insertBefore(node, reference.nextSibling);
    return node;
  }

  function markGroup(group, mode, label) {
    if (!group) return;
    if (group.dataset.agentDisplayGroup !== mode) group.dataset.agentDisplayGroup = mode;
    const tabCategory = AGENT_TAB_GROUPS[group.dataset.agentSection || ''] || 'context';
    if (group.dataset.agentCategory !== tabCategory) group.dataset.agentCategory = tabCategory;
    const chartView = mode === 'structure' || mode === 'chart' || mode === 'status' ? 'true' : 'false';
    if (group.dataset.chartView !== chartView) group.dataset.chartView = chartView;
    const grid = group.querySelector('.settingsGroupGrid');
    if (!grid) return;
    group.querySelectorAll('.agentChartModeBadge').forEach(badge => badge.remove());
    let badge = grid.querySelector(':scope > .agentSetupFinalBadge');
    if (!badge) {
      badge = document.createElement('div');
      badge.className = 'agentSetupFinalBadge fullWidth';
      grid.insertBefore(badge, grid.firstChild);
    } else if (badge !== grid.firstElementChild) {
      grid.insertBefore(badge, grid.firstChild);
    }
    if (badge.textContent !== label) badge.textContent = label;
  }

  function isGroupActive(group) {
    const input = group?.querySelector('[data-agent-enabled]');
    return !input || input.checked !== false;
  }

  function groupDisplayName(group) {
    const section = String(group?.dataset.agentSection || '').trim();
    if (SECTION_LABELS[section]) return SECTION_LABELS[section];
    const title = String(group?.querySelector(':scope > h3')?.textContent || '').trim();
    if (title) return title.replace(/ Agent$/i, '').trim();
    return section.replace(/_/g, ' ').trim() || 'Quelle';
  }

  function updateShellMetric(shell) {
    if (!shell) return;
    const cards = cardsContainer(shell);
    const meta = shell.querySelector('.agentSetupFinalMeta');
    if (!cards || !meta) return;
    const groups = Array.from(cards.querySelectorAll('[data-agent-section]'));
    const sourceGroups = groups.filter(group => group.querySelector('[data-agent-enabled]'));
    if (!sourceGroups.length) {
      meta.textContent = groups.length ? `${groups.length} Setup-Bereich${groups.length === 1 ? '' : 'e'}` : 'keine Bereiche';
      return;
    }
    const active = sourceGroups.filter(isGroupActive).length;
    const activeNames = sourceGroups.filter(isGroupActive).map(groupDisplayName);
    const visibleNames = activeNames.slice(0, 3);
    const remaining = Math.max(0, activeNames.length - visibleNames.length);
    const nameSuffix = visibleNames.length
      ? `: ${visibleNames.join(', ')}${remaining ? ` +${remaining}` : ''}`
      : '';
    meta.textContent = `LLM-Daten ${active}/${sourceGroups.length}${nameSuffix}`;
    meta.title = activeNames.length ? `Aktiv an LLM: ${activeNames.join(', ')}` : 'Keine aktive Datenquelle in dieser Rolle.';
  }

  function updateAllShellMetrics() {
    ['agentSetupPlannerGroup', 'agentSetupLlmRoleGroup', 'agentSetupStructureGroup', 'agentSetupChartViewGroup', 'agentSetupChartStatusGroup']
      .map(id => document.getElementById(id))
      .forEach(updateShellMetric);
  }

  function configSnapshot() {
    try {
      if (typeof latestConfig !== 'undefined' && latestConfig) return latestConfig;
    } catch (_) {}
    try {
      if (typeof latestStatusData !== 'undefined' && latestStatusData?.config) return latestStatusData.config;
    } catch (_) {}
    return window.latestStatusData?.config || window.latestConfig || null;
  }

  async function fetchConfigSnapshot() {
    const existing = configSnapshot();
    if (existing && Object.keys(existing).length) return existing;
    try {
      const response = await fetch('/api/status', { cache: 'no-store' });
      if (!response.ok) return null;
      const data = await response.json();
      return data?.config || null;
    } catch (_) {
      return null;
    }
  }

  function syncFieldValueFromConfig(id, value) {
    const input = document.getElementById(id);
    if (!input || value === undefined || value === null) return;
    if (document.activeElement === input) return;
    const next = String(value);
    const current = String(input.value || '');
    const emptyNumber = input.type !== 'color' && current.trim() === '';
    const emptyColor = input.type === 'color' && (!current || current.toLowerCase() === '#000000');
    if (!emptyNumber && !emptyColor) return;
    input.value = next;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  async function syncEmptyIndicatorFieldsFromConfig() {
    const cfg = await fetchConfigSnapshot();
    if (!cfg) return;
    const pairs = [
      ['cfgIndicatorSwingSize', cfg.indicator_swing_size],
      ['cfgIndicatorHhllRange', cfg.indicator_hhll_range],
      ['cfgIndicatorBoxExtendCandles', cfg.indicator_box_extend_candles],
      ['cfgIndicatorBosChochLookbackDays', cfg.indicator_bos_choch_lookback_days ?? cfg.indicator_lookback_days],
      ['cfgIndicatorBoxesLookbackDays', cfg.indicator_boxes_lookback_days ?? cfg.indicator_lookback_days],
      ['cfgIndicatorSwingLabelsLookbackDays', cfg.indicator_swing_labels_lookback_days ?? cfg.indicator_lookback_days],
      ['cfgIndicatorHmaLookbackDays', cfg.indicator_hma_lookback_days],
      ['cfgIndicatorSmaLookbackDays', cfg.indicator_sma_lookback_days],
      ['cfgIndicatorTripleEmaLookbackDays', cfg.indicator_triple_ema_lookback_days],
      ['cfgIndicatorMfiLookbackDays', cfg.indicator_mfi_lookback_days],
      ['cfgIndicatorMacdLookbackDays', cfg.indicator_macd_lookback_days],
      ['cfgIndicatorBosConfirmation', cfg.indicator_bos_confirmation || 'Wicks'],
      ['cfgIndicatorHmaPeriod', cfg.indicator_hma_period],
      ['cfgIndicatorSmaPeriod', cfg.indicator_sma_period],
      ['cfgIndicatorTripleEmaPeriod', cfg.indicator_triple_ema_period],
      ['cfgIndicatorTripleEmaSlowPeriod', cfg.indicator_triple_ema_slow_period],
      ['cfgIndicatorMfiPeriod', cfg.indicator_mfi_period],
      ['cfgIndicatorMacdFastPeriod', cfg.indicator_macd_fast_period],
      ['cfgIndicatorMacdSlowPeriod', cfg.indicator_macd_slow_period],
      ['cfgIndicatorMacdSignalPeriod', cfg.indicator_macd_signal_period],
      ['cfgIndicatorSrPivotPeriod', cfg.indicator_sr_pivot_period],
      ['cfgIndicatorSrSource', cfg.indicator_sr_source || 'High/Low'],
      ['cfgIndicatorSrMaxPivots', cfg.indicator_sr_max_pivots],
      ['cfgIndicatorSrChannelWidthPercent', cfg.indicator_sr_channel_width_percent],
      ['cfgIndicatorSrMaxLevels', cfg.indicator_sr_max_levels],
      ['cfgIndicatorSrMinStrength', cfg.indicator_sr_min_strength],
      ['cfgIndicatorRisingColor', cfg.indicator_bos_rising_color || cfg.indicator_rising_color],
      ['cfgIndicatorFallingColor', cfg.indicator_bos_falling_color || cfg.indicator_falling_color],
      ['cfgIndicatorSwingRisingColor', cfg.indicator_swing_rising_color || cfg.indicator_rising_color],
      ['cfgIndicatorSwingFallingColor', cfg.indicator_swing_falling_color || cfg.indicator_falling_color],
      ['cfgIndicatorBoxHighColor', cfg.indicator_box_high_color],
      ['cfgIndicatorBoxLowColor', cfg.indicator_box_low_color],
      ['cfgIndicatorHmaColor', cfg.indicator_hma_color],
      ['cfgIndicatorSmaColor', cfg.indicator_sma_color],
      ['cfgIndicatorTripleEmaColor', cfg.indicator_triple_ema_color],
      ['cfgIndicatorTripleEmaSlowColor', cfg.indicator_triple_ema_slow_color],
      ['cfgIndicatorMfiColor', cfg.indicator_mfi_color],
      ['cfgIndicatorMacdColor', cfg.indicator_macd_color],
      ['cfgIndicatorMacdSignalColor', cfg.indicator_macd_signal_color],
      ['cfgIndicatorMacdHistogramColor', cfg.indicator_macd_histogram_color],
      ['cfgIndicatorSrSupportColor', cfg.indicator_sr_support_color],
      ['cfgIndicatorSrResistanceColor', cfg.indicator_sr_resistance_color],
    ];
    pairs.forEach(([id, value]) => syncFieldValueFromConfig(id, value));
  }

  function removeLegacyHeaders(body) {
    directHeaderBlocks(body).forEach(block => block.remove());
    body.querySelectorAll('#agentSettingsGroups > .settingsGroup:not([data-agent-section])').forEach(block => block.remove());
    document.getElementById('agentSetupStructureAgentsHeader')?.remove();
    document.getElementById('agentSetupChartViewAgentsHeader')?.remove();
    document.getElementById('agentSetupChartStatusAgentsHeader')?.remove();
    document.getElementById('agentSetupEvaluationAgentsHeader')?.remove();
  }

  function moveGroupsIntoShell(sections, shell, mode, label) {
    const cards = cardsContainer(shell);
    if (!cards) return;
    sections.map(sectionGroup).filter(Boolean).forEach(group => {
      markGroup(group, mode, label);
      if (group.parentElement !== cards) cards.appendChild(group);
    });
  }

  function moveGroupsByAnalyst(sectionSpecs) {
    sectionSpecs.forEach(spec => {
      const group = sectionGroup(spec.section);
      if (!group) return;
      const cards = cardsContainer(spec.shell);
      if (!cards) return;
      markGroup(group, spec.mode, spec.label);
      if (group.parentElement !== cards) cards.appendChild(group);
    });
  }

  function syncShellTabVisibility() {
    ['agentSetupPlannerGroup', 'agentSetupLlmRoleGroup', 'agentSetupStructureGroup', 'agentSetupChartViewGroup', 'agentSetupChartStatusGroup'].forEach(id => {
      const shell = document.getElementById(id);
      const cards = cardsContainer(shell);
      if (!shell || !cards) return;
      const cardList = Array.from(cards.querySelectorAll('[data-agent-section]'));
      const hasCards = cardList.length > 0;
      shell.hidden = !hasCards;
      shell.dataset.agentTabEmpty = 'false';
      const empty = shell.querySelector('.agentSetupFinalEmpty');
      if (empty) empty.hidden = hasCards;
      updateShellMetric(shell);
    });
  }

  function applyFinalOrder() {
    orderScheduled = false;
    const body = setupBody();
    if (!body) return;
    suppressOrderObserverUntil = Date.now() + 500;
    normalizeSetupCopy();

    body.querySelectorAll(':scope > .settingsTabsBar').forEach(tabs => tabs.remove());
    const view = setupView();
    if (view) view.dataset.agentTab = 'all';

    removeLegacyHeaders(body);

    const structureShell = createShell(
      'agentSetupStructureGroup',
      'structure',
      'Market Structure Analyst',
      'Nutzt BOS/CHoCH, LL/HH, Swing und Support/Resistance als Struktur-Daten.'
    );
    const chartShell = createShell(
      'agentSetupChartViewGroup',
      'chart',
      'Momentum Analyst',
      'Nutzt HMA/SMA/Triple EMA, MACD, MFI, RSI, VWAP und Volume als Momentum-Daten.'
    );
    const statusShell = createShell(
      'agentSetupChartStatusGroup',
      'status',
      'Risk Officer / Kontext',
      'Nutzt Breakout/Fakeout, Volatilität und Risk-Gate-Daten für Risiko-Kontext.'
    );
    const plannerShell = createShell(
      'agentSetupPlannerGroup',
      'brain',
      'Strategie Engine / Trade Planner',
      'Baut den deterministischen Trade-Kandidaten aus Signalquellen, Memory und Entry-Logik.'
    );
    ensureDecisionPipeline(plannerShell);
    const llmShell = createShell(
      'agentSetupLlmRoleGroup',
      'llm',
      'LLM Rollen-Team',
      'Spezialisierte Rollen prüfen den Kandidaten; CEO/Judge entscheidet APPROVE, WAIT oder BLOCK.'
    );

    const reference = baseReference(body);
    insertAfter(reference, plannerShell);
    insertAfter(plannerShell, llmShell);
    insertAfter(llmShell, structureShell);
    insertAfter(structureShell, chartShell);
    insertAfter(chartShell, statusShell);

    moveGroupsByAnalyst(
      ALL_AGENT_SECTIONS.map(section => {
        if (STRUCTURE_SECTIONS.includes(section)) return { section, shell: structureShell, mode: 'structure', label: 'Market Structure Daten' };
        if (CHART_VIEW_SECTIONS.includes(section)) return { section, shell: chartShell, mode: 'chart', label: 'Momentum Daten' };
        if (CHART_STATUS_SECTIONS.includes(section)) return { section, shell: statusShell, mode: 'status', label: 'Risiko-/Kontext Daten' };
        if (section === 'ollama_audit') return { section, shell: llmShell, mode: 'llm', label: 'LLM Rollenklasse' };
        return { section, shell: plannerShell, mode: 'brain', label: 'Strategie Engine / Trade Planner' };
      })
    );

    syncShellTabVisibility();
    updateAllShellMetrics();
    syncEmptyIndicatorFieldsFromConfig();
    window.setTimeout(syncEmptyIndicatorFieldsFromConfig, 250);

    document.body.dataset.agentSetupFinalOrderPatch = PATCH_VERSION;
  }

  function scheduleFinalOrder(delay = 40) {
    if (orderScheduled) return;
    orderScheduled = true;
    window.setTimeout(applyFinalOrder, delay);
  }

  function normalizeSetupCopy() {
    const view = setupView();
    if (!view) return;
    const header = view.querySelector('.replayHeader');
    if (header) {
      const heading = header.querySelector('h2');
      const copy = header.querySelector('.label');
      if (heading) heading.textContent = 'Strategie Setup';
      if (copy) copy.textContent = 'Indikatoren liefern Daten an spezialisierte Analysten. Trade Planner baut Kandidaten, LLM-Rollen bewerten und CEO/Judge entscheidet.';
    }
    const introGroup = view.querySelector('.configModalBody > .settingsGroup:not([data-agent-section])');
    if (introGroup) introGroup.remove();
    const brainTitle = view.querySelector('[data-agent-section="brain_ceo"] > h3');
    if (brainTitle) brainTitle.textContent = 'Strategie Engine / Trade Planner';
    const brainGroup = view.querySelector('[data-agent-section="brain_ceo"]');
    if (brainGroup) {
      brainGroup.classList.add('plannerGroup');
      brainGroup.dataset.flowLabel = '1. Planung';
    }
    const roleTitle = view.querySelector('[data-agent-section="ollama_audit"] > h3');
    if (roleTitle) roleTitle.textContent = 'LLM Rollen-Team';
    const roleGroup = view.querySelector('[data-agent-section="ollama_audit"]');
    if (roleGroup) {
      roleGroup.classList.add('llmTeamGroup');
      roleGroup.dataset.flowLabel = '2. LLM Review';
      const grid = roleGroup.querySelector('.settingsGroupGrid');
      if (grid && !grid.querySelector('.llmSetupSection')) {
        const containsId = (id) => {
          const node = grid.querySelector(`#${id}`);
          return node ? node.closest(':scope > div') : null;
        };
        const teamToggleRow = containsId('cfgLlmRoleTeamEnabled');
        const providerSelectRow = containsId('cfgLlmProvider');
        const roleCards = grid.querySelector(':scope > .llmRoleCards');
        const rolesSection = document.createElement('div');
        rolesSection.className = 'llmRolesSection';
        rolesSection.setAttribute('aria-label', 'LLM Rollen');
        rolesSection.innerHTML = '<h4>Rollen-Team</h4><p>Spezialisierte Rollen bewerten den Trade-Kandidaten.</p>';
        if (teamToggleRow) rolesSection.appendChild(teamToggleRow);
        if (roleCards) rolesSection.appendChild(roleCards);
        const providerSection = document.createElement('div');
        providerSection.className = 'llmSetupSection';
        providerSection.setAttribute('aria-label', 'LLM Setup');
        providerSection.innerHTML = '<h4>LLM Setup</h4><p>Provider, Modell, Test und technische LLM-Regeln.</p>';
        if (providerSelectRow) providerSection.appendChild(providerSelectRow);
        const keepRows = new Set([teamToggleRow, providerSelectRow, roleCards, rolesSection, providerSection].filter(Boolean));
        Array.from(grid.children).forEach((child) => {
          if (!keepRows.has(child)) providerSection.appendChild(child);
        });
        grid.appendChild(rolesSection);
        grid.appendChild(providerSection);
      }
    }
    const saveButton = document.getElementById('saveAgentSettings');
    if (saveButton && (!saveButton.dataset.state || saveButton.dataset.state === 'idle')) {
      saveButton.textContent = 'Setup speichern';
    }
  }

  function installStyles() {
    const oldStyle = document.getElementById('agent-setup-final-order-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'agent-setup-final-order-style';
    style.textContent = `
      #agentSetupView { position:relative !important; z-index:80 !important; isolation:isolate !important; background:var(--bg) !important; }
      #agentSetupView.hidden { display:none !important; }
      #agentSetupView > .card { position:relative !important; z-index:90 !important; width:100% !important; max-width:none !important; overflow:visible !important; box-shadow:0 14px 34px rgba(0,0,0,.24) !important; }
      #agentSetupView .configModalBody { display:grid !important; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)) !important; gap:6px !important; align-items:start !important; overflow:visible !important; }
      #agentSetupView .settingsGroup:not([data-agent-section]), #agentSetupView .agentSetupFinalGroup { grid-column:1 / -1 !important; }
      #agentSetupView .settingsTabsBar { display:none !important; }
      #agentSetupView .agentSetupFinalGroup[hidden] { display:none !important; }
      #agentSetupView .settingsGroup[data-agent-section],
      #agentSetupView .agentSetupFinalGroup { position:relative !important; display:block !important; padding:0 !important; margin:0 !important; border:1px solid var(--line) !important; border-radius:7px !important; background:rgba(15,23,42,.18) !important; overflow:hidden !important; box-shadow:none !important; }
      #agentSetupView .settingsGroup[data-agent-section] { padding:9px 14px !important; border-left-width:4px !important; }
      #agentSetupView .agentSetupFinalGroup::before { display:none !important; }
      #agentSetupView .agentSetupFinalGroup.brain > .agentSetupFinalGroupHeader { background:linear-gradient(90deg, rgba(245,158,11,.04), rgba(15,23,42,.12) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.llm > .agentSetupFinalGroupHeader { background:linear-gradient(90deg, rgba(34,211,238,.035), rgba(15,23,42,.12) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.structure > .agentSetupFinalGroupHeader { background:linear-gradient(90deg, rgba(20,184,166,.035), rgba(15,23,42,.12) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.chart > .agentSetupFinalGroupHeader { background:linear-gradient(90deg, rgba(34,211,238,.035), rgba(15,23,42,.12) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.status > .agentSetupFinalGroupHeader { background:linear-gradient(90deg, rgba(167,139,250,.04), rgba(15,23,42,.12) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.inactive { background:rgba(15,23,42,.12) !important; }
      #agentSetupView .agentSetupFinalGroup.inactive::before { background:#64748b !important; }
      #agentSetupView .agentSetupFinalGroupHeader { position:relative !important; z-index:2 !important; display:flex !important; align-items:center !important; justify-content:space-between !important; min-height:48px !important; margin:0 !important; padding:9px 14px 9px 14px !important; gap:12px !important; border-bottom:0 !important; border-left:4px solid #64748b !important; border-radius:7px 7px 0 0 !important; cursor:pointer !important; user-select:none !important; }
      #agentSetupView .agentSetupFinalGroup.agentSetupFinalGroupCollapsed .agentSetupFinalGroupHeader { border-radius:7px !important; }
      #agentSetupView .agentSetupFinalGroup.structure > .agentSetupFinalGroupHeader { border-left-color:rgba(20,184,166,.50) !important; }
      #agentSetupView .agentSetupFinalGroup.chart > .agentSetupFinalGroupHeader { border-left-color:rgba(34,211,238,.52) !important; }
      #agentSetupView .agentSetupFinalGroup.status > .agentSetupFinalGroupHeader { border-left-color:rgba(167,139,250,.54) !important; }
      #agentSetupView .agentSetupFinalGroup.brain > .agentSetupFinalGroupHeader { border-left-color:rgba(245,158,11,.54) !important; }
      #agentSetupView .agentSetupFinalGroup.llm > .agentSetupFinalGroupHeader { border-left-color:rgba(34,211,238,.52) !important; }
      #agentSetupView .agentSetupFinalGroup.agentSetupFinalGroupCollapsed.structure > .agentSetupFinalGroupHeader { border-left-color:#14b8a6 !important; background:linear-gradient(90deg, rgba(20,184,166,.10), rgba(15,23,42,.18) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.agentSetupFinalGroupCollapsed.chart > .agentSetupFinalGroupHeader { border-left-color:#22d3ee !important; background:linear-gradient(90deg, rgba(34,211,238,.10), rgba(15,23,42,.18) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.agentSetupFinalGroupCollapsed.status > .agentSetupFinalGroupHeader { border-left-color:#a78bfa !important; background:linear-gradient(90deg, rgba(167,139,250,.10), rgba(15,23,42,.18) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.agentSetupFinalGroupCollapsed.brain > .agentSetupFinalGroupHeader { border-left-color:#f59e0b !important; background:linear-gradient(90deg, rgba(245,158,11,.11), rgba(15,23,42,.18) 42%) !important; }
      #agentSetupView .agentSetupFinalGroup.agentSetupFinalGroupCollapsed.llm > .agentSetupFinalGroupHeader { border-left-color:#22d3ee !important; background:linear-gradient(90deg, rgba(34,211,238,.10), rgba(15,23,42,.18) 42%) !important; }
      #agentSetupView .agentSetupFinalGroupHeader strong { display:block !important; color:var(--ink) !important; font-size:13px !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #agentSetupView .agentSetupFinalGroupHeader span { display:block !important; margin-top:3px !important; color:var(--muted) !important; font-size:11px !important; line-height:1.3 !important; }
      #agentSetupView .agentSetupFinalMeta { display:inline-flex !important; align-items:center !important; width:max-content !important; min-height:18px !important; margin-top:5px !important; padding:1px 7px !important; border:1px solid rgba(148,163,184,.22) !important; border-radius:4px !important; background:rgba(15,23,42,.18) !important; color:#cbd5e1 !important; font-size:9.5px !important; font-style:normal !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #agentSetupView .agentSetupFinalGroupToggle,
      #agentSetupView .settingsGroup[data-agent-section] .agentGroupToggle { min-height:28px !important; padding:4px 9px !important; border:1px solid var(--line) !important; border-radius:4px !important; background:var(--panel-soft) !important; color:var(--muted) !important; font-size:11px !important; font-weight:900 !important; cursor:pointer !important; }
      #agentSetupView .agentSetupFinalGroupToggle { display:none !important; }
      #agentSetupView .agentSetupFinalGroupCollapsed .agentSetupFinalGroupToggle,
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed .agentGroupToggle { color:#93c5fd !important; }
      #agentSetupView .agentSetupFinalGroupToggle:hover { border-color:var(--accent) !important; color:#f8fafc !important; }
      #agentSetupView .agentDecisionPipeline { display:flex !important; align-items:center !important; flex-wrap:wrap !important; gap:6px !important; margin:10px 12px 10px !important; padding:7px 9px !important; border:1px solid rgba(245,158,11,.22) !important; border-radius:5px !important; background:rgba(245,158,11,.08) !important; color:#cbd5e1 !important; font-size:11px !important; line-height:1.2 !important; }
      #agentSetupView .agentDecisionPipeline span { display:inline-flex !important; align-items:center !important; min-height:22px !important; padding:3px 7px !important; border:1px solid rgba(148,163,184,.18) !important; border-radius:5px !important; background:rgba(15,23,42,.22) !important; color:#e2e8f0 !important; font-weight:800 !important; white-space:nowrap !important; }
      #agentSetupView .agentDecisionPipeline b { color:#fbbf24 !important; font-weight:900 !important; }
      #agentSetupView .plannerGroup, #agentSetupView .llmTeamGroup { position:relative !important; }
      #agentSetupView .plannerGroup { border-left-color:#f59e0b !important; background:rgba(15,23,42,.18) !important; }
      #agentSetupView .llmTeamGroup { border-left-color:#22d3ee !important; background:rgba(15,23,42,.18) !important; margin-top:0 !important; }
      #agentSetupView .plannerGroup::before, #agentSetupView .llmTeamGroup::before { content:attr(data-flow-label) !important; display:inline-flex !important; margin:5px 0 0 !important; min-height:18px !important; align-items:center !important; padding:2px 7px !important; border:1px solid rgba(148,163,184,.22) !important; border-radius:4px !important; color:#cbd5e1 !important; background:rgba(15,23,42,.30) !important; font-size:9.5px !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #agentSetupView .plannerGroup > h3, #agentSetupView .llmTeamGroup > h3 { margin:0 0 3px !important; padding:0 !important; border-bottom:0 !important; color:var(--ink) !important; font-size:13px !important; line-height:1.25 !important; font-weight:900 !important; letter-spacing:.045em !important; text-transform:uppercase !important; }
      #agentSetupView .plannerGroup > .muted, #agentSetupView .llmTeamGroup > .muted { margin:0 !important; color:var(--muted) !important; font-size:11px !important; line-height:1.25 !important; }
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed {
        min-height:48px !important;
        border-radius:7px !important;
        padding:9px 14px !important;
      }
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed > .settingsGroupGrid,
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed > .agentDecisionPipeline,
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed > .llmRoleCards,
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed > .providerPanel,
      #agentSetupView .settingsGroup[data-agent-section].agent-group-collapsed > .fullWidth:not(.muted) {
        display:none !important;
      }
      #agentSetupView .plannerGroup .rolePrompt { border:1px solid rgba(245,158,11,.18) !important; border-radius:6px !important; background:rgba(245,158,11,.06) !important; padding:8px 10px !important; }
      #agentSetupView .agentSetupFinalGroup[data-agent-tab-empty="true"] { display:block !important; }
      #agentSetupView .agentSetupFinalGroupCollapsed .agentSetupFinalCards { display:none !important; }
      #agentSetupView .agentSetupFinalGroupCollapsed .agentSetupFinalEmpty { display:none !important; }
      #agentSetupView .agentSetupFinalGroupCollapsed > .agentDecisionPipeline { display:none !important; }
      #agentSetupView .agentSetupFinalGroupCollapsed .agentSetupFinalGroupHeader { min-height:48px !important; margin-bottom:0 !important; padding:9px 14px !important; border-bottom:0 !important; }
      #agentSetupView .agentSetupFinalEmpty { min-height:38px !important; display:flex !important; align-items:center !important; padding:9px 10px !important; border:1px dashed rgba(148,163,184,.28) !important; border-radius:7px !important; color:var(--muted) !important; font-size:12px !important; }
      #agentSetupView .agentSetupFinalEmpty[hidden] { display:none !important; }
      #agentSetupView .agentSetupFinalCards { display:grid !important; grid-template-columns:repeat(2, minmax(0, 1fr)) !important; gap:8px !important; align-items:start !important; overflow:visible !important; padding:10px 12px 12px !important; border-top:1px solid rgba(148,163,184,.16) !important; background:rgba(15,23,42,.10) !important; }
      #agentSetupView .agentSetupFinalCards > .settingsGroup, #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup, #agentSetupView .agentSetupFinalCards > .agentDirectGroup, #agentSetupView .agentSetupFinalCards > .agentUtilityGroup { min-height:0 !important; height:auto !important; max-height:none !important; display:block !important; overflow:visible !important; margin:0 !important; padding:6px 8px !important; border-radius:5px !important; border-left-width:3px !important; }
      #agentSetupView .agentSetupFinalCards > .settingsGroup:not(.agent-active), #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup:not(.agent-active), #agentSetupView .agentSetupFinalCards > .agentDirectGroup:not(.agent-active) { opacity:1 !important; }
      #agentSetupView .agentSetupFinalCards > .settingsGroup:not(.agent-active):hover, #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup:not(.agent-active):hover, #agentSetupView .agentSetupFinalCards > .agentDirectGroup:not(.agent-active):hover, #agentSetupView .agentSetupFinalCards > .settingsGroup:focus-within, #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup:focus-within, #agentSetupView .agentSetupFinalCards > .agentDirectGroup:focus-within { opacity:1 !important; }
      #agentSetupView .agentSetupFinalCards > .settingsGroup > h3, #agentSetupView .agentSetupFinalCards > .agentIndicatorGroup > h3, #agentSetupView .agentSetupFinalCards > .agentDirectGroup > h3, #agentSetupView .agentSetupFinalCards > .agentUtilityGroup > h3 { display:none !important; }
      #agentSetupView .agentSetupFinalCards .settingsGroupGrid {
        display:grid !important;
        grid-template-columns:repeat(auto-fill, minmax(140px, 148px)) !important;
        gap:9px 10px !important;
        align-items:end !important;
        justify-content:start !important;
        overflow:visible !important;
      }
      #agentSetupView .agentSetupFinalCards .settingsGroupGrid > div {
        min-width:0 !important;
        max-width:100% !important;
      }
      #agentSetupView .agentSetupFinalCards .label,
      #agentSetupView .agentSetupFinalCards label {
        gap:5px !important;
        font-size:11.5px !important;
        line-height:1.2 !important;
        min-width:0 !important;
      }
      #agentSetupView .agentSetupFinalCards input,
      #agentSetupView .agentSetupFinalCards select {
        width:100% !important;
        max-width:100% !important;
        min-height:29px !important;
        padding:5px 7px !important;
        font-size:12px !important;
        box-sizing:border-box !important;
      }
      #agentSetupView .agentSetupFinalCards .agentIndicatorGroup > .settingsGroupGrid > .colorField {
        grid-column:1 / -1 !important;
        width:96px !important;
        max-width:96px !important;
      }
      #agentSetupView .agentSetupFinalCards input[type="color"] {
        width:82px !important;
        min-width:82px !important;
        max-width:82px !important;
        height:28px !important;
        min-height:28px !important;
        padding:4px !important;
        justify-self:start !important;
      }
      #agentSetupView .agentSetupFinalCards .label.fullWidth,
      #agentSetupView .agentSetupFinalCards .fullWidth {
        grid-column:1 / -1 !important;
      }
      #agentSetupView .agentSetupFinalCards .agentCardColorLine, #agentSetupView .agentSetupFinalCards .agentSetupFinalBadge, #agentSetupView .agentSetupFinalCards .agentColorRow, #agentSetupView .agentSetupFinalCards .agentCollapsedHint { display:none !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader { display:grid !important; grid-column:1 / -1 !important; grid-template-columns:minmax(0, 1fr) 34px !important; align-items:center !important; gap:8px !important; min-height:36px !important; }
      #agentSetupView .agentSetupFinalCards .agentGroupToggle { display:none !important; }
      #agentSetupView .agentSetupFinalCards .agentGroupHeader { grid-template-columns:minmax(0, 1fr) !important; }
      #agentSetupView .agentSetupFinalCards .agentControlMain { min-width:0 !important; }
      #agentSetupView .agentSetupFinalCards .plannerGroup,
      #agentSetupView .agentSetupFinalCards .llmTeamGroup,
      #agentSetupView .agentSetupFinalCards > .agentUtilityGroup { grid-column:1 / -1 !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .switchLine { min-height:30px !important; display:grid !important; grid-template-columns:46px minmax(0, 1fr) !important; gap:12px !important; align-items:center !important; padding:0 !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .switchInput { justify-self:start !important; width:46px !important; min-width:46px !important; max-width:46px !important; height:24px !important; min-height:24px !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .switchInput::after { top:2px !important; left:2px !important; width:18px !important; height:18px !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .switchInput:checked::after { left:24px !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .fieldLabel { min-width:0 !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; padding-left:0 !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .switchState { min-width:62px !important; justify-content:center !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .agentSetupToggle { width:34px !important; height:34px !important; min-width:34px !important; min-height:34px !important; padding:0 !important; display:grid !important; place-items:center !important; border-radius:5px !important; }
      #agentSetupView .agentSetupFinalCards .agentControlHeader .helpText { grid-column:1 / -1 !important; margin-top:4px !important; }
      #agentSetupView .agentSetupFinalCards .agentSetupPanel { grid-column:1 / -1 !important; padding:12px !important; gap:10px !important; border-radius:6px !important; border-left-width:3px !important; width:min(640px, calc(100vw - 42px)) !important; max-height:78vh !important; }
      #agentSetupView .agentSetupFinalCards .agentSetupPanel.open { grid-template-columns:repeat(2, minmax(0, 1fr)) !important; }
      #agentSetupView .agentSetupPopupHeader { padding-bottom:8px !important; gap:10px !important; }
      #agentSetupView .agentSetupPopupHeader strong { font-size:12px !important; line-height:1.2 !important; letter-spacing:.04em !important; text-transform:uppercase !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      #agentSetupView .agentSetupClose { min-height:30px !important; padding:6px 10px !important; border-radius:5px !important; font-size:12px !important; }
      #agentSetupView .agentSetupPanel .fieldLabel { font-size:11.5px !important; line-height:1.2 !important; }
      #agentSetupView .agentSetupPanel input, #agentSetupView .agentSetupPanel select { min-height:32px !important; padding:6px 8px !important; font-size:12px !important; border-radius:5px !important; }
      #agentSetupView .agentSetupPanel .helpText { padding:7px 8px !important; border-radius:5px !important; font-size:11px !important; line-height:1.35 !important; }
      #agentSetupView .agentSetupPanel .switchLine { min-height:32px !important; }
      #agentSetupView .agentSetupPanel .switchState { min-width:48px !important; justify-content:center !important; }
      #agentSetupView .llmTeamGroup .settingsGroupGrid { display:grid !important; grid-template-columns:1fr !important; gap:10px !important; width:100% !important; max-width:none !important; }
      #agentSetupView .llmTeamGroup .llmRolesSection,
      #agentSetupView .llmTeamGroup .llmSetupSection { grid-column:1 / -1 !important; display:grid !important; width:100% !important; max-width:none !important; gap:10px !important; padding:10px !important; border:1px solid rgba(148,163,184,.20) !important; border-radius:6px !important; background:rgba(15,23,42,.16) !important; box-sizing:border-box !important; }
      #agentSetupView .llmTeamGroup .llmRolesSection { border-left:3px solid rgba(34,211,238,.58) !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection { border-left:3px solid rgba(245,158,11,.58) !important; grid-template-columns:repeat(3, minmax(220px, 1fr)) !important; align-items:stretch !important; }
      #agentSetupView .llmTeamGroup .llmRolesSection > h4,
      #agentSetupView .llmTeamGroup .llmSetupSection > h4 { grid-column:1 / -1 !important; margin:0 !important; color:#e2e8f0 !important; font-size:12px !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #agentSetupView .llmTeamGroup .llmRolesSection > p,
      #agentSetupView .llmTeamGroup .llmSetupSection > p { grid-column:1 / -1 !important; margin:-6px 0 0 !important; color:var(--muted) !important; font-size:11px !important; line-height:1.3 !important; }
      #agentSetupView .llmRoleCards { grid-column:1 / -1 !important; display:grid !important; width:100% !important; max-width:none !important; grid-template-columns:repeat(2, minmax(0, 1fr)) !important; gap:10px !important; align-items:stretch !important; justify-self:stretch !important; }
      #agentSetupView .llmTeamGroup .llmRolesSection > div:not(.llmRoleCards),
      #agentSetupView .llmTeamGroup .llmSetupSection > div { min-width:0 !important; max-width:none !important; padding:8px 10px !important; border:1px solid rgba(148,163,184,.18) !important; border-radius:5px !important; background:rgba(2,6,23,.12) !important; box-sizing:border-box !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection > div:has(#cfgLlmProvider) { grid-column:1 / 2 !important; }
      #agentSetupView .llmTeamGroup .providerPanel.providerHidden { display:none !important; }
      #agentSetupView .llmTeamGroup .providerPanel { min-width:0 !important; }
      #agentSetupView .llmTeamGroup .settingsGroupGrid input, #agentSetupView .llmTeamGroup .settingsGroupGrid select { width:100% !important; max-width:none !important; min-width:0 !important; min-height:34px !important; }
      #agentSetupView .llmTeamGroup .settingsGroupGrid button:not(.helpButton) { width:100% !important; min-height:34px !important; }
      #agentSetupView .llmTeamGroup .switchLine { min-width:0 !important; min-height:30px !important; display:flex !important; gap:10px !important; align-items:center !important; }
      #agentSetupView .llmTeamGroup .switchLine .switchInput { flex:0 0 auto !important; width:46px !important; min-width:46px !important; max-width:46px !important; height:24px !important; min-height:24px !important; }
      #agentSetupView .llmTeamGroup .switchLine .switchInput::after { top:2px !important; left:2px !important; width:18px !important; height:18px !important; }
      #agentSetupView .llmTeamGroup .switchLine .switchInput:checked::after { left:24px !important; }
      #agentSetupView .llmTeamGroup .switchLine .fieldLabel { flex:1 1 auto !important; min-width:0 !important; white-space:normal !important; overflow:visible !important; }
      #agentSetupView .llmTeamGroup .switchState { margin-left:auto !important; flex:0 0 auto !important; min-width:62px !important; justify-content:center !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection .switchState,
      #agentSetupView .llmTeamGroup .llmRolesSection > div:not(.llmRoleCards) .switchState { display:none !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection > div:has(.switchInput:checked),
      #agentSetupView .llmTeamGroup .llmRolesSection > div:not(.llmRoleCards):has(.switchInput:checked) { border-left-color:#34d399 !important; background:linear-gradient(270deg, rgba(6,78,59,.13) 0%, rgba(6,78,59,.055) 26%, rgba(15,23,42,.19) 58%, rgba(15,23,42,.18) 100%) !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection > div:has(.switchInput:not(:checked)),
      #agentSetupView .llmTeamGroup .llmRolesSection > div:not(.llmRoleCards):has(.switchInput:not(:checked)) { border-left-color:#f87171 !important; background:linear-gradient(270deg, rgba(127,29,29,.09) 0%, rgba(127,29,29,.04) 26%, rgba(15,23,42,.185) 58%, rgba(15,23,42,.17) 100%) !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection > div:has(.switchInput:checked) .fieldLabel,
      #agentSetupView .llmTeamGroup .llmRolesSection > div:not(.llmRoleCards):has(.switchInput:checked) .fieldLabel { color:#34d399 !important; font-size:12.5px !important; font-weight:850 !important; }
      #agentSetupView .llmTeamGroup .llmSetupSection > div:has(.switchInput:not(:checked)) .fieldLabel,
      #agentSetupView .llmTeamGroup .llmRolesSection > div:not(.llmRoleCards):has(.switchInput:not(:checked)) .fieldLabel { color:#f87171 !important; font-size:12.5px !important; font-weight:850 !important; }
      #agentSetupView .settingsGroupGrid > div:has(> .switchLine .switchInput) > .switchLine .switchState,
      #agentSetupView .agentControlHeader:has(.switchInput) .switchState { display:none !important; }
      #agentSetupView .settingsGroupGrid > div:has(> .switchLine .switchInput:checked),
      #agentSetupView .agentControlHeader:has(.switchInput:checked) { border-left-color:#34d399 !important; background:linear-gradient(270deg, rgba(6,78,59,.12) 0%, rgba(6,78,59,.05) 26%, rgba(15,23,42,.19) 58%, rgba(15,23,42,.18) 100%) !important; }
      #agentSetupView .settingsGroupGrid > div:has(> .switchLine .switchInput:not(:checked)),
      #agentSetupView .agentControlHeader:has(.switchInput:not(:checked)) { border-left-color:#f87171 !important; background:linear-gradient(270deg, rgba(127,29,29,.085) 0%, rgba(127,29,29,.035) 26%, rgba(15,23,42,.185) 58%, rgba(15,23,42,.17) 100%) !important; }
      #agentSetupView .settingsGroupGrid > div:has(> .switchLine .switchInput:checked) > .switchLine .fieldLabel,
      #agentSetupView .agentControlHeader:has(.switchInput:checked) .fieldLabel { color:#34d399 !important; font-size:12.5px !important; font-weight:850 !important; }
      #agentSetupView .settingsGroupGrid > div:has(> .switchLine .switchInput:not(:checked)) > .switchLine .fieldLabel,
      #agentSetupView .agentControlHeader:has(.switchInput:not(:checked)) .fieldLabel { color:#f87171 !important; font-size:12.5px !important; font-weight:850 !important; }
      #agentSetupView .llmTeamGroup .apiTestRow { display:grid !important; grid-template-columns:minmax(150px, 230px) minmax(0, 1fr) !important; gap:10px !important; align-items:center !important; }
      #agentSetupView .llmTeamGroup .apiTestRow button { width:100% !important; }
      #agentSetupView .llmRoleCard { min-height:92px !important; padding:9px 10px !important; border:1px solid var(--line) !important; border-left:3px solid var(--accent) !important; border-radius:6px !important; background:var(--panel-soft) !important; display:grid !important; grid-template-columns:minmax(0, 1fr) auto !important; gap:8px 10px !important; align-items:start !important; }
      #agentSetupView .llmRoleCardHead { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:8px !important; min-width:0 !important; }
      #agentSetupView .llmRoleCard h4 { margin:0 !important; color:var(--ink) !important; font-size:13px !important; line-height:1.2 !important; letter-spacing:.03em !important; text-transform:uppercase !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      #agentSetupView .llmRoleCard:not(.judge) .llmRoleCardHead .switchState { display:none !important; }
      #agentSetupView .llmRoleCard:has(.llmRoleCardHead .switchState.active) h4 { color:#34d399 !important; }
      #agentSetupView .llmRoleCard:not(:has(.llmRoleCardHead .switchState.active)):not(.judge) h4 { color:#f87171 !important; }
      #agentSetupView .llmRoleCard .rolePrompt { grid-column:1 / 2 !important; color:var(--muted) !important; font-size:12px !important; line-height:1.3 !important; min-width:0 !important; }
      #agentSetupView .llmRoleCard > .switchLine { grid-column:2 / 3 !important; grid-row:1 / 3 !important; align-self:center !important; min-width:150px !important; justify-self:end !important; }
      #agentSetupView .rolePromptDetails { grid-column:1 / -1 !important; border-top:1px solid rgba(148,163,184,.14) !important; padding-top:5px !important; }
      #agentSetupView .rolePromptDetails summary { width:max-content !important; cursor:pointer !important; color:#93c5fd !important; font-size:11px !important; font-weight:800 !important; }
      #agentSetupView .rolePromptDetails[open] summary { margin-bottom:6px !important; }
      #agentSetupView .rolePromptEditor { width:100% !important; min-height:72px !important; resize:vertical !important; border:1px solid var(--line) !important; border-radius:6px !important; background:var(--panel) !important; color:var(--ink) !important; padding:8px 9px !important; font:12px/1.35 Arial, sans-serif !important; }
      #agentSetupView .providerPanel.providerHidden { display:none !important; }
      #agentSetupView .llmRoleCard.judge { border-left-color:#f59e0b !important; }
      #agentSetupView .llmRoleCard.judge h4 { color:#fbbf24 !important; }
      #agentSetupView [data-agent-display-group="structure"],
      #agentSetupView [data-agent-display-group="chart"],
      #agentSetupView [data-agent-display-group="status"],
      #agentSetupView [data-agent-display-group="brain"],
      #agentSetupView [data-agent-display-group="llm"],
      #agentSetupView [data-agent-display-group="inactive"] { border-left:0 !important; opacity:1 !important; }
      #agentSetupView .agentSetupFinalBadge { display:inline-flex !important; align-items:center !important; width:max-content !important; min-height:18px !important; padding:1px 6px !important; border:1px solid var(--line) !important; border-radius:4px !important; background:var(--panel-soft) !important; color:var(--muted) !important; font-size:9.5px !important; font-weight:900 !important; letter-spacing:.03em !important; text-transform:uppercase !important; }
      @media (max-width:1100px) { #agentSetupView .llmRoleCards { grid-template-columns:1fr !important; } #agentSetupView .llmTeamGroup .llmSetupSection { grid-template-columns:repeat(2, minmax(220px, 1fr)) !important; } #agentSetupView .llmRoleCard { grid-template-columns:minmax(0, 1fr) auto !important; } }
      @media (max-width:820px) { #agentSetupView .llmTeamGroup .llmSetupSection { grid-template-columns:repeat(2, minmax(0, 1fr)) !important; } }
      @media (max-width:620px) { #agentSetupView .llmTeamGroup .llmSetupSection { grid-template-columns:1fr !important; } }
      @media (max-width:700px) { #agentSetupView .llmRoleCard { grid-template-columns:1fr !important; } #agentSetupView .llmRoleCard > .switchLine { grid-column:1 / -1 !important; grid-row:auto !important; justify-self:start !important; } }
      #agentSetupView [data-agent-display-group="structure"] .agentSetupFinalBadge { color:#5eead4 !important; border-color:#0f766e !important; background:rgba(15,118,110,.14) !important; }
      #agentSetupView [data-agent-display-group="chart"] .agentSetupFinalBadge { color:#67e8f9 !important; border-color:#0891b2 !important; background:rgba(8,145,178,.14) !important; }
      #agentSetupView [data-agent-display-group="status"] .agentSetupFinalBadge { color:#ddd6fe !important; border-color:#7c3aed !important; background:rgba(124,58,237,.14) !important; }
      #agentSetupView [data-agent-display-group="brain"] .agentSetupFinalBadge { color:#fde68a !important; border-color:#d97706 !important; background:rgba(217,119,6,.14) !important; }
      #agentSetupView [data-agent-display-group="llm"] .agentSetupFinalBadge { color:#67e8f9 !important; border-color:#0891b2 !important; background:rgba(8,145,178,.14) !important; }
      #agentSetupView [data-agent-display-group="inactive"] .agentSetupFinalBadge { color:#cbd5e1 !important; border-color:#475569 !important; background:rgba(71,85,105,.18) !important; }
      #agentSetupView .modalActions { position:sticky !important; bottom:0 !important; z-index:3200 !important; isolation:isolate !important; display:flex !important; justify-content:flex-end !important; padding:10px 12px !important; margin:8px -10px -10px !important; background:linear-gradient(180deg, rgba(17,24,39,.88), rgba(17,24,39,.99)) !important; border-top:1px solid var(--line) !important; box-shadow:0 -14px 34px rgba(0,0,0,.34) !important; }
      #agentSetupView .agentSaveFeedback { flex:1 1 auto !important; min-height:36px !important; display:flex !important; align-items:center !important; padding:8px 12px !important; border:1px solid rgba(148,163,184,.18) !important; border-radius:6px !important; background:rgba(15,23,42,.72) !important; color:#9fb0c8 !important; font-weight:800 !important; letter-spacing:0 !important; }
      #agentSetupView .agentSaveFeedback[data-state="dirty"] { color:#fbbf24 !important; border-color:rgba(251,191,36,.42) !important; background:rgba(251,191,36,.08) !important; }
      #agentSetupView .agentSaveFeedback[data-state="saving"] { color:#67e8f9 !important; border-color:rgba(34,211,238,.50) !important; background:linear-gradient(90deg, rgba(34,211,238,.16), rgba(15,23,42,.72)) !important; }
      #agentSetupView .agentSaveFeedback[data-state="saved"] { color:#34d399 !important; border-color:rgba(52,211,153,.55) !important; background:linear-gradient(90deg, rgba(16,185,129,.18), rgba(15,23,42,.72)) !important; }
      #agentSetupView .agentSaveFeedback[data-state="error"] { color:#fca5a5 !important; border-color:rgba(248,113,113,.58) !important; background:linear-gradient(90deg, rgba(248,113,113,.16), rgba(15,23,42,.72)) !important; }
      #agentSetupView #saveAgentSettings { position:relative !important; z-index:3201 !important; flex:0 0 170px !important; width:170px !important; min-width:150px !important; max-width:190px !important; min-height:36px !important; padding:8px 14px !important; border-radius:6px !important; box-shadow:0 12px 26px rgba(20,184,166,.18) !important; }
      #agentSetupView .agentSetupToggle { width:34px !important; min-width:34px !important; max-width:34px !important; height:34px !important; border-radius:6px !important; }
      #agentSetupView .settingsGroup.open, #agentSetupView .agentIndicatorGroup.open, #agentSetupView .agentDirectGroup.open, #agentSetupView .agentUtilityGroup.open, #agentSetupView .settingsGroup:focus-within, #agentSetupView .agentIndicatorGroup:focus-within, #agentSetupView .agentDirectGroup:focus-within, #agentSetupView .agentUtilityGroup:focus-within { height:auto !important; max-height:none !important; min-height:0 !important; z-index:120 !important; overflow:visible !important; }
      #agentSetupView .modalBackdrop, #agentSetupView .modal { z-index:2000 !important; }
      .modalBackdrop.open { z-index:2000 !important; }
      .modalBackdrop.open .modal, .modal.open { z-index:2010 !important; }
      @media (max-width:900px) { #agentSetupView .configModalBody { grid-template-columns:1fr !important; } #agentSetupView .agentSetupFinalCards .settingsGroupGrid { grid-template-columns:1fr auto !important; } #agentSetupView #saveAgentSettings { flex:0 0 170px !important; width:170px !important; max-width:190px !important; } }
      @media (max-width:760px) { #agentSetupView .agentSetupFinalCards { grid-template-columns:1fr !important; } }
      @media (max-width:900px) { #agentSetupView .llmTeamGroup .settingsGroupGrid { grid-template-columns:1fr !important; } }
      @media (max-width:760px) { #agentSetupView .agentSetupFinalCards .agentSetupPanel.open { grid-template-columns:1fr !important; } }
    `;
    document.head.appendChild(style);
  }

  function installHooks() {
    document.addEventListener('keydown', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const categoryHeader = target.closest('#agentSetupView .agentSetupFinalGroupHeader[data-agent-final-header-toggle]');
      if (!categoryHeader || (event.key !== 'Enter' && event.key !== ' ')) return;
      event.preventDefault();
      const shell = document.getElementById(categoryHeader.dataset.agentFinalHeaderToggle);
      if (shell) setShellCollapsed(shell, !shell.classList.contains('agentSetupFinalGroupCollapsed'));
    });
    document.addEventListener('click', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest('#agentSetupViewButton, #agentSetupButton, [data-view="agentSetup"], .settingsTabButton')) {
        scheduleFinalOrder(40);
        window.setTimeout(applyFinalOrder, 250);
        window.setTimeout(syncShellTabVisibility, 80);
        window.setTimeout(syncShellTabVisibility, 320);
      }
      const categoryHeader = target.closest('#agentSetupView .agentSetupFinalGroupHeader[data-agent-final-header-toggle]');
      if (categoryHeader && !target.closest('button, a, input, select, textarea, summary')) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const shell = document.getElementById(categoryHeader.dataset.agentFinalHeaderToggle);
        if (shell) setShellCollapsed(shell, !shell.classList.contains('agentSetupFinalGroupCollapsed'));
        return;
      }
      if (target.matches('#agentSetupView [data-agent-enabled]')) {
        window.setTimeout(updateAllShellMetrics, 20);
      }
      if (target.closest('#agentSetupView .settingsButton, #agentSetupView .agentSettingsButton, #agentSetupView button[aria-label*="Setting"], #agentSetupView button[title*="Setting"], #agentSetupView button[title*="Konfig"], #agentSetupView .settingsGroup button')) {
        const group = target.closest('.settingsGroup, .agentIndicatorGroup, .agentDirectGroup, .agentUtilityGroup');
        if (group) group.classList.add('open');
        window.setTimeout(() => { if (group) group.classList.add('open'); }, 120);
      }
    }, true);

    document.addEventListener('change', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.matches('#agentSetupView [data-agent-enabled]')) return;
      syncShellTabVisibility();
    }, true);

    document.addEventListener('agent-settings-rendered', () => {
      scheduleFinalOrder(20);
      window.setTimeout(applyFinalOrder, 120);
    });

    const view = setupView();
    if (view && !view.dataset.finalOrderObserver) {
      const observer = new MutationObserver(mutations => {
        if (Date.now() < suppressOrderObserverUntil) return;
        if (mutations.some(mutation => Array.from(mutation.addedNodes).some(node => node instanceof Element))) scheduleFinalOrder(60);
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
