// ==================================================
// dashboard_direct_agent_chart_view_fix_patch.js
// ==================================================
// DIRECT AGENT CHART VIEW FIX PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-direct-agent-chart-view-fix-v7-direct-status-chart';
  const CHART_VIEW_SECTIONS = ['hma', 'sma', 'triple_ema', 'macd', 'mfi', 'rsi', 'vwap', 'volume'];
  const CHART_STATUS_SECTIONS = ['breakout_fakeout', 'volatility_regime', 'risk'];
  const EVALUATION_ONLY_SECTIONS = [];
  let originalDrawChart = null;
  let originalClearKlineChart = null;
  let directVolumeRegistered = false;

  function runtimeConfig() {
    try {
      if (typeof latestConfig !== 'undefined' && latestConfig) return latestConfig;
    } catch (_) {}
    try {
      if (typeof latestStatusData !== 'undefined' && latestStatusData?.config) return latestStatusData.config;
    } catch (_) {}
    if (window.latestConfig) return window.latestConfig;
    if (window.latestStatusData?.config) return window.latestStatusData.config;
    return {};
  }

  function runtimeStatus() {
    try {
      if (typeof latestStatusData !== 'undefined' && latestStatusData) return latestStatusData;
    } catch (_) {}
    return window.latestStatusData || null;
  }

  function configValue(key, fallback = undefined) {
    const cfg = runtimeConfig();
    if (Object.prototype.hasOwnProperty.call(cfg, key)) return cfg[key];
    return fallback;
  }

  function boolConfig(key, fallback = false) {
    const value = configValue(key, fallback);
    if (typeof value === 'boolean') return value;
    const text = String(value ?? '').trim().toLowerCase();
    if (['1', 'true', 'yes', 'on', 'aktiv', 'active'].includes(text)) return true;
    if (['0', 'false', 'no', 'off', 'aus', 'inactive'].includes(text)) return false;
    return !!fallback;
  }

  function numberConfig(key, fallback) {
    const value = Number(configValue(key, fallback));
    return Number.isFinite(value) ? value : fallback;
  }

  function colorConfig(primaryKey, fallbackKey, fallback) {
    return String(configValue(primaryKey, configValue(fallbackKey, fallback)) || fallback);
  }

  function chartInstance() {
    if (window.__klineChartInstance) return window.__klineChartInstance;
    try {
      if (typeof window.initKlineChart === 'function') return window.initKlineChart();
    } catch (_) {}
    return null;
  }

  function apiInstance() {
    return window.klinecharts || window.KLineCharts || window.KLineChart || null;
  }

  function candleNumber(candle, key) {
    const number = Number(candle?.[key]);
    return Number.isFinite(number) ? number : 0;
  }

  function candleTime(candle) {
    const number = Number(candle?.timestamp ?? candle?.time ?? candle?.openTime);
    if (!Number.isFinite(number)) return null;
    return number > 1000000000000 ? Math.floor(number / 1000) : number;
  }

  function selectedChartSymbol() {
    const explicit = document.getElementById('chartAsset')?.value || document.getElementById('assetFilter')?.value;
    const cfg = runtimeConfig();
    const fallback = Array.isArray(cfg.symbols) && cfg.symbols.length ? cfg.symbols[0] : '';
    const value = explicit && explicit !== '__ALL__' ? explicit : fallback;
    return String(value || '').replace('.P', '').split(':', 1)[0].trim().toUpperCase();
  }

  function currentAgentBoard() {
    const status = runtimeStatus();
    const symbol = selectedChartSymbol();
    if (!status || !symbol) return null;
    return status?.cycle?.agents?.[symbol] || status?.cycle?.symbols?.[symbol]?.agents || null;
  }

  function agentReports() {
    const board = currentAgentBoard();
    const reports = Array.isArray(board?.reports) ? board.reports : [];
    const extended = reports.slice();
    if (board?.brain) extended.push({ ...board.brain, agent_name: 'Brain Agent' });
    if (board?.ceo) extended.push({ ...board.ceo, agent_name: 'CEO Agent' });
    return extended.filter(Boolean);
  }

  function findReport(...needles) {
    const wanted = needles.map(item => String(item || '').toLowerCase());
    return agentReports().find(report => {
      const name = String(report?.agent_name || '').toLowerCase();
      return wanted.every(needle => name.includes(needle));
    }) || null;
  }

  function textValue(value, fallback = '-') {
    if (value === null || value === undefined || value === '') return fallback;
    return String(value);
  }

  function scoreText(report) {
    const number = Number(report?.score);
    return Number.isFinite(number) ? String(Math.round(number)) : '-';
  }

  function signalClass(report) {
    const signal = String(report?.signal || 'NEUTRAL').toLowerCase();
    if (report?.blocking) return 'blocked';
    if (signal === 'long') return 'long';
    if (signal === 'short') return 'short';
    return 'neutral';
  }

  function registerDirectVolumeIndicator() {
    if (directVolumeRegistered) return;
    const api = apiInstance();
    if (!api || typeof api.registerIndicator !== 'function') return;
    try {
      api.registerIndicator({
        name: 'BOT_VOLUME_DIRECT',
        shortName: 'Volume',
        series: 'volume',
        precision: 0,
        calcParams: [],
        figures: [{ key: 'volume', title: 'VOLUME: ', type: 'bar' }],
        calc: dataList => dataList.map(k => ({ volume: Number(k.volume || 0) }))
      });
      directVolumeRegistered = true;
    } catch (_) {
      directVolumeRegistered = true;
    }
  }

  function createIndicatorSafe(storageKey, indicator, paneId, order, height) {
    const chart = chartInstance();
    if (!chart || typeof chart.createIndicator !== 'function') return;
    window.__botDirectAgentChartView = window.__botDirectAgentChartView || {};
    if (window.__botDirectAgentChartView[storageKey]) return;
    try {
      window.__botDirectAgentChartView[storageKey] = chart.createIndicator(indicator, false, {
        id: paneId,
        height,
        minHeight: 96,
        dragEnabled: true,
        order,
        state: 'normal',
        axis: { name: 'right', position: 'right', inside: false, scrollZoomEnabled: true, gap: { top: 0.12, bottom: 0.12 } }
      }) || 'attempted';
    } catch (_) {
      window.__botDirectAgentChartView[storageKey] = 'attempted';
    }
  }

  function createOverlaySafe(id, points, color, size = 1) {
    const chart = chartInstance();
    if (!chart || typeof chart.createOverlay !== 'function' || !points.length) return null;
    try {
      chart.createOverlay({
        name: 'segment',
        id,
        points,
        styles: { line: { color: color || '#14b8a6', size } }
      });
      return { type: 'overlay', id };
    } catch (_) {
      return null;
    }
  }

  function removeChartItem(value) {
    const chart = chartInstance();
    if (!chart || !value || value === 'attempted') return;
    if (typeof value === 'object' && value.type === 'overlay') {
      if (typeof chart.removeOverlay === 'function') {
        try { chart.removeOverlay({ id: value.id }); return; } catch (_) {}
        try { chart.removeOverlay(value.id); return; } catch (_) {}
      }
      return;
    }
    if (typeof chart.removeIndicator === 'function') {
      try { chart.removeIndicator(value); } catch (_) {}
    }
  }

  function removeNativeDirectAgentItems() {
    const nativeItems = window.__botNativeIndicators || {};
    ['rsi', 'volume', 'vwap'].forEach(key => {
      if (!nativeItems[key]) return;
      removeChartItem(nativeItems[key]);
      delete nativeItems[key];
    });
  }

  function clearDirectAgentChartView() {
    Object.values(window.__botDirectAgentChartView || {}).forEach(removeChartItem);
    window.__botDirectAgentChartView = {};
  }

  function vwapPoints(candles) {
    const typed = Array.isArray(candles) ? candles : [];
    const lookback = Math.max(1, Math.floor(numberConfig('agent_vwap_lookback_candles', numberConfig('indicator_vwap_lookback_candles', 96))));
    const points = [];
    for (let index = 0; index < typed.length; index += 1) {
      const start = Math.max(0, index - lookback + 1);
      let volumeSum = 0;
      let weightedSum = 0;
      for (let pos = start; pos <= index; pos += 1) {
        const candle = typed[pos];
        const volume = candleNumber(candle, 'volume');
        if (volume <= 0) continue;
        weightedSum += ((candleNumber(candle, 'high') + candleNumber(candle, 'low') + candleNumber(candle, 'close')) / 3) * volume;
        volumeSum += volume;
      }
      const timestamp = candleTime(typed[index]);
      if (timestamp !== null && volumeSum > 0) points.push({ timestamp, value: weightedSum / volumeSum });
    }
    return points;
  }

  function directPaneCount() {
    let count = 0;
    if (boolConfig('agent_rsi_enabled', false) || boolConfig('indicator_show_rsi', false)) count += 1;
    if (boolConfig('agent_volume_enabled', false) || boolConfig('indicator_show_volume', false)) count += 1;
    return count;
  }

  function nativePaneCount() {
    let count = 0;
    if (boolConfig('agent_macd_enabled', false) || boolConfig('indicator_show_macd', false)) count += 1;
    if (boolConfig('agent_mfi_enabled', false) || boolConfig('indicator_show_mfi', false)) count += 1;
    return count;
  }

  function applyChartHeight() {
    const chartEl = document.getElementById('klineChart');
    const wrap = chartEl?.closest('.chartCanvasWrap');
    if (!chartEl || !wrap) return;
    const paneCount = directPaneCount() + nativePaneCount();
    const height = Math.max(980, Math.min(1680, 760 + paneCount * 185));
    wrap.style.height = `${height}px`;
    wrap.style.minHeight = `${height}px`;
    wrap.style.maxHeight = 'none';
    wrap.style.overflow = 'visible';
    chartEl.style.height = `${height}px`;
    chartEl.style.minHeight = `${height}px`;
    chartEl.style.maxHeight = 'none';
    document.body.dataset.directAgentChartHeight = String(height);
    window.setTimeout(() => {
      try {
        if (typeof window.resizeKlineChart === 'function') window.resizeKlineChart();
      } catch (_) {}
      try {
        const chart = chartInstance();
        if (chart && typeof chart.resize === 'function') chart.resize();
      } catch (_) {}
    }, 80);
  }

  function drawBreakoutRange(candles, report) {
    const details = report?.details || {};
    const high = Number(details.range_high);
    const low = Number(details.range_low);
    const typed = Array.isArray(candles) ? candles : [];
    if (!Number.isFinite(high) || !Number.isFinite(low) || typed.length < 2) return;
    const start = candleTime(typed[Math.max(0, typed.length - 48)]);
    const end = candleTime(typed[typed.length - 1]);
    if (start === null || end === null) return;
    window.__botDirectAgentChartView.breakoutHigh = createOverlaySafe('bot_direct_breakout_high', [{ timestamp: start, value: high }, { timestamp: end, value: high }], '#f472b6', 1) || 'attempted';
    window.__botDirectAgentChartView.breakoutLow = createOverlaySafe('bot_direct_breakout_low', [{ timestamp: start, value: low }, { timestamp: end, value: low }], '#f472b6', 1) || 'attempted';
  }

  function directAgentTile(title, report, detail) {
    const cls = signalClass(report);
    const signal = textValue(report?.signal, 'NEUTRAL');
    return `
      <div class="directAgentChartTile ${cls}">
        <div class="directAgentChartTileHead"><strong>${title}</strong><span>${signal}</span></div>
        <div class="directAgentChartScore">Score ${scoreText(report)}</div>
        <div class="directAgentChartDetail">${detail || textValue(report?.message, 'wartet')}</div>
      </div>
    `;
  }

  function ensureDirectAgentStatusPanel(candles) {
    const chartView = document.getElementById('chartView');
    const chartCard = chartView?.querySelector('.card');
    if (!chartCard) return;

    let panel = document.getElementById('directAgentChartStatusPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'directAgentChartStatusPanel';
      panel.className = 'directAgentChartStatusPanel';
      const chartMeta = document.getElementById('chartMeta');
      if (chartMeta && chartMeta.parentNode === chartCard) chartCard.insertBefore(panel, chartMeta);
      else chartCard.appendChild(panel);
    }

    const breakout = findReport('breakout');
    const volatility = findReport('volatility');
    const risk = findReport('risk');
    const breakoutDetail = breakout?.details?.mode
      ? `${textValue(breakout.details.mode)} · High ${textValue(breakout.details.range_high)} · Low ${textValue(breakout.details.range_low)}`
      : textValue(breakout?.message, 'wartet');
    const volatilityDetail = volatility?.details?.regime
      ? `${textValue(volatility.details.regime)} · ATR ${textValue(volatility.details.atr)} · Ratio ${textValue(volatility.details.ratio)}x`
      : textValue(volatility?.message, 'wartet');
    const riskDetail = Array.isArray(risk?.details?.hard_blocks) && risk.details.hard_blocks.length
      ? `Block: ${risk.details.hard_blocks.join(' / ')}`
      : Array.isArray(risk?.details?.warnings) && risk.details.warnings.length
        ? `Warnung: ${risk.details.warnings.join(' / ')}`
        : textValue(risk?.message, 'wartet');

    panel.innerHTML = `
      <div class="directAgentChartStatusHead">
        <strong>Direkte Agenten im Chartfenster</strong>
        <span>Range / Regime / Risk-Status</span>
      </div>
      <div class="directAgentChartGrid">
        ${directAgentTile('Breakout / Fakeout', breakout, breakoutDetail)}
        ${directAgentTile('Volatility Regime', volatility, volatilityDetail)}
        ${directAgentTile('Risk Agent', risk, riskDetail)}
      </div>
    `;

    if (breakout) drawBreakoutRange(candles, breakout);
  }

  function ensureDirectAgentChartView(candles) {
    const chart = chartInstance();
    if (!chart) return;
    removeNativeDirectAgentItems();
    window.__botDirectAgentChartView = window.__botDirectAgentChartView || {};

    if (boolConfig('agent_rsi_enabled', false) || boolConfig('indicator_show_rsi', false)) {
      const period = Math.max(1, Math.floor(numberConfig('agent_rsi_period', numberConfig('indicator_rsi_period', 14))));
      createIndicatorSafe('rsi', { name: 'RSI', calcParams: [period] }, 'bot_direct_rsi_pane', 90, 130);
    }

    if (boolConfig('agent_volume_enabled', false) || boolConfig('indicator_show_volume', false)) {
      registerDirectVolumeIndicator();
      createIndicatorSafe('volume', { name: 'BOT_VOLUME_DIRECT', id: 'BOT_VOLUME_DIRECT_MAIN' }, 'bot_direct_volume_pane', 100, 130);
    }

    if (boolConfig('agent_vwap_enabled', false) || boolConfig('indicator_show_vwap', false)) {
      if (!window.__botDirectAgentChartView.vwap) {
        const color = colorConfig('indicator_vwap_color', 'agent_vwap_color', '#14b8a6');
        window.__botDirectAgentChartView.vwap = createOverlaySafe('bot_direct_vwap_line', vwapPoints(candles), color) || 'attempted';
      }
    }

    ensureDirectAgentStatusPanel(candles);
    applyChartHeight();

    const status = document.getElementById('chartPluginStatus');
    if (status) {
      const base = Object.keys(window.__botNativeIndicators || {}).filter(key => window.__botNativeIndicators[key]);
      const direct = Object.keys(window.__botDirectAgentChartView || {}).filter(key => window.__botDirectAgentChartView[key]);
      const active = Array.from(new Set(base.concat(direct)));
      status.textContent = `KLineCharts · Agent-Indikatoren ${active.length ? active.join(' / ') : 'bereit'}`;
    }
  }

  function setupBody() {
    const view = document.getElementById('agentSetupView');
    return view?.querySelector('.configModalBody') || null;
  }

  function sectionGroup(body, section) {
    return body?.querySelector(`[data-agent-section="${section}"]`) || null;
  }

  function insertAfter(reference, node) {
    if (!reference || !node || !reference.parentNode) return reference;
    reference.parentNode.insertBefore(node, reference.nextSibling);
    return node;
  }

  function sectionHeader(id, title, detail, mode) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const header = document.createElement('div');
    header.id = id;
    header.className = `agentSetupSectionHeader ${mode || ''}`.trim();
    header.innerHTML = `<div><strong>${title}</strong><span>${detail}</span></div>`;
    return header;
  }

  function directHeaderBlock(body) {
    return Array.from(body?.querySelectorAll('.settingsGroup') || []).find(block => {
      if (block.dataset.agentSection) return false;
      const title = String(block.querySelector(':scope > h3')?.textContent || '').trim();
      return /Direkte Agenten|Agenten ohne eigene Hauptchart-Linie|Nur Bewertungsagenten/i.test(title);
    }) || null;
  }

  function markGroup(group, mode, label) {
    if (!group) return;
    group.dataset.chartView = mode === 'chart' || mode === 'status' ? 'true' : 'false';
    group.dataset.agentDisplayGroup = mode;
    group.querySelectorAll('.agentChartModeBadge').forEach(badge => badge.remove());
    const grid = group.querySelector('.settingsGroupGrid');
    if (!grid) return;
    const badge = document.createElement('div');
    badge.className = 'agentChartModeBadge fullWidth';
    badge.textContent = label;
    grid.insertBefore(badge, grid.firstChild);
  }

  function layoutAgentSetupSections() {
    const body = setupBody();
    if (!body) return;

    const tabs = body.querySelector('.settingsTabsBar');
    if (tabs && tabs !== body.firstElementChild) body.insertBefore(tabs, body.firstElementChild);

    const chartGroups = CHART_VIEW_SECTIONS.map(section => sectionGroup(body, section)).filter(Boolean);
    const statusGroups = CHART_STATUS_SECTIONS.map(section => sectionGroup(body, section)).filter(Boolean);
    const evaluationGroups = EVALUATION_ONLY_SECTIONS.map(section => sectionGroup(body, section)).filter(Boolean);

    chartGroups.forEach(group => markGroup(group, 'chart', 'Chart View'));
    statusGroups.forEach(group => markGroup(group, 'status', 'Chart Status'));
    evaluationGroups.forEach(group => markGroup(group, 'evaluation', 'Nur Bewertung'));

    const oldHeader = directHeaderBlock(body);
    if (oldHeader) oldHeader.remove();

    const chartHeader = sectionHeader(
      'agentSetupChartViewAgentsHeader',
      'Chart View Agenten',
      'Agenten mit Linie, Pane oder Preis-Overlay im Chart.',
      'chart'
    );
    const statusHeader = sectionHeader(
      'agentSetupChartStatusAgentsHeader',
      'Chart Status Agenten',
      'Direkte Agenten als Status-Kacheln und Range-Anzeige im Chartfenster.',
      'status'
    );
    const evaluationHeader = sectionHeader(
      'agentSetupEvaluationAgentsHeader',
      'Nur Bewertungsagenten',
      'Bewertung, Risiko, Regime und Filter ohne eigene Chart-Anzeige.',
      'evaluation'
    );

    const reference = body.querySelector('.settingsGroup:not([data-agent-section])') || body.firstElementChild;
    body.insertBefore(chartHeader, reference?.nextSibling || body.firstChild);
    let cursor = chartHeader;
    chartGroups.forEach(group => { cursor = insertAfter(cursor, group); });
    if (statusGroups.length) {
      cursor = insertAfter(cursor, statusHeader);
      statusGroups.forEach(group => { cursor = insertAfter(cursor, group); });
    }
    if (evaluationGroups.length) {
      cursor = insertAfter(cursor, evaluationHeader);
      evaluationGroups.forEach(group => { cursor = insertAfter(cursor, group); });
    } else {
      evaluationHeader.remove();
    }

    document.body.dataset.agentSetupCleanOrder = PATCH_VERSION;
  }

  function injectLayoutStyles() {
    const oldStyle = document.getElementById('direct-agent-chart-view-layout-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'direct-agent-chart-view-layout-style';
    style.textContent = `
      main { max-width:none !important; width:100% !important; }
      #chartView, #agentSetupView { width:100% !important; max-width:none !important; }
      #chartView > .card, #agentSetupView > .card { width:100% !important; max-width:none !important; overflow:visible !important; }
      #chartView .chartCanvasWrap { width:100% !important; min-height:980px !important; height:980px; max-height:none !important; overflow:visible !important; }
      #chartView #klineChart { width:100% !important; min-height:980px !important; height:980px; max-height:none !important; }
      #chartView #chartMeta { clear:both !important; margin-top:14px !important; }
      #chartView .directAgentChartStatusPanel { margin:14px 0 10px !important; padding:12px !important; border:1px solid var(--line) !important; border-left:5px solid #a78bfa !important; border-radius:8px !important; background:rgba(15,23,42,.22) !important; }
      #chartView .directAgentChartStatusHead { display:flex !important; align-items:baseline !important; justify-content:space-between !important; gap:12px !important; margin-bottom:10px !important; }
      #chartView .directAgentChartStatusHead strong { color:var(--ink) !important; font-size:13px !important; font-weight:900 !important; letter-spacing:.07em !important; text-transform:uppercase !important; }
      #chartView .directAgentChartStatusHead span { color:var(--muted) !important; font-size:12px !important; }
      #chartView .directAgentChartGrid { display:grid !important; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)) !important; gap:10px !important; }
      #chartView .directAgentChartTile { min-height:96px !important; padding:11px 12px !important; border:1px solid var(--line) !important; border-radius:7px !important; background:var(--panel-soft) !important; box-shadow:inset 4px 0 0 #64748b !important; }
      #chartView .directAgentChartTile.long { box-shadow:inset 4px 0 0 #22c55e !important; }
      #chartView .directAgentChartTile.short { box-shadow:inset 4px 0 0 #ef4444 !important; }
      #chartView .directAgentChartTile.blocked { box-shadow:inset 4px 0 0 #f97316 !important; }
      #chartView .directAgentChartTileHead { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:10px !important; }
      #chartView .directAgentChartTileHead strong { color:var(--ink) !important; font-size:12px !important; font-weight:900 !important; letter-spacing:.05em !important; text-transform:uppercase !important; }
      #chartView .directAgentChartTileHead span { display:inline-flex !important; align-items:center !important; min-height:22px !important; padding:2px 7px !important; border-radius:999px !important; background:rgba(148,163,184,.18) !important; color:var(--muted) !important; font-size:11px !important; font-weight:900 !important; }
      #chartView .directAgentChartScore { margin-top:8px !important; color:var(--accent) !important; font-size:12px !important; font-weight:900 !important; }
      #chartView .directAgentChartDetail { margin-top:6px !important; color:var(--muted) !important; font-size:12px !important; line-height:1.35 !important; overflow-wrap:anywhere !important; }
      #agentSetupView .configModalBody { display:grid !important; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)) !important; gap:16px !important; align-items:start !important; grid-auto-flow:row dense !important; overflow:visible !important; padding:16px 14px 84px !important; }
      #agentSetupView .settingsTabsBar { grid-column:1 / -1 !important; width:100% !important; display:flex !important; flex-wrap:wrap !important; align-items:center !important; gap:8px !important; margin:0 0 10px !important; padding:0 0 14px !important; border-bottom:1px solid var(--line) !important; }
      #agentSetupView .settingsTabButton { min-width:128px !important; justify-content:center !important; }
      #agentSetupView .settingsGroup:not([data-agent-section]), #agentSetupView .agentSetupSectionHeader { grid-column:1 / -1 !important; }
      #agentSetupView .agentSetupSectionHeader { display:flex !important; align-items:center !important; justify-content:space-between !important; min-height:66px !important; padding:14px 16px !important; border:1px solid var(--line) !important; border-radius:8px !important; background:rgba(15,23,42,.24) !important; }
      #agentSetupView .agentSetupSectionHeader.chart { border-left:5px solid #22d3ee !important; }
      #agentSetupView .agentSetupSectionHeader.status { border-left:5px solid #a78bfa !important; }
      #agentSetupView .agentSetupSectionHeader.evaluation { border-left:5px solid #fb923c !important; }
      #agentSetupView .agentSetupSectionHeader strong { display:block !important; color:var(--ink) !important; font-size:15px !important; font-weight:900 !important; letter-spacing:.07em !important; text-transform:uppercase !important; }
      #agentSetupView .agentSetupSectionHeader span { display:block !important; margin-top:5px !important; color:var(--muted) !important; font-size:12px !important; letter-spacing:.02em !important; }
      #agentSetupView [data-agent-display-group="chart"] { border-left:4px solid #22d3ee !important; }
      #agentSetupView [data-agent-display-group="status"] { border-left:4px solid #a78bfa !important; }
      #agentSetupView [data-agent-display-group="evaluation"] { border-left:4px solid #fb923c !important; }
      #agentSetupView .agentChartModeBadge { display:inline-flex !important; align-items:center !important; min-height:24px !important; width:max-content !important; padding:3px 8px !important; border:1px solid var(--line) !important; border-radius:999px !important; background:var(--panel-soft) !important; color:var(--muted) !important; font-size:11px !important; font-weight:900 !important; letter-spacing:.04em !important; text-transform:uppercase !important; }
      #agentSetupView [data-agent-display-group="chart"] .agentChartModeBadge { color:#67e8f9 !important; border-color:#0891b2 !important; background:rgba(8,145,178,.14) !important; }
      #agentSetupView [data-agent-display-group="status"] .agentChartModeBadge { color:#ddd6fe !important; border-color:#7c3aed !important; background:rgba(124,58,237,.14) !important; }
      #agentSetupView [data-agent-display-group="evaluation"] .agentChartModeBadge { color:#fdba74 !important; border-color:#c2410c !important; background:rgba(194,65,12,.14) !important; }
      #agentSetupView .settingsGroup, #agentSetupView .agentIndicatorGroup, #agentSetupView .agentDirectGroup, #agentSetupView .agentUtilityGroup { min-height:0 !important; height:auto !important; align-content:start !important; contain:layout style !important; }
      #agentSetupView .settingsGroupGrid { align-items:start !important; }
      #agentSetupView .modalActions { position:sticky !important; bottom:0 !important; z-index:50 !important; display:flex !important; justify-content:flex-end !important; gap:10px !important; margin:0 -16px -16px !important; padding:16px 24px !important; border-top:1px solid var(--line) !important; background:linear-gradient(180deg, rgba(17,24,39,.90), rgba(17,24,39,.98)) !important; backdrop-filter:blur(8px) !important; }
      #agentSetupView .modalActions #saveAgentSettings { min-width:230px !important; box-shadow:0 -6px 20px rgba(0,0,0,.18) !important; }
      @media (max-width:900px) { main { padding:16px 12px 32px !important; } #agentSetupView .configModalBody { grid-template-columns:1fr !important; padding:12px 0 90px !important; } #agentSetupView .settingsTabButton { flex:1 1 140px !important; } #agentSetupView .modalActions { margin:0 -16px -16px !important; padding:12px 14px !important; } #agentSetupView .modalActions #saveAgentSettings { width:100% !important; } }
    `;
    document.head.appendChild(style);
  }

  function patchDrawChart() {
    if (window.drawChart?.__directAgentChartViewFixPatchedV7) return;
    originalDrawChart = window.drawChart;
    if (typeof originalDrawChart !== 'function') return;
    window.drawChart = function patchedDirectAgentChartViewDrawChart(candles, overlay, indicatorData) {
      clearDirectAgentChartView();
      const result = originalDrawChart.apply(this, arguments);
      ensureDirectAgentChartView(candles || []);
      layoutAgentSetupSections();
      return result;
    };
    window.drawChart.__directAgentChartViewFixPatchedV7 = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__directAgentChartViewFixClearPatchedV7) return;
    originalClearKlineChart = window.clearKlineChart;
    if (typeof originalClearKlineChart !== 'function') return;
    window.clearKlineChart = function patchedDirectAgentChartViewClearChart() {
      clearDirectAgentChartView();
      return originalClearKlineChart.apply(this, arguments);
    };
    window.clearKlineChart.__directAgentChartViewFixClearPatchedV7 = true;
  }

  function install() {
    injectLayoutStyles();
    patchDrawChart();
    patchClearChart();
    layoutAgentSetupSections();
    applyChartHeight();
    window.setTimeout(layoutAgentSetupSections, 250);
    window.setTimeout(layoutAgentSetupSections, 1000);
    window.setTimeout(applyChartHeight, 350);
    window.setTimeout(applyChartHeight, 1200);
    document.body.dataset.directAgentChartViewFixPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  window.addEventListener('resize', applyChartHeight);
})();
