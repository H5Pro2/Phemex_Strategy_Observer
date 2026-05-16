const fmt = (value, fallback='-') => value === null || value === undefined ? fallback : value;
    const pct = value => value === null || value === undefined ? '-' : (value * 100).toFixed(2) + '%';
    const gateReasonLabel = reason => {
      const map = {
        invalid_side: 'keine LONG/SHORT-Richtung',
        missing_price: 'Entry/SL/TP fehlt',
        invalid_entry: 'Entry ungueltig',
        invalid_long_geometry: 'LONG-Geometrie ungueltig',
        invalid_short_geometry: 'SHORT-Geometrie ungueltig',
        invalid_risk_reward: 'Risk/Reward ungueltig',
        reward_too_small: 'TP-Abstand zu klein',
        sl_distance_too_high: 'SL-Abstand zu gross',
        rr_too_small: 'RR zu klein',
        net_profit_too_small: 'Netto-Profit zu klein'
      };
      return map[String(reason || '')] || fmt(reason);
    };
    const gateNumber = value => value === null || value === undefined || value === '' ? '-' : Number(value).toFixed(6);
    const gatePercent = value => value === null || value === undefined || value === '' ? '-' : (Number(value) * 100).toFixed(3) + '%';
    function gateDetailText(gate) {
      if (!gate) return 'wartet';
      const parts = [gate.trade_allowed ? 'OK' : `BLOCKED: ${gateReasonLabel(gate.reason)}`];
      if (gate.rr !== undefined) parts.push(`RR ${gateNumber(gate.rr)}`);
      if (gate.min_rr !== undefined) parts.push(`min RR ${gateNumber(gate.min_rr)}`);
      if (gate.risk_fraction !== undefined) parts.push(`Risk ${gatePercent(gate.risk_fraction)}`);
      if (gate.reward_fraction !== undefined) parts.push(`Reward ${gatePercent(gate.reward_fraction)}`);
      if (gate.net_profit_fraction !== undefined) parts.push(`Netto ${gatePercent(gate.net_profit_fraction)}`);
      if (gate.min_net_profit_fraction !== undefined) parts.push(`min Netto ${gatePercent(gate.min_net_profit_fraction)}`);
      if (gate.max_sl_distance_fraction !== undefined) parts.push(`max SL ${gatePercent(gate.max_sl_distance_fraction)}`);
      return parts.join(' | ');
    }
    function gateHtml(gate) {
      const cls = gate?.trade_allowed ? 'good' : 'dangerText';
      return `<span class="${cls}">${escapeHtml(gateDetailText(gate))}</span>`;
    }
    function lifecycleStageClass(stage) {
      const value = String(stage || '').toLowerCase();
      if (value === 'tp') return 'good';
      if (value === 'sl' || value === 'expired') return 'bad';
      if (value === 'open') return 'open';
      return 'pending';
    }
    function tradeTime(value) {
      if (!value) return '-';
      const number = Number(value);
      if (!Number.isFinite(number)) return '-';
      const ms = number > 1000000000000 ? number : number * 1000;
      return new Date(ms).toLocaleString('de-DE');
    }
    function renderTradeLifecycle(trade) {
      const lifecycle = trade?.lifecycle || {};
      const stage = lifecycle.current_stage || trade?.status || '-';
      const label = lifecycle.stage_label || fmt(trade?.status);
      const detail = lifecycle.stage_detail || '-';
      const steps = lifecycle.steps || [];
      const stepHtml = steps.map(step => {
        const state = String(step.state || 'waiting').toLowerCase();
        return `<span class="lifeStep ${state}" title="${escapeHtml(tradeTime(step.timestamp))}">${escapeHtml(step.label || step.key || '-')}</span>`;
      }).join(' ');
      return `<div class="lifeBox ${lifecycleStageClass(stage)}"><strong>${escapeHtml(label)}</strong><br><span>${escapeHtml(detail)}</span><div class="lifeSteps">${stepHtml}</div></div>`;
    }
    function tradeLifecycleTime(trade) {
      const lifecycle = trade?.lifecycle || {};
      const steps = lifecycle.steps || [];
      const current = steps.slice().reverse().find(step => step.timestamp);
      return tradeTime(current?.timestamp || trade?.closed_at || trade?.filled_at || trade?.created_at);
    }
    function tradePatternKey(trade) {
      const features = trade?.setup?.features || {};
      return String(features.brain_pattern_key || features.pattern_key || features.strategy || 'na');
    }
    function tradeResultBucket(trade) {
      const status = String(trade?.status || '').toLowerCase();
      const result = Number(trade?.result_r);
      if (status === 'pending' || status === 'open') return 'active';
      if (!Number.isFinite(result)) return status || 'unknown';
      if (result > 0) return 'win';
      if (result < 0) return 'loss';
      return 'breakeven';
    }
    function tradeMatchesFilters(trade) {
      const symbolOk = !selectedAsset || trade?.setup?.symbol === selectedAsset;
      const status = String(trade?.status || '').toLowerCase();
      const statusOk = selectedTradeStatus === '__ALL__' || status === selectedTradeStatus;
      const patternOk = selectedTradePattern === '__ALL__' || tradePatternKey(trade) === selectedTradePattern;
      const resultOk = selectedTradeResult === '__ALL__' || tradeResultBucket(trade) === selectedTradeResult;
      return symbolOk && statusOk && patternOk && resultOk;
    }
    function syncTradeHistoryFilters(tradesAll) {
      const statusEl = document.getElementById('tradeStatusFilter');
      const patternEl = document.getElementById('tradePatternFilter');
      const resultEl = document.getElementById('tradeResultFilter');
      if (!statusEl || !patternEl || !resultEl) return;
      const statuses = Array.from(new Set((tradesAll || []).map(t => String(t.status || '').toLowerCase()).filter(Boolean))).sort();
      const patterns = Array.from(new Set((tradesAll || []).map(tradePatternKey).filter(Boolean))).sort();
      const keepStatus = selectedTradeStatus;
      const keepPattern = selectedTradePattern;
      const keepResult = selectedTradeResult;
      statusEl.innerHTML = '<option value="__ALL__">Alle Status</option>' + statuses.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
      patternEl.innerHTML = '<option value="__ALL__">Alle Pattern</option>' + patterns.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
      resultEl.innerHTML = [
        '<option value="__ALL__">Alle Ergebnisse</option>',
        '<option value="active">Aktiv</option>',
        '<option value="win">Gewinn</option>',
        '<option value="loss">Verlust</option>',
        '<option value="breakeven">Break-even</option>',
        '<option value="expired">Expired</option>'
      ].join('');
      selectedTradeStatus = statuses.includes(keepStatus) ? keepStatus : '__ALL__';
      selectedTradePattern = patterns.includes(keepPattern) ? keepPattern : '__ALL__';
      selectedTradeResult = ['__ALL__', 'active', 'win', 'loss', 'breakeven', 'expired'].includes(keepResult) ? keepResult : '__ALL__';
      statusEl.value = selectedTradeStatus;
      patternEl.value = selectedTradePattern;
      resultEl.value = selectedTradeResult;
    }
    function tradeExportRows() {
      const tradesAll = latestStatusData?.paper?.trades || [];
      return tradesAll.filter(tradeMatchesFilters).slice().reverse().map(trade => {
        const setup = trade.setup || {};
        const features = setup.features || {};
        const lifecycle = trade.lifecycle || {};
        const gate = features.value_gate || features.economic_gate || {};
        return {
          id: trade.id || '',
          status: trade.status || '',
          symbol: setup.symbol || '',
          side: setup.side || '',
          size_mode: setup.trade_size_mode || '',
          planned_notional_usd: setup.planned_notional_usd ?? '',
          planned_quantity_asset: setup.planned_quantity_asset ?? '',
          entry: setup.entry ?? '',
          stop_loss: setup.stop_loss ?? '',
          take_profit: setup.take_profit ?? '',
          result_r: trade.result_r ?? '',
          risk_usd: trade.risk_usd ?? '',
          gross_pnl_usd: trade.gross_pnl_usd ?? '',
          estimated_fees_usd: trade.estimated_fees_usd ?? '',
          net_pnl_usd: trade.net_pnl_usd ?? '',
          confidence: setup.confidence ?? '',
          agent_pattern: tradePatternKey(trade),
          result_bucket: tradeResultBucket(trade),
          lifecycle_stage: lifecycle.current_stage || trade.status || '',
          lifecycle_detail: lifecycle.stage_detail || '',
          created_at: tradeTime(trade.created_at),
          filled_at: tradeTime(trade.filled_at),
          closed_at: tradeTime(trade.closed_at),
          gate_reason: gate.reason || '',
          gate_rr: gate.rr ?? '',
          gate_net_profit_fraction: gate.net_profit_fraction ?? '',
        };
      });
    }
    function downloadTextFile(filename, content, type) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }
    function csvCell(value) {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    }
    function exportTradeHistory(format) {
      const rows = tradeExportRows();
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      if (format === 'json') {
        downloadTextFile(`trade_history_${stamp}.json`, JSON.stringify(rows, null, 2), 'application/json;charset=utf-8');
        setControlMessage(`JSON Export erstellt: ${rows.length} Trades`);
        return;
      }
      const headers = Object.keys(rows[0] || {
        id: '', status: '', symbol: '', side: '', size_mode: '', planned_notional_usd: '', planned_quantity_asset: '', entry: '', stop_loss: '', take_profit: '', result_r: '', confidence: '', agent_pattern: '', result_bucket: '', lifecycle_stage: '', lifecycle_detail: '', created_at: '', filled_at: '', closed_at: '', gate_reason: '', gate_rr: '', gate_net_profit_fraction: ''
      });
      const csv = [headers.map(csvCell).join(';')].concat(rows.map(row => headers.map(header => csvCell(row[header])).join(';'))).join('\\n');
      downloadTextFile(`trade_history_${stamp}.csv`, csv, 'text/csv;charset=utf-8');
      setControlMessage(`CSV Export erstellt: ${rows.length} Trades`);
    }
    const percentInputValue = value => {
      const number = Number(value ?? 0);
      if (!Number.isFinite(number)) return 0;
      return Math.round(number * 1000000) / 10000;
    };
    const percentOutputValue = value => {
      const number = Number(String(value ?? '0').replace(',', '.'));
      if (!Number.isFinite(number)) return 0;
      return Math.max(0, number) / 100;
    };
    const percentDisplay = value => value === null || value === undefined ? '-' : percentInputValue(value).toFixed(2) + '%';
    const money = (value, currency='USDT') => value === null || value === undefined ? '-' : Number(value).toFixed(2) + ' ' + currency;
    const pnlMoney = (value, currency='USDT') => value === null || value === undefined ? '-' : `${Number(value).toFixed(2)} ${currency}`;
    const ALL_ASSETS_VALUE = '__ALL__';
    let selectedAsset = null;
    let selectedTradeStatus = '__ALL__';
    let selectedTradePattern = '__ALL__';
    let selectedTradeResult = '__ALL__';
    let selectedAgentAsset = null;
    let latestStatusData = null;
    let currentView = 'dashboard';
    let agentSortMode = 'score_desc';
    let agentRoleFilter = 'all';
    let lastChartKey = '';
    let klineChart = null;
    let klineOverlayIds = [];
    let marketStructureOverlaysRegistered = false;
    let chartConfig = null;
    let latestConfig = {};
    function applyUiTheme(theme) {
      const value = theme === 'light' ? 'light' : 'dark';
      document.body.dataset.theme = value;
    }
    let localTradeSizes = {};
    let activeTradeSizeSymbol = null;
    let localMinProfitFractions = {};
    let localMaxSlDistanceFractions = {};
    let valueGatePriceCache = {};
    let valueGatePreviewToken = 0;
    let lastActionMessage = null;
    let lastIndicatorData = null;
    let lastChartRows = [];
    let lastReplayPreviewData = null;
    let lastReplayHistoryData = null;
    let replayRequestRunning = false;
    let refreshRunning = false;
    let refreshFailedCount = 0;
    function td(value) { return `<td>${value}</td>`; }
    function assetViewLabel(value) {
      return value ? value : 'Gesamt';
    }
    function selectedAssetValue() {
      return selectedAsset || ALL_ASSETS_VALUE;
    }
    function setSelectedAssetFromDropdown(value) {
      selectedAsset = value === ALL_ASSETS_VALUE ? null : value;
    }
    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
    }
    function timeframeLabel(seconds) {
      const map = {60:'1m', 300:'5m', 900:'15m', 1800:'30m', 3600:'1h', 14400:'4h', 86400:'1D'};
      return map[Number(seconds)] || `${seconds}s`;
    }
    function emaSourceLabel(source, signalTf) {
      if (source === 'daily') return 'Daily EMA';
      return `EMA auf ${timeframeLabel(signalTf)}`;
    }
    function updateEmaConfigVisibility() {
      const mode = document.getElementById('cfgTrendMode')?.value || 'day_candle';
      const source = document.getElementById('cfgTrendEmaSource');
      const period = document.getElementById('cfgTrendEma');
      const showSource = mode === 'ema';
      const showCustomPeriod = showSource && source && source.value !== 'daily';
      if (source) source.parentElement.style.display = showSource ? 'block' : 'none';
      if (period) period.parentElement.style.display = showCustomPeriod ? 'block' : 'none';
    }
    function isModalOpen(id) {
      const modal = document.getElementById(id);
      return modal && modal.classList.contains('open');
    }
    function setControlMessage(message, level='ok') {
      lastActionMessage = { message, level, until: Date.now() + 4500 };
      renderControlMessage(message);
    }
    function renderControlMessage(fallback='Bereit') {
      const el = document.getElementById('controlStatus');
      if (!el) return;
      if (lastActionMessage && Date.now() < lastActionMessage.until) {
        el.textContent = lastActionMessage.message;
        el.className = `controlStatus ${lastActionMessage.level}`;
        return;
      }
      lastActionMessage = null;
      el.textContent = fallback;
      el.className = 'controlStatus';
    }
    function renderBotControls(cfg) {
      const running = !!cfg.observer_enabled;
      const start = document.getElementById('startBot');
      const stop = document.getElementById('stopBot');
      const activeSymbols = cfg.symbols || [];
      const active = cfg.observer_asset_mode === 'multi'
        ? `${activeSymbols.length} Assets`
        : (activeSymbols[0] || '-');
      if (start) {
        start.classList.toggle('available', !running);
        start.classList.toggle('running', running);
        start.disabled = running;
        start.textContent = running ? 'Läuft' : 'Start';
        start.title = running ? 'Scanner läuft bereits' : 'Scanner starten';
      }
      if (stop) {
        stop.classList.toggle('available', running);
        stop.classList.toggle('stopped', !running);
        stop.disabled = !running;
        stop.textContent = running ? 'Stop' : 'Gestoppt';
        stop.title = running ? 'Scanner stoppen' : 'Scanner ist bereits gestoppt';
      }
      renderControlMessage(running ? `Scanner aktiv: ${active}` : `Scanner gestoppt: ${active}`);
    }
    function renderDayCandleStatus(data, cfg) {
      const activeSymbols = cfg.symbols || [];
      const symbol = selectedAsset || activeSymbols[0] || 'BTCUSDT';
      const scan = data.cycle?.symbols?.[symbol]?.scan || {};
      const day = scan.day_candle || {};
      const direction = String(day.direction || 'neutral').toLowerCase();
      const panel = document.getElementById('dayCandlePanel');
      const icon = document.getElementById('dayCandleIcon');
      const detail = document.getElementById('dayCandleDetail');
      if (!panel || !icon || !detail) return;
      panel.className = `dayCandlePanel ${direction}`;
      if (direction === 'long' || direction === 'short') {
        const image = direction === 'long' ? '/files/arrow_up.png' : '/files/arrow_down.png';
        icon.innerHTML = `<img src="${image}" alt="${direction}">`;
      } else {
        icon.innerHTML = '<span class="dayCandleFallback">–</span>';
      }
      const label = direction === 'long' ? 'LONG' : direction === 'short' ? 'SHORT' : 'NEUTRAL';
      const open = day.open !== undefined ? `O ${fmt(day.open)}` : '';
      const close = day.close !== undefined ? `C ${fmt(day.close)}` : '';
      const candles = day.candles !== undefined ? `${fmt(day.candles)} Kerzen` : 'keine Day-Candle';
      detail.textContent = `${label} · ${[open, close, candles].filter(Boolean).join(' · ')}`;
    }
    function flashButton(id) {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.classList.add('flash');
      window.setTimeout(() => btn.classList.remove('flash'), 700);
    }
    function syncSwitchState(inputId, stateId, activeText='Aktiv', inactiveText='Aus', boxId=null) {
      const input = document.getElementById(inputId);
      const state = document.getElementById(stateId);
      if (!input || !state) return;
      const active = !!input.checked;
      state.textContent = active ? activeText : inactiveText;
      state.classList.toggle('active', active);
      if (boxId) {
        const box = document.getElementById(boxId);
        if (box) box.classList.toggle('active', active);
      }
    }
    function syncAllSwitchStates() {
      syncSwitchState('paperToggle', 'paperToggleState', 'Aktiv', 'Aus', 'paperToggleBox');
      syncSwitchState('cfgCorrelationBlock', 'cfgCorrelationState');
      syncSwitchState('cfgTrendFilter', 'cfgTrendState');
      syncSwitchState('cfgIndicatorEnabled', 'cfgIndicatorEnabledState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowBosChoch', 'cfgIndicatorShowBosChochState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowBoxes', 'cfgIndicatorShowBoxesState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowSwingLabels', 'cfgIndicatorShowSwingLabelsState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowHma', 'cfgIndicatorShowHmaState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowSma', 'cfgIndicatorShowSmaState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowTripleEma', 'cfgIndicatorShowTripleEmaState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowMfi', 'cfgIndicatorShowMfiState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowMacd', 'cfgIndicatorShowMacdState', 'Aktiv', 'Aus');
      syncSwitchState('cfgIndicatorShowSupportResistance', 'cfgIndicatorShowSupportResistanceState', 'Aktiv', 'Aus');
      syncSwitchState('cfgBrainEnabled', 'cfgBrainEnabledState', 'Aktiv', 'Aus');
      syncSwitchState('cfgBrainRequireBox', 'cfgBrainRequireBoxState', 'Aktiv', 'Aus');
      syncSwitchState('cfgBrainLlmLayer', 'cfgBrainLlmLayerState', 'Aktiv', 'Aus');
      syncSwitchState('cfgOllamaEnabled', 'cfgOllamaEnabledState', 'Aktiv', 'Aus');
      syncSwitchState('cfgOllamaBlockHint', 'cfgOllamaBlockHintState', 'Aktiv', 'Aus');
      syncSwitchState('cfgAgentShowOffline', 'cfgAgentShowOfflineState', 'Aktiv', 'Aus');
      document.querySelectorAll('[data-agent-enabled]').forEach(input => syncSwitchState(input.id, `${input.id}State`, 'Aktiv', 'Aus'));
      document.querySelectorAll('[data-agent-blocking]').forEach(input => syncSwitchState(input.id, `${input.id}State`, 'Block', 'Info'));
      syncUtilityAgentGroupStates();
    }
    async function refresh() {
      if (refreshRunning) return;
      refreshRunning = true;
      try {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 9000);
      const response = await fetch('/api/status', { cache: 'no-store', signal: controller.signal });
      window.clearTimeout(timeout);
      if (!response.ok) throw new Error(`status ${response.status}`);
      const data = await response.json();
      refreshFailedCount = 0;
      latestStatusData = data;
      const perf = data.paper?.performance || {};
      const cfg = data.config || {};
      latestConfig = cfg;
      renderReplayRuleWeightStatus();
      applyUiTheme(cfg.ui_theme);
      updateKlineChartStyles();
      const account = data.account || {};
      const currency = account.currency || cfg.account_balance_currency || 'USDT';
      const activeSymbols = cfg.symbols || [];
      const activeSummary = cfg.observer_asset_mode === 'multi'
        ? `${activeSymbols.length} Assets aktiv`
        : `${activeSymbols[0] || '-'} aktiv`;
      document.getElementById('subtitle').textContent = `Letztes Update: ${fmt(data.bot?.last_update_utc)} | ${activeSummary}`;
      const scanner = cfg.observer_enabled ? 'Scanner läuft' : 'Scanner gestoppt';
      const paperMode = cfg.paper_trading_enabled ? 'Testmodus/Paper' : 'Testmodus/Signal-only';
      const assetModeLabel = cfg.observer_asset_mode === 'multi' ? 'Multi Asset' : 'Single Asset';
      const statusPanel = document.getElementById('statusPanel');
      const liveActive = !!data.bot?.live_trading_enabled;
      const apiWarning = account.status && account.status !== 'ok';
      statusPanel.className = 'statusPanel ' + (liveActive ? 'live' : apiWarning ? 'warning' : cfg.observer_enabled ? 'running' : 'stopped');
      document.getElementById('statusTitle').textContent = liveActive ? 'LIVE' : paperMode.toUpperCase();
      document.getElementById('statusDetail').textContent = apiWarning ? `${assetModeLabel} | ${scanner} | API pruefen` : `${assetModeLabel} | ${scanner}`;
      document.getElementById('accountBalance').textContent = account.status === 'ok' ? money(account.account_balance, currency) : 'API nicht verbunden';
      document.getElementById('availableBalance').textContent = account.status === 'ok' ? money(account.available_balance_estimate, currency) : fmt(account.error, '-');
      document.getElementById('profit').textContent = pct(perf.profit_fraction);
      document.getElementById('profit').className = 'value ' + ((perf.profit_fraction || 0) >= 0 ? 'good' : 'bad');
      document.getElementById('winrate').textContent = pct(perf.win_rate);
      if (!isModalOpen('tradingModal')) {
        document.getElementById('paperToggle').checked = !!cfg.paper_trading_enabled;
        syncSwitchState('paperToggle', 'paperToggleState', 'Aktiv', 'Aus', 'paperToggleBox');
        localTradeSizes = JSON.parse(JSON.stringify(cfg.trade_sizes_by_symbol || {}));
        renderTradeSizeAssetSelector(cfg);
        loadTradeSizeForSelectedAsset();
        updateSizeVisibility();
      }

      const tradesAll = data.paper?.trades || [];
      const watchlist = cfg.watchlist_assets || [];
      const watchSymbols = watchlist.map(item => item.symbol);
      const extraSymbols = tradesAll.map(t => t.setup?.symbol).filter(Boolean).filter(symbol => !watchSymbols.includes(symbol));
      const symbols = [...watchSymbols, ...Array.from(new Set(extraSymbols))];
      if (selectedAsset && !symbols.includes(selectedAsset)) selectedAsset = null;
      syncChartAssetOptions(cfg);
      const assetFilter = document.getElementById('assetFilter');
      const oldValue = assetFilter.value || selectedAssetValue();
      const assetOptions = [`<option value="${ALL_ASSETS_VALUE}">Gesamt / alles anzeigen</option>`].concat(symbols.map(symbol => {
        const item = watchlist.find(asset => asset.symbol === symbol);
        const active = (cfg.symbols || []).includes(symbol) ? ' *' : '';
        return `<option value="${symbol}">${item ? item.label : symbol}${active}</option>`;
      }));
      assetFilter.innerHTML = assetOptions.join('');
      if (oldValue === ALL_ASSETS_VALUE || !symbols.includes(oldValue)) {
        selectedAsset = null;
      } else {
        selectedAsset = oldValue;
      }
      assetFilter.value = selectedAssetValue();
      renderDayCandleStatus(data, cfg);
      renderBotControls(cfg);
      syncAgentAssetOptions(cfg);
      syncReplayAssetOptions(cfg);
      renderLlmAuditSummary(data, cfg);
      renderAgentViewer(data, cfg);
      const viewLabel = assetViewLabel(selectedAsset);
      syncTradeHistoryFilters(tradesAll);
      document.getElementById('tradesTitle').textContent = `Trade-History (${viewLabel})`;
      const assetStats = selectedAsset ? data.paper?.per_symbol?.[selectedAsset] : null;
      if (assetStats && !lastActionMessage) {
        renderControlMessage(`Ansicht ${selectedAsset}: ${assetStats.closed} geschlossen, Winrate ${pct(assetStats.win_rate)}, Sum R ${assetStats.sum_r}`);
      } else if (!selectedAsset && !lastActionMessage) {
        renderControlMessage(`Gesamtansicht: ${fmt(perf.closed, 0)} geschlossen, ${fmt(data.paper?.open_trades, 0)} offen, ${fmt(data.paper?.pending_trades, 0)} pending`);
      }

      const trades = tradesAll.filter(tradeMatchesFilters).slice().reverse().slice(0, 50);
      const tradeFilterInfo = document.getElementById('tradeFilterInfo');
      if (tradeFilterInfo) tradeFilterInfo.textContent = `${trades.length} von ${tradesAll.length} Trades sichtbar`;
      document.getElementById('tradeRows').innerHTML = trades.map(t => {
        const s = t.setup || {};
        const size = s.trade_size_mode === 'asset'
          ? `${fmt(s.planned_quantity_asset)} asset`
          : `${fmt(s.planned_notional_usd)} USD`;
        return '<tr>' + [
          td(`<span class="tradeStatus ${lifecycleStageClass(t.status)}">${escapeHtml(fmt(t.status))}</span>`),
          td(fmt(s.symbol)), td(fmt(s.side)), td(size), td(fmt(s.entry)), td(fmt(s.stop_loss)),
          td(fmt(s.take_profit)), td(fmt(t.result_r)), td(fmt(s.confidence)),
          td(renderTradeLifecycle(t)), td(tradeLifecycleTime(t))
        ].join('') + '</tr>';
      }).join('') || '<tr><td colspan="11">Noch keine Paper-Trades.</td></tr>';

      const cycle = data.cycle || {};
      const eventBySymbol = {};
      (cycle.events || []).forEach(event => {
        if (event.symbol && !eventBySymbol[event.symbol]) eventBySymbol[event.symbol] = event;
        if (event.setup?.symbol && !eventBySymbol[event.setup.symbol]) eventBySymbol[event.setup.symbol] = event;
      });
      const debugSymbols = Object.entries(cycle.symbols || {}).filter(([symbol]) => !selectedAsset || symbol === selectedAsset);
      document.getElementById('debugRows').innerHTML = debugSymbols.map(([symbol, info]) => {
        const scan = info.scan || {};
        const event = eventBySymbol[symbol] || {};
        const gate = event.reason === 'value_gate'
          ? gateHtml(event.value_result)
          : 'nicht erreicht';
        const status = scan.setup_found ? '<span class="good">Setup Kandidat</span>' : '<span class="dangerText">Kein Setup</span>';
        const side = scan.side ? `side ${scan.side}` : 'side -';
        const zone = scan.zone_type
          ? `zone ${scan.zone_type} ${fmt(scan.zone_low)} - ${fmt(scan.zone_high)} score ${fmt(scan.zone_score)} retests ${fmt(scan.retests)}`
          : `nearest ${fmt(scan.nearest_zone_type)} ${fmt(scan.nearest_zone_low)} - ${fmt(scan.nearest_zone_high)} dist ${fmt(scan.nearest_zone_distance)}`;
        const impulse = scan.impulse_time ? `base ${fmt(scan.base_candles)} | impulse body ${fmt(scan.impulse_body_ratio)} xRange ${fmt(scan.impulse_range_multiple)}` : '';
        const entry = scan.entry_method ? `entry ${scan.entry_method} | has_fvg ${fmt(scan.has_fvg)} | zone ${fmt(scan.entry_zone_low)} - ${fmt(scan.entry_zone_high)}` : '';
        const confirm = scan.confirmation_candles_after_signal !== undefined ? `confirm ${scan.confirmation_candles_after_signal}` : '';
        const emaInfo = scan.ema?.active ? `ema ${emaSourceLabel(scan.ema.source, cfg.signal_timeframe_seconds)} ${fmt(scan.ema.period)} | ${fmt(scan.ema.direction)} | C ${fmt(scan.ema.close)} / EMA ${fmt(scan.ema.ema)}` : '';
        const confirmationDebug = scan.confirmation_debug?.closest
          ? `best window: touch ${fmt(scan.confirmation_debug.closest.zone_touch_ok)} / body ${fmt(scan.confirmation_debug.closest.body_ok)} / break ${fmt(scan.confirmation_debug.closest.break_ok)} / fvg ${fmt(scan.confirmation_debug.closest.fvg_ok)} / rejection ${fmt(scan.confirmation_debug.closest.rejection_ok)}<br>windows touch ${fmt(scan.confirmation_debug.zone_touch_windows, 0)} body ${fmt(scan.confirmation_debug.body_ok_windows, 0)} break ${fmt(scan.confirmation_debug.break_ok_windows, 0)} fvg ${fmt(scan.confirmation_debug.fvg_ok_windows, 0)} rejection ${fmt(scan.confirmation_debug.rejection_ok_windows, 0)}`
          : '';
        return '<tr>' + [
          td(symbol),
          td(status),
          td(fmt(scan.reason || event.reason)),
          td([side, zone, impulse, entry, confirm, emaInfo, confirmationDebug].filter(Boolean).join('<br>')),
          td(gate)
        ].join('') + '</tr>';
      }).join('') || '<tr><td colspan="5">Noch kein Scan-Debug vorhanden.</td></tr>';

      const botRows = [
        ['Modus', data.bot?.mode],
        ['Live', data.bot?.live_trading_enabled ? 'aktiv' : 'gesperrt'],
        ['Scanner', cfg.observer_enabled ? 'läuft' : 'gestoppt'],
        ['Paper-Trading', cfg.paper_trading_enabled ? 'aktiv' : 'aus'],
        ['Asset Mode', cfg.observer_asset_mode === 'multi' ? 'Multi Asset' : 'Single Asset'],
        ['Risk Locks', `max ${cfg.max_open_trades_total} gesamt / ${cfg.max_open_trades_per_asset} je Asset`],
        ['Correlation Lock', cfg.block_same_direction_correlated_trades ? 'aktiv' : 'aus'],
        ['Stop-Loss', cfg.stop_loss_mode === 'atr' ? `ATR ${fmt(cfg.stop_loss_atr_period)} × ${fmt(cfg.stop_loss_atr_multiplier)}` : `Struktur + ${fmt(cfg.stop_loss_buffer_percent)}% Puffer`],
        ['Phemex Balance', account.status === 'ok' ? money(account.account_balance, currency) : fmt(account.error)],
        ['Positionsgroesse', cfg.trade_size_mode === 'asset' ? `${cfg.trade_size_asset} Asset` : `${cfg.trade_size_usd} USD/USDT`],
        ['Timeframes', `${timeframeLabel(data.config?.signal_timeframe_seconds)} / ${timeframeLabel(data.config?.confirmation_timeframe_seconds)}`],
        ['Trend', cfg.trend_filter_mode === 'ema' ? `${emaSourceLabel(cfg.trend_ema_source, cfg.signal_timeframe_seconds)} ${cfg.trend_ema_period}${cfg.use_trend_filter ? ' blockierend' : ' optional'}` : (cfg.trend_filter_mode === 'day_candle' ? `Day-Candle${cfg.use_trend_filter ? ' blockierend' : ' Status'}` : 'aus')],
        ['Loops', `Phemex ${fmt(cfg.phemex_poll_seconds ?? cfg.poll_seconds)}s / System ${fmt(cfg.system_loop_seconds)}s`],
        ['TP/SL', `${data.config?.reward_risk}:1`],
        ['Value Gate', `min Netto ${percentDisplay(cfg.min_net_profit_fraction)} | max SL ${percentDisplay(cfg.max_sl_distance_fraction)}`],
        ['Ollama Audit', `${cfg.brain_llm_layer_enabled && cfg.ollama_enabled ? 'aktiv' : 'aus'} | ${fmt(cfg.ollama_model || 'qwen2.5:3b')}`],
        ['Paper-Trades', `${fmt(perf.closed, 0)} geschlossen / ${fmt(data.paper?.open_trades, 0)} offen / ${fmt(data.paper?.pending_trades, 0)} pending`],
      ];
      document.getElementById('botRows').innerHTML = botRows.map(([k,v]) => `<tr><th>${k}</th><td>${fmt(v)}</td></tr>`).join('');

      const buckets = data.memory?.top_buckets || [];
      document.getElementById('bucketRows').innerHTML = buckets.map(b => '<tr>' + [
        td(`<code>${b.key}</code>`), td(b.count), td(pct(b.win_rate)), td(b.avg_r)
      ].join('') + '</tr>').join('') || '<tr><td colspan="4">Noch keine abgeschlossenen Trades im Lernspeicher.</td></tr>';
      document.getElementById('cycle').textContent = JSON.stringify(data.cycle || {}, null, 2);
      } catch (error) {
        refreshFailedCount += 1;
        console.error('Dashboard refresh failed', error);
        renderControlMessage(`Dashboard-Refresh Fehler (${refreshFailedCount})`, 'warn');
      } finally {
        refreshRunning = false;
      }
    }
    function normalizeReplaySymbol(value) {
      return String(value || '').replace('.P', '').split(':', 1)[0].trim().toUpperCase();
    }
    function syncReplayAssetOptions(cfg) {
      const replayAsset = document.getElementById('replayAsset');
      if (!replayAsset) return;
      const current = normalizeReplaySymbol(replayAsset.value);
      const watchlist = cfg?.watchlist_assets || latestConfig?.watchlist_assets || [];
      const assetList = cfg?.asset_list || latestConfig?.asset_list || [];
      const activeSymbols = cfg?.symbols || latestConfig?.symbols || [];
      const symbols = Array.from(new Set([
        ...watchlist.map(item => item?.symbol).filter(Boolean),
        ...assetList,
        ...activeSymbols,
      ].map(normalizeReplaySymbol).filter(Boolean)));
      if (!symbols.length) symbols.push('BTCUSDT');
      replayAsset.innerHTML = symbols.map(symbol => `<option value="${escapeHtml(symbol)}">${escapeHtml(symbol)}</option>`).join('');
      if (symbols.includes(current)) {
        replayAsset.value = current;
      } else {
        replayAsset.value = symbols[0];
      }
    }
    function replayGateLabel(gate) {
      if (!gate) return '-';
      if (gate.trade_allowed) return `OK · RR ${fmt(gate.rr)}`;
      return `BLOCK · ${fmt(gate.reason)}`;
    }
    function replayTradeLabel(frame) {
      const events = frame?.replay_events || [];
      const summary = frame?.replay_trade_summary || {};
      const eventText = events.length
        ? events.map(event => `${fmt(event.status)}${event.result_r !== undefined && event.result_r !== null ? ' ' + fmt(event.result_r) + 'R' : ''}`).join(' / ')
        : '-';
      return `${eventText}<br><span class="label">P ${fmt(summary.pending, 0)} · O ${fmt(summary.open, 0)} · TP ${fmt(summary.tp, 0)} · SL ${fmt(summary.sl, 0)} · Exp ${fmt(summary.expired, 0)}</span>`;
    }
    function replayDecisionValue(frame) {
      return String(frame?.decision || frame?.ceo_signal || '').toUpperCase();
    }
    function replayFrameTradeStatuses(frame) {
      return (frame?.replay_events || []).map(event => String(event.status || '').toLowerCase()).filter(Boolean);
    }
    function replayFrameMatchesFilters(frame) {
      const decisionFilter = document.getElementById('replayFilterDecision')?.value || 'all';
      const gateFilter = document.getElementById('replayFilterGate')?.value || 'all';
      const resultFilter = document.getElementById('replayFilterResult')?.value || 'all';
      if (decisionFilter !== 'all' && replayDecisionValue(frame) !== decisionFilter) return false;
      const gate = frame?.gate || null;
      if (gateFilter === 'allowed' && !gate?.trade_allowed) return false;
      if (gateFilter === 'blocked' && (!gate || gate.trade_allowed)) return false;
      if (gateFilter === 'missing' && gate) return false;
      const statuses = replayFrameTradeStatuses(frame);
      if (resultFilter === 'created' && statuses.length === 0) return false;
      if (resultFilter === 'none' && statuses.length > 0) return false;
      if (!['all', 'created', 'none'].includes(resultFilter) && !statuses.includes(resultFilter)) return false;
      return true;
    }
    function filteredReplayFrames(data) {
      return (data?.frames || []).filter(frame => replayFrameMatchesFilters(frame));
    }
    function renderReplayFilterSummary(data, shownCount, filteredCount=null, displayLimit=null) {
      const el = document.getElementById('replayFilterSummary');
      if (!el) return;
      const returned = (data?.frames || []).length;
      const fullTotal = Number(data?.summary?.frames || returned);
      const filtered = filteredCount === null ? returned : filteredCount;
      const limitText = displayLimit && filtered > shownCount ? ` · Anzeige max ${fmt(displayLimit, 0)}` : '';
      const backendLimitText = fullTotal > returned ? ` · geladen ${fmt(returned, 0)} von ${fmt(fullTotal, 0)}` : '';
      el.textContent = `Filter: ${fmt(shownCount, 0)} sichtbar / ${fmt(filtered, 0)} Treffer${backendLimitText}${limitText}`;
      el.className = shownCount === filtered && fullTotal === returned ? 'controlStatus' : 'controlStatus warn';
    }

    function replayRuleClass(quality) {
      const value = String(quality || 'WATCH').toUpperCase();
      if (value === 'GOOD') return 'good';
      if (value === 'BAD') return 'bad';
      return 'watch';
    }
    function replayRuleMinCount(memory=null) {
      return Math.max(3, Number(memory?.rule_min_count ?? latestConfig?.replay_rule_weight_min_count ?? 5));
    }
    function replayRuleAdjustment(rule, memory=null) {
      const quality = String(rule?.quality || 'WATCH').toUpperCase();
      const maxAbs = Math.max(0, Number(memory?.rule_max_abs_adjustment ?? latestConfig?.replay_rule_max_abs_adjustment ?? 12));
      if (quality === 'GOOD') return Math.max(0, Math.min(maxAbs, Number(memory?.rule_good_bonus ?? latestConfig?.replay_rule_good_bonus ?? 6)));
      if (quality === 'BAD') return Math.max(-maxAbs, Math.min(0, Number(memory?.rule_bad_penalty ?? latestConfig?.replay_rule_bad_penalty ?? -10)));
      return 0;
    }
    function replayRuleSafetyClass(rule, memory=null) {
      if (rule?.eligible) return 'safe';
      const count = Number(rule?.count || 0);
      return count < replayRuleMinCount(memory) ? 'warn' : 'neutral';
    }
    function replayRuleSafetyText(rule, memory=null) {
      if (rule?.eligible) return `aktivierbar · min ${fmt(replayRuleMinCount(memory), 0)}`;
      const count = Number(rule?.count || 0);
      if (count < replayRuleMinCount(memory)) return `zu wenig Daten · min ${fmt(replayRuleMinCount(memory), 0)}`;
      return 'nur Beobachtung';
    }
    function replayRuleScopeText(rule) {
      const scope = String(rule?.scope || latestConfig?.replay_rule_scope || 'asset').toLowerCase();
      const symbol = rule?.symbol || '-';
      return scope === 'global' ? 'global' : `asset · ${symbol}`;
    }
    function replayActionClass(action) {
      const value = String(action || '').toUpperCase();
      if (value === 'PRIORITY') return 'priority';
      if (value === 'AVOID') return 'avoid';
      if (value === 'FEE_DRAG') return 'watch';
      if (value === 'WAIT') return 'wait';
      return 'watch';
    }
    function replayActionText(asset) {
      return asset?.action_label || (asset?.action || 'beobachten');
    }

    function renderReplayMemoryTest(data) {
      const summaryEl = document.getElementById('replayMemoryTestSummary');
      const rowsEl = document.getElementById('replayMemoryRows');
      const rulesSummaryEl = document.getElementById('replayPreviewRulesSummary');
      const ruleRowsEl = document.getElementById('replayPreviewRuleRows');
      const memory = data?.memory_test || null;
      if (!summaryEl || !rowsEl) return;
      if (!memory) {
        summaryEl.textContent = 'Memory-Testmodus: keine Daten.';
        rowsEl.innerHTML = '<tr><td colspan="5">Keine Replay-Memory-Buckets.</td></tr>';
        if (rulesSummaryEl) rulesSummaryEl.textContent = 'Replay-Lernregeln: keine Daten.';
        if (ruleRowsEl) ruleRowsEl.innerHTML = '<tr><td colspan="8">Keine Replay-Lernregeln.</td></tr>';
        return;
      }
      summaryEl.innerHTML = [
        `<strong>Memory-Testmodus</strong> · isoliert vom Live-Lernspeicher: ${memory.isolated_from_live_memory ? 'Ja' : 'Nein'}`,
        `Abgeschlossene Replay-Trades ${fmt(memory.completed_trades, 0)} · Buckets ${fmt(memory.bucket_count, 0)}`,
        `Winrate ${pct(memory.win_rate)} · Sum R ${fmt(memory.sum_r, 0)}`,
      ].join('<br>');
      const buckets = memory.top_buckets || [];
      rowsEl.innerHTML = buckets.map(bucket => {
        const context = [
          `Entry ${Object.keys(bucket.entry_methods || {}).join(', ') || '-'}`,
          `Phase ${Object.keys(bucket.market_phases || {}).join(', ') || '-'}`,
          `Vola ${Object.keys(bucket.volatility || {}).join(', ') || '-'}`,
          `Session ${Object.keys(bucket.sessions || {}).join(', ') || '-'}`,
        ].join('<br>');
        return '<tr>' + [
          td(`<code>${escapeHtml(bucket.key || '-')}</code>`),
          td(fmt(bucket.count, 0)),
          td(pct(bucket.win_rate)),
          td(fmt(bucket.avg_r)),
          td(context),
        ].join('') + '</tr>';
      }).join('') || '<tr><td colspan="5">Keine abgeschlossenen Replay-Trades für Memory-Test.</td></tr>';

      const rules = memory.preview_rules || [];
      const goodRules = rules.filter(rule => String(rule.quality).toUpperCase() === 'GOOD').length;
      const badRules = rules.filter(rule => String(rule.quality).toUpperCase() === 'BAD').length;
      const watchRules = rules.filter(rule => String(rule.quality).toUpperCase() === 'WATCH').length;
      const eligibleRules = rules.filter(rule => rule.eligible).length;
      if (rulesSummaryEl) {
        const activeRules = (latestConfig?.replay_rule_weight_rules || []).length;
        const safetyLine = memory.rule_small_sample
          ? `Warnung: kleine Datenbasis · abgeschlossen ${fmt(memory.completed_trades, 0)} · empfohlen mindestens ${fmt(Math.max(replayRuleMinCount(memory) * 3, 20), 0)}`
          : `Datenbasis ausreichend · abgeschlossen ${fmt(memory.completed_trades, 0)}`;
        rulesSummaryEl.innerHTML = [
          `<strong>Replay-Lernregeln</strong> · ${memory.source === 'replay_history' ? 'aus gespeicherter Historie' : 'aktueller Replay-Test'} · zunächst nur Vorschau`,
          `GOOD ${fmt(goodRules, 0)} · BAD ${fmt(badRules, 0)} · WATCH ${fmt(watchRules, 0)} · aktivierbar ${fmt(eligibleRules, 0)}`,
          `Mindest-Trades je Pattern ${fmt(replayRuleMinCount(memory), 0)} · Bonus +${fmt(Math.abs(replayRuleAdjustment({quality:'GOOD'}, memory)), 0)} · Malus ${fmt(replayRuleAdjustment({quality:'BAD'}, memory), 0)} · Max ${fmt(memory.rule_max_abs_adjustment ?? latestConfig?.replay_rule_max_abs_adjustment ?? 12, 0)}`,
          `Status ${latestConfig?.replay_rule_weight_enabled ? 'aktiv' : 'Vorschau'} · übernommene Regeln ${fmt(activeRules, 0)} · Scope ${latestConfig?.replay_rule_scope || 'asset'}`,
          `Asset-Schutz: Regeln wirken nur auf das Asset, aus dem der Replay-Lauf stammt`,
          safetyLine,
        ].join('<br>');
        rulesSummaryEl.className = memory.rule_small_sample ? 'valueGatePreview controlStatus warn' : 'valueGatePreview';
      }
      renderReplayRuleWeightStatus();
      if (ruleRowsEl) {
        ruleRowsEl.innerHTML = rules.map(rule => '<tr>' + [
          td(`<span class="replayRuleQuality ${replayRuleClass(rule.quality) || 'watch'}">${escapeHtml(rule.quality || 'WATCH')}</span>`),
          td(`<span class="replayRuleScope">${escapeHtml(replayRuleScopeText(rule))}</span>`),
          td(`<code>${escapeHtml(rule.key || '-')}</code>`),
          td(`${fmt(rule.count, 0)} / ${fmt(rule.min_count ?? replayRuleMinCount(memory), 0)}`),
          td(pct(rule.win_rate)),
          td(fmt(rule.avg_r)),
          td(`<span class="replayRuleSafety ${replayRuleSafetyClass(rule, memory)}">${escapeHtml(replayRuleSafetyText(rule, memory))}</span>`),
          td(rule.eligible ? `${Number(replayRuleAdjustment(rule, memory)) >= 0 ? '+' : ''}${fmt(replayRuleAdjustment(rule, memory), 0)}` : '0'),
          td(escapeHtml(rule.action || '-')),
        ].join('') + '</tr>').join('') || '<tr><td colspan="9">Keine Replay-Lernregeln aus Replay-Memory.</td></tr>'; 
      }
    }


    function replayRulesForBrainWeight() {
      const memory = lastReplayPreviewData?.memory_test || {};
      const rules = memory?.preview_rules || [];
      const minCount = replayRuleMinCount(memory);
      return rules
        .filter(rule => ['GOOD', 'BAD'].includes(String(rule.quality || '').toUpperCase()))
        .filter(rule => rule.eligible && Number(rule.count || 0) >= minCount)
        .map(rule => ({
          key: rule.key,
          pattern_key: rule.pattern_key || '',
          symbol: rule.symbol || '',
          scope: rule.scope || latestConfig?.replay_rule_scope || 'asset',
          quality: String(rule.quality || 'WATCH').toUpperCase(),
          count: Number(rule.count || 0),
          min_count: minCount,
          adjustment: replayRuleAdjustment(rule, memory),
          win_rate: rule.win_rate ?? null,
          avg_r: rule.avg_r ?? null,
          sum_r: rule.sum_r ?? null,
        }));
    }

    function renderReplayRuleWeightStatus(message=null, level=null) {
      const el = document.getElementById('replayRuleWeightStatus');
      const manager = document.getElementById('replayRuleManager');
      if (!el && !manager) return;
      const enabled = !!latestConfig?.replay_rule_weight_enabled;
      const rules = latestConfig?.replay_rule_weight_rules || [];
      const count = rules.length;
      const goodCount = rules.filter(rule => String(rule.quality || '').toUpperCase() === 'GOOD').length;
      const badCount = rules.filter(rule => String(rule.quality || '').toUpperCase() === 'BAD').length;
      const scope = latestConfig?.replay_rule_scope || 'asset';
      const minCount = replayRuleMinCount();
      const maxAbs = latestConfig?.replay_rule_max_abs_adjustment ?? 12;
      if (el) {
        if (message) {
          el.textContent = message;
          el.className = `controlStatus ${level || 'ok'}`;
        } else {
          el.textContent = enabled ? `Replay-Regeln aktiv · ${count} Regeln` : `Replay-Regeln aus · ${count} Regeln gespeichert`;
          el.className = enabled ? 'controlStatus ok' : 'controlStatus';
        }
      }
      if (manager) {
        manager.innerHTML = [
          `<div class="replayRuleMetric"><span>Status</span><strong>${enabled ? 'Aktiv' : 'Aus'}</strong><small>${fmt(count, 0)} gespeicherte Regeln</small></div>`,
          `<div class="replayRuleMetric"><span>Qualität</span><strong>GOOD ${fmt(goodCount, 0)} · BAD ${fmt(badCount, 0)}</strong><small>WATCH bleibt ohne Brain-Gewichtung</small></div>`,
          `<div class="replayRuleMetric"><span>Sicherheit</span><strong>min ${fmt(minCount, 0)} Trades</strong><small>max Bonus/Malus ${fmt(maxAbs, 0)}</small></div>`,
          `<div class="replayRuleMetric"><span>Scope</span><strong>${escapeHtml(scope)}</strong><small>Asset-Regeln bevorzugt</small></div>`,
        ].join('');
      }
    }

    async function saveReplayRuleWeights(enabled) {
      const candidateRules = replayRulesForBrainWeight();
      const rules = enabled ? candidateRules : [];
      if (enabled && !rules.length) {
        renderReplayRuleWeightStatus('Keine sicheren GOOD/BAD-Regeln: Mindest-Trades nicht erreicht oder Datenbasis zu klein.', 'warn');
        return;
      }
      renderReplayRuleWeightStatus(enabled ? 'Replay-Regeln werden gespeichert...' : 'Replay-Regeln werden deaktiviert...', 'warn');
      const response = await fetch('/api/replay-rule-weights', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled, rules}),
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Replay-Lernregeln konnten nicht gespeichert werden');
      latestConfig = data;
      renderReplayRuleWeightStatus(enabled ? `Replay-Regeln aktiv · ${rules.length} Regeln übernommen` : 'Replay-Regeln deaktiviert · 0 aktive Regeln', 'ok');
      renderReplayMemoryTest(lastReplayPreviewData || {});
    }

    function renderReplayRows(data) {
      const rows = document.getElementById('replayRows');
      const filtered = filteredReplayFrames(data).slice().reverse();
      const displayLimit = Math.max(40, Number(latestConfig?.replay_frame_display_limit || 120));
      const frames = filtered.slice(0, displayLimit);
      renderReplayFilterSummary(data, frames.length, filtered.length, displayLimit);
      if (!rows) return;
      rows.innerHTML = frames.map(frame => {
        const candidate = frame.candidate || {};
        const entry = candidate.entry_price !== undefined ? `${fmt(candidate.entry_price)} / SL ${fmt(candidate.sl_price)} / TP ${fmt(candidate.tp_price)}` : '-';
        return '<tr>' + [
          td(fmt(frame.time_utc)),
          td(fmt(frame.close)),
          td(`${fmt(frame.ceo_signal)} · ${fmt(frame.ceo_score)}`),
          td(`${fmt(frame.decision)} · ${fmt(frame.brain_score)}`),
          td(replayGateLabel(frame.gate)),
          td(entry),
          td(replayTradeLabel(frame)),
          td(fmt(frame.brain_message)),
        ].join('') + '</tr>';
      }).join('') || '<tr><td colspan="8">Keine Replay-Frames für diesen Filter.</td></tr>';
    }
    function refreshReplayFilters() {
      if (lastReplayPreviewData) renderReplayRows(lastReplayPreviewData);
    }
    function replayExportRows(data) {
      const frames = filteredReplayFrames(data);
      return frames.map(frame => {
        const candidate = frame.candidate || {};
        const gate = frame.gate || {};
        const tradeSummary = frame.replay_trade_summary || {};
        const events = frame.replay_events || [];
        return {
          symbol: data.symbol || '',
          resolution: data.resolution || '',
          time_utc: frame.time_utc || '',
          close: frame.close ?? '',
          ceo_signal: frame.ceo_signal || '',
          ceo_score: frame.ceo_score ?? '',
          decision: frame.decision || '',
          brain_score: frame.brain_score ?? '',
          brain_message: frame.brain_message || '',
          gate_allowed: gate.trade_allowed ?? false,
          gate_reason: gate.reason || '',
          gate_rr: gate.rr ?? '',
          entry_price: candidate.entry_price ?? '',
          sl_price: candidate.sl_price ?? '',
          tp_price: candidate.tp_price ?? '',
          entry_method: candidate.entry_method || '',
          target_method: candidate.target_method || '',
          replay_events: events.map(event => event.status).join('|'),
          replay_result_r: events.map(event => event.result_r ?? '').filter(value => value !== '').join('|'),
          replay_pending: tradeSummary.pending ?? 0,
          replay_open: tradeSummary.open ?? 0,
          replay_tp: tradeSummary.tp ?? 0,
          replay_sl: tradeSummary.sl ?? 0,
          replay_expired: tradeSummary.expired ?? 0,
          replay_sum_r: tradeSummary.sum_r ?? 0,
          replay_expectancy_r: tradeSummary.expectancy_r ?? '',
          replay_profit_factor: tradeSummary.profit_factor ?? '',
          replay_max_drawdown_r: tradeSummary.max_drawdown_r ?? '',
          replay_max_drawdown_usd: tradeSummary.max_drawdown_usd ?? '',
          replay_best_pnl_series_usd: tradeSummary.best_pnl_series_usd ?? '',
          replay_worst_pnl_series_usd: tradeSummary.worst_pnl_series_usd ?? '',
          replay_break_even_win_rate: tradeSummary.break_even_win_rate ?? '',
          memory_pattern_key: candidate.pattern_key || '',
          memory_entry_method: candidate.entry_method || '',
        };
      });
    }
    function downloadTextFile(filename, content, mimeType) {
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }
    function csvEscape(value) {
      const text = String(value ?? '');
      return /[",\n;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    }
    function exportReplayPreview(format) {
      const status = document.getElementById('replayStatus');
      if (!lastReplayPreviewData) {
        if (status) {
          status.textContent = 'Kein Replay für Export vorhanden.';
          status.className = 'controlStatus warn';
        }
        return;
      }
      const symbol = lastReplayPreviewData.symbol || 'replay';
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      if (format === 'json') {
        downloadTextFile(`replay_${symbol}_${stamp}.json`, JSON.stringify(lastReplayPreviewData, null, 2), 'application/json;charset=utf-8');
      } else {
        const exportRows = replayExportRows(lastReplayPreviewData);
        const headers = exportRows.length ? Object.keys(exportRows[0]) : ['symbol', 'resolution'];
        const csv = [
          headers.join(';'),
          ...exportRows.map(row => headers.map(header => csvEscape(row[header])).join(';')),
        ].join('\\n');
        downloadTextFile(`replay_${symbol}_${stamp}.csv`, csv, 'text/csv;charset=utf-8');
      }
      if (status) {
        status.textContent = `Replay ${String(format).toUpperCase()} exportiert.`;
        status.className = 'controlStatus ok';
      }
    }
    function replaySelectedSymbol() {
      return document.getElementById('replayAsset')?.value || (latestConfig?.symbols || [])[0] || 'BTCUSDT';
    }
    function replayHistoryStatsSummary(asset) {
      const currency = latestConfig?.replay_pnl_currency || 'USDT';
      return [
        ['Asset Menge', fmt(asset.display_asset_quantity ?? asset.avg_asset_quantity)],
        ['RR Faktor', fmt(asset.avg_rr_factor)],
        ['TP', pnlMoney(asset.display_tp_price, currency)],
        ['SL', pnlMoney(asset.display_sl_price, currency)],
        ['Gebühren pro Trade', pnlMoney(asset.display_fee_or_trade_value_usd ?? asset.display_notional_usd ?? asset.avg_notional_usd, currency)],
        ['Netto PnL', pnlMoney(asset.net_pnl_usd, currency)],
      ];
    }
    function renderReplayAssetComparison(history) {
      const assets = history?.asset_stats || [];
      const cards = document.getElementById('replayAssetCompareCards');
      const rows = document.getElementById('replayAssetCompareRows');
      if (cards) {
        if (!assets.length) {
          cards.innerHTML = '<div class="valueGatePreview">Noch keine Asset-Historie vorhanden.</div>';
        } else {
          cards.innerHTML = assets.slice(0, 4).map(asset => `
            <div class="replayRankCard ${replayActionClass(asset.action)}">
              <div class="replayRankHead">
                <div class="replayRankSymbol">${escapeHtml(asset.symbol)}</div>
                <div class="replayRankBadge">Rang ${fmt(asset.rank, '-')} · ${escapeHtml(asset.ranking_grade || '-')}</div>
              </div>
              <div class="replayRankAction"><span class="replayDecisionBadge mini ${replayActionClass(asset.action)}">${escapeHtml(replayActionText(asset))}</span><small>${escapeHtml(asset.action_reason || '')}</small></div>
              <div class="replayRankStats">
                ${replayHistoryStatsSummary(asset).map(([label, value]) => `<div class="replayStatRow"><div class="replayStatLabel">${label}</div><div class="replayStatValue">${value}</div></div>`).join('')}
              </div>
            </div>
          `).join('');
        }
      }
      if (rows) {
        rows.innerHTML = assets.length ? assets.map(asset => `
          <tr>
            ${td(fmt(asset.rank))}
            ${td(escapeHtml(asset.symbol))}
            ${td(fmt(asset.display_asset_quantity ?? asset.avg_asset_quantity))}
            ${td(fmt(asset.avg_rr_factor))}
            ${td(pnlMoney(asset.display_tp_price, latestConfig?.replay_pnl_currency || 'USDT'))}
            ${td(pnlMoney(asset.display_sl_price, latestConfig?.replay_pnl_currency || 'USDT'))}
            ${td(pnlMoney(asset.display_fee_or_trade_value_usd ?? asset.display_notional_usd ?? asset.avg_notional_usd, latestConfig?.replay_pnl_currency || 'USDT'))}
            ${td(pnlMoney(asset.net_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT'))}
          </tr>
        `).join('') : `<tr><td colspan="8">Noch keine Replay-Historie.</td></tr>`;
      }
    }
    function replayMemoryFromHistoryForSymbol(symbol) {
      const clean = String(symbol || '').toUpperCase();
      return lastReplayHistoryData?.memory_test_by_symbol?.[clean] || lastReplayHistoryData?.memory_test || null;
    }
    function replayRunToPreviewData(run) {
      const summary = run?.summary || {};
      return {
        mode: 'replay_history_run',
        symbol: run?.symbol,
        resolution: run?.resolution,
        limit: run?.limit,
        warmup: run?.warmup,
        summary,
        frames: [],
        replay_trades: run?.trade_results || [],
        memory_test: replayMemoryFromHistoryForSymbol(run?.symbol) || {},
      };
    }
    function showReplayHistoryRun(runId) {
      const run = (lastReplayHistoryData?.runs || []).find(item => String(item.id) === String(runId));
      if (!run) return;
      lastReplayPreviewData = replayRunToPreviewData(run);
      const asset = document.getElementById('replayAsset');
      if (asset && run.symbol) asset.value = run.symbol;
      renderReplaySummaryFromData(lastReplayPreviewData);
      renderReplayRows(lastReplayPreviewData);
      renderReplayMemoryTest(lastReplayPreviewData);
      switchReplayTab('overview');
    }
    function renderReplaySummaryFromData(data) {
      const summary = document.getElementById('replaySummary');
      if (!summary) return;
      const s = data?.summary || {};
      summary.className = 'replaySummaryGrid';
      const replayCards = [
        { label: 'Replay', headline: `${escapeHtml(data?.symbol || '-')} · ${timeframeLabel(data?.resolution)}`, subline: `${fmt(s.frames, 0)} Frames · gespeichert` },
        { label: 'Gate', stats: [['Candidates', fmt(s.candidates, 0)], ['OK', fmt(s.gate_allowed, 0)], ['Block', fmt(s.gate_blocked, 0)]] },
        { label: 'Trades', stats: [['Created', fmt(s.replay_created, 0)], ['Closed', fmt(s.replay_closed, 0)], ['Open', fmt(s.replay_open, 0)]] },
        { label: 'Ergebnis', stats: [['TP', fmt(s.replay_tp, 0)], ['SL', fmt(s.replay_sl, 0)], ['Expired', fmt(s.replay_expired, 0)]] },
        { label: 'Performance', stats: [['Winrate', pct(s.replay_win_rate)], ['Sum R', fmt(s.replay_sum_r)], ['Expectancy', fmt(s.replay_expectancy_r)]] },
        { label: 'PnL', stats: [['Gross', pnlMoney(s.replay_gross_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')], ['Fees', pnlMoney(s.replay_estimated_fees_usd, latestConfig?.replay_pnl_currency || 'USDT')], ['Netto', pnlMoney(s.replay_net_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')]] },
        { label: 'Qualität', stats: [['Profit Factor', fmt(s.replay_profit_factor)], ['Net PF', fmt(s.replay_net_profit_factor_usd)], ['Max Drawdown', `${fmt(s.replay_max_drawdown_r)}R`]] },
        { label: 'Risiko', stats: [['DD USDT', pnlMoney(s.replay_max_drawdown_usd, latestConfig?.replay_pnl_currency || 'USDT')], ['Best Serie', pnlMoney(s.replay_best_pnl_series_usd, latestConfig?.replay_pnl_currency || 'USDT')], ['Worst Serie', pnlMoney(s.replay_worst_pnl_series_usd, latestConfig?.replay_pnl_currency || 'USDT')], ['BE Winrate', pct(s.replay_break_even_win_rate)]] },
      ];
      summary.innerHTML = replayCards.map((card) => `
        <div class="replayMiniCard">
          <div class="label">${card.label}</div>
          ${card.headline ? `<div class="replayMiniHeadline">${card.headline}</div>` : ''}
          ${card.subline ? `<div class="replayMiniSubline">${card.subline}</div>` : ''}
          ${card.stats ? `<div class="replayStatList">${card.stats.map(([statLabel, statValue]) => `<div class="replayStatRow"><div class="replayStatLabel">${statLabel}</div><div class="replayStatValue">${statValue}</div></div>`).join('')}</div>` : ''}
        </div>
      `).join('');
    }
    function replayRunMetric(run, key) {
      const summary = run?.summary || {};
      const value = Number(summary[key]);
      return Number.isFinite(value) ? value : null;
    }
    function replayRunBestWorstMap(runs) {
      const closedRuns = (runs || []).filter(run => Number(replayRunMetric(run, 'replay_closed')) > 0);
      const result = { bestId: null, worstId: null };
      if (!closedRuns.length) return result;
      const score = run => {
        const pf = replayRunMetric(run, 'replay_profit_factor');
        const sumR = replayRunMetric(run, 'replay_sum_r') ?? 0;
        const dd = replayRunMetric(run, 'replay_max_drawdown_r') ?? 0;
        const expectancy = replayRunMetric(run, 'replay_expectancy_r') ?? 0;
        return [pf === null ? -999 : pf, sumR, expectancy, -dd];
      };
      const compare = (a, b) => {
        const sa = score(a);
        const sb = score(b);
        for (let i = 0; i < sa.length; i += 1) {
          if (sa[i] !== sb[i]) return sa[i] - sb[i];
        }
        return Number(a.created_at || 0) - Number(b.created_at || 0);
      };
      const sorted = closedRuns.slice().sort(compare);
      result.worstId = sorted[0]?.id || null;
      result.bestId = sorted[sorted.length - 1]?.id || null;
      return result;
    }
    function replayRunMark(run, markers) {
      const id = String(run?.id || '');
      if (id && id === String(markers.bestId || '')) return '<span class="replayRunMark best">BEST</span>';
      if (id && id === String(markers.worstId || '')) return '<span class="replayRunMark worst">LOW</span>';
      return '<span class="replayRunMark">RUN</span>';
    }
    function renderReplayHistory(history) {
      lastReplayHistoryData = history || {};
      const selectedSymbol = replaySelectedSymbol();
      const allRuns = (history?.runs || []).slice().reverse();
      const runs = allRuns.filter(run => String(run.symbol || '').toUpperCase() === String(selectedSymbol).toUpperCase());
      const markers = replayRunBestWorstMap(runs);
      const summary = document.getElementById('replayHistorySummary');
      const rows = document.getElementById('replayHistoryRows');
      if (summary) {
        const assetCount = (history?.asset_stats || []).length;
        const bestRun = runs.find(run => String(run.id) === String(markers.bestId || ''));
        const worstRun = runs.find(run => String(run.id) === String(markers.worstId || ''));
        summary.innerHTML = `
          <div class="replayHistorySummaryCompact">
            <div class="replayHistorySummaryMain">${escapeHtml(selectedSymbol)} · ${runs.length} Läufe · ${assetCount} Assets</div>
            <div class="replayHistorySummarySub">Best: ${bestRun ? `${pnlMoney(bestRun.summary?.replay_net_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')} · ${fmt(bestRun.summary?.replay_sum_r)}R` : '-'} · Low: ${worstRun ? `${pnlMoney(worstRun.summary?.replay_net_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')} · DD ${pnlMoney(worstRun.summary?.replay_max_drawdown_usd, latestConfig?.replay_pnl_currency || 'USDT')}` : '-'}</div>
          </div>`;
      }
      if (rows) {
        rows.innerHTML = runs.length ? runs.map(run => {
          const s = run.summary || {};
          const markerClass = String(run.id) === String(markers.bestId || '') ? 'best' : String(run.id) === String(markers.worstId || '') ? 'worst' : '';
          return `<tr class="replayHistoryRow ${markerClass}">
            ${td(replayRunMark(run, markers))}
            ${td(`<div class="mainCell">${escapeHtml(fmt(run.symbol))} · ${timeframeLabel(run.resolution)}</div><div class="subCell">${escapeHtml(fmt(run.created_at_utc))} · ${fmt(s.frames, 0)} Frames</div>`)}
            ${td(`<div class="num">${fmt(s.replay_created, 0)}</div><div class="subCell">closed ${fmt(s.replay_closed, 0)}</div>`)}
            ${td(`<div class="num">${pct(s.replay_win_rate)}</div>`)}
            ${td(`<div class="num">${fmt(s.replay_sum_r)}</div>`)}
            ${td(`<div class="num">${pnlMoney(s.replay_net_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')}</div><div class="subCell">Fees ${pnlMoney(s.replay_estimated_fees_usd, latestConfig?.replay_pnl_currency || 'USDT')}</div>`)}
            ${td(`<div class="num">${fmt(s.replay_profit_factor)}</div>`)}
            ${td(`<div class="num">${fmt(s.replay_max_drawdown_r)}R</div><div class="subCell">${pnlMoney(s.replay_max_drawdown_usd, latestConfig?.replay_pnl_currency || 'USDT')}</div>`)}
            ${td(`<div class="num">${pct(s.replay_break_even_win_rate)}</div><div class="subCell">BE Win</div>`)}
            ${td(`<button class="replayRunButton" type="button" data-replay-run="${escapeHtml(run.id)}">Anzeigen</button>`)}
          </tr>`;
        }).join('') : `<tr><td colspan="10">Keine gespeicherten Replay-Läufe für ${escapeHtml(selectedSymbol)}.</td></tr>`;
        rows.querySelectorAll('[data-replay-run]').forEach(button => {
          button.addEventListener('click', () => showReplayHistoryRun(button.dataset.replayRun));
        });
      }
      renderReplayAssetComparison(history);
      if (!lastReplayPreviewData || String(lastReplayPreviewData.symbol || '').toUpperCase() !== String(selectedSymbol).toUpperCase()) {
        const latestRun = runs[0];
        if (latestRun) {
          lastReplayPreviewData = replayRunToPreviewData(latestRun);
          renderReplaySummaryFromData(lastReplayPreviewData);
          renderReplayRows(lastReplayPreviewData);
          renderReplayMemoryTest(lastReplayPreviewData);
        } else {
          renderReplayMemoryTest({ memory_test: replayMemoryFromHistoryForSymbol(selectedSymbol) });
        }
      } else if (!lastReplayPreviewData?.memory_test?.preview_rules?.length) {
        const historyMemory = replayMemoryFromHistoryForSymbol(selectedSymbol);
        if (historyMemory) {
          lastReplayPreviewData.memory_test = historyMemory;
          renderReplayMemoryTest(lastReplayPreviewData);
        }
      }
    }
    async function loadReplayHistory() {
      try {
        const response = await fetch('/api/replay-history', { cache: 'no-store' });
        const history = await response.json();
        if (!response.ok || history.error) throw new Error(history.error || 'Replay-Historie nicht verfügbar');
        renderReplayHistory(history);
      } catch (error) {
        const summary = document.getElementById('replayHistorySummary');
        if (summary) summary.textContent = String(error.message || error);
      }
    }
    async function clearReplayHistory(symbol=null) {
      const selectedSymbol = symbol === null ? null : replaySelectedSymbol();
      const label = selectedSymbol ? `${selectedSymbol}` : 'alle Assets';
      if (!window.confirm(`Replay-Historie löschen: ${label}?`)) return;
      const response = await fetch('/api/replay-history/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: selectedSymbol }),
      });
      const result = await response.json();
      if (!response.ok || result.error) throw new Error(result.error || 'Historie konnte nicht gelöscht werden');
      lastReplayPreviewData = null;
      renderReplayHistory(result.history);
    }
    async function runReplayPreview() {
      if (replayRequestRunning) return;
      replayRequestRunning = true;
      const startButton = document.getElementById('runReplayPreview');
      const status = document.getElementById('replayStatus');
      const rows = document.getElementById('replayRows');
      const summary = document.getElementById('replaySummary');
      if (startButton) {
        startButton.disabled = true;
        startButton.textContent = 'Replay läuft...';
      }
      if (status) {
        status.textContent = 'Replay läuft... große Tests werden kompakt berechnet.';
        status.className = 'controlStatus warn';
      }
      try {
        const symbol = document.getElementById('replayAsset')?.value || (latestConfig?.symbols || [])[0] || 'BTCUSDT';
        const resolution = document.getElementById('replayTf')?.value || latestConfig?.signal_timeframe_seconds || 300;
        const rawSteps = Number(document.getElementById('replaySteps')?.value || 250);
        const maxSteps = Number(latestConfig?.replay_max_steps || 750);
        const steps = Math.max(5, Math.min(rawSteps, maxSteps));
        const limit = Math.min(Number(latestConfig?.replay_kline_limit_max || 1000), Math.max(Number(latestConfig?.kline_limit || 500), steps + 160));
        if (document.getElementById('replaySteps')) document.getElementById('replaySteps').value = steps;
        const response = await fetch(`/api/replay-preview?symbol=${encodeURIComponent(symbol)}&resolution=${encodeURIComponent(resolution)}&steps=${encodeURIComponent(steps)}&limit=${encodeURIComponent(limit)}`, { cache: 'no-store' });
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || 'Replay fehlgeschlagen');
        lastReplayPreviewData = data;
        const s = data.summary || {};
        if (summary) {
          summary.className = 'replaySummaryGrid';
          const replayCards = [
            {
              label: 'Replay',
              headline: `${escapeHtml(data.symbol)} · ${timeframeLabel(data.resolution)}`,
              subline: `${fmt(s.frames, 0)} Frames · ${fmt(s.available_candles, 0)} Kerzen geladen`,
            },
            {
              label: 'Brain',
              stats: [
                ['Long', fmt(s.brain_long ?? s.long_bias, 0)],
                ['Short', fmt(s.brain_short ?? s.short_bias, 0)],
                ['Wait', fmt(s.brain_wait ?? s.wait, 0)],
                ['Blocked', fmt(s.brain_blocked ?? s.blocked, 0)],
              ],
            },
            {
              label: 'CEO',
              stats: [
                ['Long', fmt(s.ceo_long, 0)],
                ['Short', fmt(s.ceo_short, 0)],
                ['Wait', fmt(s.ceo_wait, 0)],
                ['Blocked', fmt(s.ceo_blocked, 0)],
              ],
            },
            {
              label: 'Gate',
              stats: [
                ['Candidates', fmt(s.candidates, 0)],
                ['OK', fmt(s.gate_allowed, 0)],
                ['Block', fmt(s.gate_blocked, 0)],
              ],
            },
            {
              label: 'Trades',
              stats: [
                ['Created', fmt(s.replay_created, 0)],
                ['Pending', fmt(s.replay_pending, 0)],
                ['Open', fmt(s.replay_open, 0)],
              ],
            },
            {
              label: 'Ergebnis',
              stats: [
                ['TP', fmt(s.replay_tp, 0)],
                ['SL', fmt(s.replay_sl, 0)],
                ['Expired', fmt(s.replay_expired, 0)],
              ],
            },
            {
              label: 'Performance',
              stats: [
                ['Winrate', pct(s.replay_win_rate)],
                ['Sum R', fmt(s.replay_sum_r, 0)],
                ['Expectancy', fmt(s.replay_expectancy_r)],
              ],
            },
            {
              label: 'PnL',
              stats: [
                ['Gross', pnlMoney(s.replay_gross_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')],
                ['Fees', pnlMoney(s.replay_estimated_fees_usd, latestConfig?.replay_pnl_currency || 'USDT')],
                ['Netto', pnlMoney(s.replay_net_pnl_usd, latestConfig?.replay_pnl_currency || 'USDT')],
              ],
            },
            {
              label: 'Risiko',
              stats: [
                ['DD USDT', pnlMoney(s.replay_max_drawdown_usd, latestConfig?.replay_pnl_currency || 'USDT')],
                ['Best Serie', pnlMoney(s.replay_best_pnl_series_usd, latestConfig?.replay_pnl_currency || 'USDT')],
                ['Worst Serie', pnlMoney(s.replay_worst_pnl_series_usd, latestConfig?.replay_pnl_currency || 'USDT')],
                ['BE Winrate', pct(s.replay_break_even_win_rate)],
              ],
            },
            {
              label: 'Qualität',
              stats: [
                ['Profit Factor', fmt(s.replay_profit_factor)],
                ['Max Drawdown', `${fmt(s.replay_max_drawdown_r)}R`],
                ['Replay Limit', `${fmt(s.effective_steps, 0)} / ${fmt(s.safe_steps, 0)}`],
                ['Kline Limit', s.kline_limit_fallback ? `${fmt(s.kline_limit, 0)} Fallback` : fmt(s.kline_limit, 0)],
              ],
            },
          ];
          summary.innerHTML = replayCards.map((card) => `
            <div class="replayMiniCard">
              <div class="label">${card.label}</div>
              ${card.headline ? `<div class="replayMiniHeadline">${card.headline}</div>` : ''}
              ${card.subline ? `<div class="replayMiniSubline">${card.subline}</div>` : ''}
              ${card.stats ? `<div class="replayStatList">${card.stats.map(([statLabel, statValue]) => `<div class="replayStatRow"><div class="replayStatLabel">${statLabel}</div><div class="replayStatValue">${statValue}</div></div>`).join('')}</div>` : ''}
            </div>
          `).join('');
        }
        renderReplayMemoryTest(data);
        renderReplayRows(data);
        await loadReplayHistory();
        switchReplayTab('trades');
        if (status) {
          status.textContent = data.summary?.kline_limit_fallback ? 'Replay fertig · Phemex-Limit-Fallback aktiv' : 'Replay fertig';
          status.className = 'controlStatus ok';
        }
      } catch (error) {
        if (status) {
          status.textContent = String(error.message || error);
          status.className = 'controlStatus warn';
        }
      } finally {
        replayRequestRunning = false;
        if (startButton) {
          startButton.disabled = false;
          startButton.textContent = 'Replay starten';
        }
      }
    }
    function setView(view) {
      currentView = view;
      document.getElementById('dashboardView').classList.toggle('hidden', view !== 'dashboard');
      document.getElementById('chartView').classList.toggle('hidden', view !== 'chart');
      document.getElementById('agentView').classList.toggle('hidden', view !== 'agents');
      document.getElementById('agentSetupView')?.classList.toggle('hidden', view !== 'agent_setup');
      document.getElementById('replayView').classList.toggle('hidden', view !== 'replay');
      document.getElementById('chartViewButton').classList.toggle('active', view === 'chart');
      document.getElementById('agentViewButton').classList.toggle('active', view === 'agents');
      document.getElementById('agentSetupViewButton')?.classList.toggle('active', view === 'agent_setup');
      document.getElementById('replayViewButton').classList.toggle('active', view === 'replay');
      document.getElementById('chartViewButton').textContent = view === 'chart' ? 'Bot View' : 'Chart View';
      document.getElementById('agentViewButton').textContent = view === 'agents' ? 'Bot View' : 'Agent Viewer';
      document.getElementById('agentSetupViewButton') && (document.getElementById('agentSetupViewButton').textContent = view === 'agent_setup' ? 'Bot View' : 'Agenten Setup');
      document.getElementById('replayViewButton').textContent = view === 'replay' ? 'Bot View' : 'Replay View';
      if (view === 'chart') {
        window.setTimeout(() => {
          resizeKlineChart();
          loadChartData(true);
        }, 0);
      }
      if (view === 'agents') {
        syncAgentAssetOptions(latestConfig || {});
        renderAgentViewer(latestStatusData || {}, latestConfig || {});
      }
      if (view === 'replay') {
        syncReplayAssetOptions(latestConfig || {});
        renderReplayRuleWeightStatus();
      }
      if (view === 'agent_setup') {
        loadAgentSettings();
      }
    }
    function syncChartAssetOptions(cfg) {
      chartConfig = cfg || chartConfig || {};
      const mode = chartConfig.observer_asset_mode || 'single';
      const activeSymbols = chartConfig.symbols || [];
      const watchlist = chartConfig.watchlist_assets || [];
      const chartAsset = document.getElementById('chartAsset');
      const chartAssetWrap = document.getElementById('chartAssetWrap');
      if (!chartAsset || !chartAssetWrap) return;
      chartAssetWrap.style.display = mode === 'multi' ? 'block' : 'none';
      const allowedSymbols = mode === 'multi' ? activeSymbols : activeSymbols.slice(0, 1);
      const current = chartAsset.value;
      chartAsset.innerHTML = allowedSymbols.map(symbol => {
        const item = watchlist.find(asset => asset.symbol === symbol);
        return `<option value="${symbol}">${item ? item.label : symbol}</option>`;
      }).join('');
      if (mode === 'multi' && allowedSymbols.includes(current)) {
        chartAsset.value = current;
      } else if (allowedSymbols.length) {
        chartAsset.value = allowedSymbols[0];
      }
    }
    function activeChartSymbol() {
      const cfg = chartConfig || {};
      const activeSymbols = cfg.symbols || [];
      if ((cfg.observer_asset_mode || 'single') === 'multi') {
        return document.getElementById('chartAsset').value || activeSymbols[0] || 'BTCUSDT';
      }
      return activeSymbols[0] || 'BTCUSDT';
    }
    function syncAgentAssetOptions(cfg) {
      const activeSymbols = (cfg?.symbols || latestConfig?.symbols || []);
      const watchlist = (cfg?.watchlist_assets || latestConfig?.watchlist_assets || []);
      const agentAsset = document.getElementById('agentAsset');
      if (!agentAsset) return;
      const current = agentAsset.value || selectedAgentAsset || selectedAsset;
      agentAsset.innerHTML = activeSymbols.map(symbol => {
        const item = watchlist.find(asset => asset.symbol === symbol);
        return `<option value="${escapeHtml(symbol)}">${escapeHtml(item ? item.label : symbol)}</option>`;
      }).join('');
      if (activeSymbols.includes(current)) {
        agentAsset.value = current;
      } else if (activeSymbols.length) {
        agentAsset.value = activeSymbols[0];
      }
      selectedAgentAsset = agentAsset.value || selectedAgentAsset || selectedAsset || activeSymbols[0] || 'BTCUSDT';
    }
    function activeAgentSymbol() {
      return document.getElementById('agentAsset')?.value || selectedAgentAsset || selectedAsset || (latestConfig?.symbols || [])[0] || 'BTCUSDT';
    }
    function llmLayerForSymbol(data, cfg, symbol) {
      const activeSymbol = symbol || selectedAgentAsset || selectedAsset || (cfg?.symbols || [])[0] || 'BTCUSDT';
      const board = data?.cycle?.agents?.[activeSymbol] || data?.cycle?.symbols?.[activeSymbol]?.agents || null;
      const brainState = data?.cycle?.brains?.[activeSymbol] || data?.cycle?.symbols?.[activeSymbol]?.brain || null;
      const layer = board?.llm_layer || brainState?.llm_layer || null;
      if (layer) return layer;
      const enabled = !!cfg?.brain_llm_layer_enabled && !!cfg?.ollama_enabled;
      return {
        enabled,
        provider: 'ollama',
        model: cfg?.ollama_model || 'qwen2.5:3b',
        role: 'local_trade_auditor',
        verdict: enabled ? 'NO_DATA' : 'NO_DATA',
        confidence_note: '-',
        risk_note: enabled ? 'Wartet auf naechsten Agentenzyklus.' : 'LLM/Ollama ist deaktiviert.',
        conflict_note: '-',
        advice: enabled ? 'Noch kein LLM-Audit im aktuellen Status.' : 'Aktivierung ueber Agent Settings / Ollama Audit.',
        block_hint: false,
      };
    }
    function renderLlmAuditContent(llmLayer, cfg) {
      const layer = llmLayer || llmLayerForSymbol(latestStatusData || {}, cfg || latestConfig || {}, selectedAgentAsset || selectedAsset);
      const enabled = !!layer?.enabled;
      const provider = layer?.provider || 'ollama';
      const model = layer?.model || cfg?.ollama_model || 'qwen2.5:3b';
      const verdict = layer?.verdict || 'NO_DATA';
      const blockHint = !!layer?.block_hint;
      const riskNote = layer?.risk_note && layer.risk_note !== '-' ? layer.risk_note : (layer?.message || '-');
      const conflictNote = layer?.conflict_note && layer.conflict_note !== '-' ? layer.conflict_note : '-';
      const auditNote = layer?.advice && layer.advice !== '-' ? layer.advice : (layer?.message || '-');
      return `<div class="llmAuditGrid">
        <div class="llmAuditItem"><div class="label">Status</div><div class="llmBadge ${enabled ? 'active' : 'inactive'}">${enabled ? 'Aktiv' : 'Aus'}</div></div>
        <div class="llmAuditItem"><div class="label">Provider</div><div class="llmAuditValue">${escapeHtml(provider)}</div></div>
        <div class="llmAuditItem"><div class="label">Modell</div><div class="llmAuditValue">${escapeHtml(model)}</div></div>
        <div class="llmAuditItem"><div class="label">Verdict</div><div class="llmVerdict ${escapeHtml(String(verdict).toLowerCase())}">${escapeHtml(verdict)}</div></div>
        <div class="llmAuditItem fullWidth"><div class="label">Risiko-Hinweis</div><div class="llmNote">${escapeHtml(riskNote)}</div></div>
        <div class="llmAuditItem fullWidth"><div class="label">Konflikt-Hinweis</div><div class="llmNote">${escapeHtml(conflictNote)}</div></div>
        <div class="llmAuditItem fullWidth"><div class="label">Audit-Hinweis</div><div class="llmNote">${escapeHtml(auditNote)}</div></div>
        <div class="llmAuditItem"><div class="label">Block Hint</div><div class="llmBadge ${blockHint ? 'warn' : 'inactive'}">${blockHint ? 'Hinweis' : 'Nein'}</div></div>
      </div>`;
    }
    function llmAuditEnabled(cfg) {
      return !!cfg?.brain_llm_layer_enabled && !!cfg?.ollama_enabled;
    }
    function renderLlmAuditSummary(data, cfg) {
      const panel = document.getElementById('llmAuditSummary');
      const section = document.getElementById('llmAuditSummarySection') || panel?.closest('section');
      if (!panel) return;
      if (!llmAuditEnabled(cfg)) {
        panel.innerHTML = '';
        if (section) section.style.display = 'none';
        return;
      }
      if (section) section.style.display = '';
      const activeSymbols = cfg?.symbols || [];
      const symbol = selectedAgentAsset || selectedAsset || activeSymbols[0] || 'BTCUSDT';
      panel.innerHTML = renderLlmAuditContent(llmLayerForSymbol(data, cfg, symbol), cfg);
    }
    function signalClass(signal) {
      const value = String(signal || 'NEUTRAL').toLowerCase();
      return value === 'long' ? 'long' : value === 'short' ? 'short' : 'neutral';
    }
    function agentRole(report, ceo=false) {
      if (ceo) return 'ceo';
      if (report?.role) return String(report.role);
      const name = String(report?.agent_name || '').toLowerCase();
      const fn = String(report?.function || '').toLowerCase();
      if (name.includes('risk') || name.includes('gate') || fn.includes('risk') || fn.includes('gate') || fn.includes('pipeline')) return 'risk';
      if (name.includes('bos') || name.includes('choch') || name.includes('box') || name.includes('support') || name.includes('resistance') || name.includes('swing') || name.includes('hh')) return 'structure';
      if (name.includes('hma') || name.includes('sma') || name.includes('triple') || name.includes('macd') || name.includes('mfi') || name.includes('volume')) return 'momentum';
      return 'other';
    }
    function agentRoleLabel(role) {
      const map = { structure:'Struktur', momentum:'Momentum', risk:'Risk / Pipeline', ceo:'CEO / Brain', other:'Sonstige' };
      return map[role] || 'Sonstige';
    }
    function agentSortValue(report, mode) {
      const roleOrder = { structure:1, momentum:2, risk:3, ceo:4, other:5 };
      const signalOrder = { LONG:1, SHORT:2, NEUTRAL:3 };
      if (mode === 'role') return roleOrder[agentRole(report)] || 9;
      if (mode === 'blocking') return report?.blocking ? 0 : 1;
      if (mode === 'signal') return signalOrder[String(report?.signal || 'NEUTRAL').toUpperCase()] || 9;
      return -Number(report?.score || 0);
    }
    function sortAgentReports(reports) {
      const mode = document.getElementById('agentSortMode')?.value || agentSortMode || 'score_desc';
      return reports.slice().sort((a, b) => {
        const primary = agentSortValue(a, mode) - agentSortValue(b, mode);
        if (primary !== 0) return primary;
        return Number(b?.score || 0) - Number(a?.score || 0);
      });
    }
    function filterAgentReportsByRole(reports, role) {
      if (!role || role === 'all') return reports;
      return reports.filter(report => agentRole(report) === role);
    }
    function agentQualityProfile(report) {
      const q = report?.details?.quality_profile || {};
      const score = Math.max(0, Math.min(100, Number(q.reliability_score ?? report?.score ?? 0)));
      const quality = String(q.quality || (report?.blocking ? 'BLOCK' : report?.conflict ? 'WEAK' : score >= 72 ? 'STRONG' : score >= 55 ? 'OK' : 'WEAK')).toUpperCase();
      return {
        quality,
        data: q.data_quality || 'ok',
        strength: q.signal_strength || (Number(report?.score || 0) >= 72 ? 'strong' : Number(report?.score || 0) >= 50 ? 'medium' : 'weak'),
        reliability: score,
      };
    }
    function agentQualityLabel(quality) {
      const map = { STRONG:'stark', OK:'ok', WEAK:'schwach', BLOCK:'block', OFFLINE:'offline' };
      return map[String(quality || '').toUpperCase()] || String(quality || '-').toLowerCase();
    }
    function roleGroupFromReports(reports, role) {
      const items = (reports || []).filter(report => agentRole(report) === role);
      const longItems = items.filter(report => String(report?.signal || '').toUpperCase() === 'LONG');
      const shortItems = items.filter(report => String(report?.signal || '').toUpperCase() === 'SHORT');
      const longScore = longItems.reduce((sum, report) => sum + Number(report?.score || 0), 0);
      const shortScore = shortItems.reduce((sum, report) => sum + Number(report?.score || 0), 0);
      const blocking = items.filter(report => report?.blocking).length;
      const consensus = longScore > shortScore && longItems.length ? 'LONG' : shortScore > longScore && shortItems.length ? 'SHORT' : 'NEUTRAL';
      return { role, items, longItems, shortItems, longScore, shortScore, blocking, consensus };
    }
    function roleGroupFromCeoDetails(ceo, reports, role) {
      const group = ceo?.details?.role_groups?.[role];
      if (group) return group;
      const fallback = roleGroupFromReports(reports, role);
      return {
        role,
        long_count: fallback.longItems.length,
        short_count: fallback.shortItems.length,
        neutral_count: Math.max(0, fallback.items.length - fallback.longItems.length - fallback.shortItems.length),
        long_score: fallback.longScore,
        short_score: fallback.shortScore,
        blocking_count: fallback.blocking,
        consensus: fallback.consensus,
        strength: Math.max(fallback.longScore, fallback.shortScore),
        agents: fallback.items.map(report => report.agent_name || '-'),
      };
    }
    function roleConsensusText(group) {
      const consensus = String(group?.consensus || 'NEUTRAL').toUpperCase();
      const long = `${fmt(group?.long_count, 0)} / ${fmt(group?.long_score, 0)}`;
      const short = `${fmt(group?.short_count, 0)} / ${fmt(group?.short_score, 0)}`;
      return `${consensus} · L ${long} · S ${short}`;
    }
    function renderAgentDecisionCenter(board, reports, brain, gate, tradePlan) {
      const ceo = board?.ceo || {};
      const structure = roleGroupFromCeoDetails(ceo, reports, 'structure');
      const momentum = roleGroupFromCeoDetails(ceo, reports, 'momentum');
      const risk = roleGroupFromCeoDetails(ceo, reports, 'risk');
      const breakdown = brain?.details?.score_breakdown || tradePlan?.features?.brain_score_breakdown || board?.score_breakdown || {};
      const gateAllowed = gate?.trade_allowed === true;
      const gateLabel = gate ? (gateAllowed ? 'OK' : 'BLOCK') : 'pending';
      const gateReason = gate?.reason || (gateAllowed ? 'trade_allowed' : '-');
      const decision = ceo?.details?.decision || ceo?.message?.split(':')?.[0] || '-';
      const brainScore = Number(brain?.score ?? breakdown.final_score ?? 0);
      const minBrainScore = Number(breakdown.min_score ?? latestConfig?.brain_min_score ?? 0);
      const blockingReports = (reports || []).filter(report => report?.blocking);
      const candidateState = tradePlan ? 'Plan vorhanden' : 'kein Plan';
      const priorityBlocked = blockingReports.length > 0 || (gate && !gateAllowed);
      const priorityLabel = priorityBlocked ? 'Blockierend' : tradePlan && gateAllowed ? 'Freigegeben' : 'Beobachten';
      const priorityClass = priorityBlocked ? 'bad' : tradePlan && gateAllowed ? 'good' : 'watch';
      const visibleAgents = (reports || [])
        .filter(report => isRiskPipelineReport(report) || agentRole(report) === 'momentum')
        .slice()
        .sort((a, b) => Number(!!b?.blocking) - Number(!!a?.blocking) || Number(a?.score || 0) - Number(b?.score || 0))
        .slice(0, 4);
      const agentNote = report => {
        const quality = agentQualityProfile(report);
        if (report?.blocking) return ['Blockierender Agent', 'bad'];
        if (String(quality.quality).toUpperCase() === 'OFFLINE') return ['Agent offline', 'bad'];
        if (String(quality.quality).toUpperCase() === 'WEAK') return ['Schwache Daten-/Signalqualität', 'warn'];
        return [report?.message || 'Daten ok', 'muted'];
      };
      const initials = name => String(name || '-')
        .split(/\s+|\//)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part.charAt(0).toUpperCase())
        .join('') || '-';
      const statusChip = (value, cls='neutral') => `<span class="priorityChip ${escapeHtml(cls)}">${escapeHtml(value)}</span>`;
      const summaryRows = [
        ['shield', 'Blockierende Priorität', priorityLabel, priorityClass],
        ['db', 'Datenqualität', `${fmt(blockingReports.length, 0)} ${blockingReports.length ? 'blockierend' : 'ok'}`, blockingReports.length ? 'bad' : 'good'],
        ['signal', 'Agent Signal', priorityBlocked ? 'blockiert' : 'beobachten', priorityBlocked ? 'bad' : 'watch'],
        ['user', 'CEO', `${ceo?.signal || 'NEUTRAL'} · ${fmt(ceo?.score, 0)}`, signalClass(ceo?.signal)],
        ['brain', 'Brain Score', `${fmt(brainScore, 0)} / min ${fmt(minBrainScore, 0)}`, brainScore >= minBrainScore ? 'good' : 'warn'],
        ['gate', 'Economic Gate', gate ? `${gateLabel}${gateAllowed ? '' : ' · ' + gateReason}` : 'pending', gateAllowed ? 'good' : gate ? 'bad' : 'watch'],
      ];
      const agentRows = visibleAgents.map(report => {
        const [note, noteClass] = agentNote(report);
        const role = agentRoleLabel(agentRole(report));
        const signal = String(report?.signal || 'NEUTRAL').toUpperCase();
        return `<div class="priorityAgentRow">
          <div class="priorityAgentName"><span class="priorityAvatar">${escapeHtml(initials(report?.agent_name))}</span><strong>${escapeHtml(report?.agent_name || '-')}</strong></div>
          <div>${escapeHtml(role)}</div>
          <div>${statusChip(signal, signal.toLowerCase())}</div>
          <div><strong>${fmt(report?.score, 0)}</strong></div>
          <div><span class="priorityNote ${escapeHtml(noteClass)}">${escapeHtml(note)}</span></div>
        </div>`;
      }).join('') || '<div class="priorityEmpty">Keine Risk-/Momentum-Agenten sichtbar.</div>';
      return `<div class="agentDecisionCenter priorityDecisionCenter">
        <div class="priorityHeader">
          <div class="priorityTitle">Prioritätsansicht</div>
          <div class="priorityHeaderChips">
            ${statusChip(decision || 'Beobachten', 'watch')}
            ${statusChip(latestConfig?.observer_enabled ? 'aktiv' : 'gestoppt', latestConfig?.observer_enabled ? 'good' : 'watch')}
            ${statusChip(`${fmt(blockingReports.length, 0)}x`, blockingReports.length ? 'bad' : 'good')}
            ${statusChip(candidateState, tradePlan ? 'good' : 'watch')}
          </div>
        </div>
        <div class="priorityGrid">
          <div class="prioritySummaryCard">
            ${summaryRows.map(([icon, label, value, cls]) => `<div class="prioritySummaryRow ${escapeHtml(cls)}">
              <span class="priorityIcon ${escapeHtml(icon)}"></span>
              <span>${escapeHtml(label)}</span>
              <strong>${String(value || '').includes('NEUTRAL') || String(value || '').includes('LONG') || String(value || '').includes('SHORT') ? String(value).replace(/^(LONG|SHORT|NEUTRAL)/, match => statusChip(match, match.toLowerCase())) : escapeHtml(value)}</strong>
            </div>`).join('')}
          </div>
          <div class="priorityAgentTable">
            <div class="priorityAgentHead"><span>Agent</span><span>Fokus</span><span>Status</span><span>Score</span><span>Hinweis</span></div>
            ${agentRows}
          </div>
        </div>
      </div>`;
    }
    function renderBrainScoreBreakdown(brain, candidate) {
      const breakdown = brain?.details?.score_breakdown || candidate?.features?.brain_score_breakdown || {};
      if (!Object.keys(breakdown).length) return '';
      const items = [
        ['Richtung', `${fmt(breakdown.direction)} · Gap ${fmt(breakdown.score_gap)}`],
        ['Basis', fmt(breakdown.raw_direction_average)],
        ['Memory', `${Number(breakdown.memory_adjustment ?? 0) >= 0 ? '+' : ''}${fmt(breakdown.memory_adjustment ?? 0)} · Count ${fmt(breakdown.memory_count, 0)}`],
        ['Replay', `${Number(breakdown.replay_adjustment ?? 0) >= 0 ? '+' : ''}${fmt(breakdown.replay_adjustment ?? 0)} · ${fmt(breakdown.replay_rule_quality)}`],
        ['Datenqualität', `-${fmt(breakdown.quality_penalty ?? 0)} · schwach ${fmt(breakdown.weak_count ?? 0)} · offline ${fmt(breakdown.offline_count ?? 0)}`],
        ['Final', `${fmt(breakdown.final_score, 0)} / min ${fmt(breakdown.min_score, 0)}`],
      ];
      return `<div class="agentScoreBreakdown">${items.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('')}</div>`;
    }
    function renderAgentRoleGroup(title, reports, role) {
      if (!reports.length) return '';
      return `<div class="agentRoleGroup ${escapeHtml(role)}"><div class="agentRoleGroupTitle">${escapeHtml(title)} <span>${fmt(reports.length, 0)} Agenten</span></div><div class="agentGrid">${reports.map(report => renderAgentCard(report)).join('')}</div></div>`;
    }
    function agentConflictBucket(reports) {
      const active = (reports || []).filter(report => {
        const signal = String(report?.signal || 'NEUTRAL').toUpperCase();
        return signal === 'LONG' || signal === 'SHORT' || report?.conflict || report?.blocking;
      });
      const longReports = active.filter(report => String(report?.signal || '').toUpperCase() === 'LONG');
      const shortReports = active.filter(report => String(report?.signal || '').toUpperCase() === 'SHORT');
      const conflictReports = active.filter(report => report?.conflict || (longReports.length > 0 && shortReports.length > 0));
      const blockingReports = active.filter(report => report?.blocking);
      return { active, longReports, shortReports, conflictReports, blockingReports };
    }
    function agentConflictRow(report) {
      const role = agentRole(report);
      const signal = String(report?.signal || 'NEUTRAL').toUpperCase();
      const score = Math.max(0, Math.min(100, Number(report?.score || 0)));
      const flags = [report?.blocking ? 'BLOCKING' : '', report?.conflict ? 'KONFLIKT' : ''].filter(Boolean).join(' · ');
      return `<div class="agentConflictRow ${signal.toLowerCase()}">
        <span>${escapeHtml(report?.agent_name || '-')}</span>
        <span>${escapeHtml(agentRoleLabel(role))}</span>
        <span>${escapeHtml(signal)} · ${score}</span>
        <span>${escapeHtml(flags || '-')}</span>
      </div>`;
    }
    function renderAgentConflictPanel(reports, ceo=null) {
      const roles = [
        ['structure', 'Struktur'],
        ['momentum', 'Momentum'],
        ['risk', 'Risk / Pipeline'],
        ['signal', 'Sonstige'],
      ];
      const matrixRows = roles.map(([role, label]) => {
        const group = roleGroupFromCeoDetails(ceo || {}, reports, role);
        const consensus = String(group.consensus || 'NEUTRAL').toLowerCase();
        const agentNames = (group.agents || []).slice(0, 4).join(', ') || '-';
        return `<div class="agentMatrixRow ${escapeHtml(consensus)}">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(group.consensus || 'NEUTRAL')}</strong>
          <span>L ${fmt(group.long_count, 0)} / ${fmt(group.long_score, 0)}</span>
          <span>S ${fmt(group.short_count, 0)} / ${fmt(group.short_score, 0)}</span>
          <span>Block ${fmt(group.blocking_count, 0)}</span>
          <small>${escapeHtml(agentNames)}</small>
        </div>`;
      }).join('');
      const bucket = agentConflictBucket(reports);
      const hasDirectionConflict = bucket.longReports.length > 0 && bucket.shortReports.length > 0;
      const panelClass = bucket.blockingReports.length ? 'blocked' : hasDirectionConflict ? 'conflict' : 'neutral';
      const rows = bucket.active
        .slice()
        .sort((a, b) => Number(!!b?.blocking) - Number(!!a?.blocking) || Number(!!b?.conflict) - Number(!!a?.conflict) || Number(b?.score || 0) - Number(a?.score || 0))
        .map(agentConflictRow)
        .join('');
      const summary = `LONG ${bucket.longReports.length} · SHORT ${bucket.shortReports.length} · Blocking ${bucket.blockingReports.length} · Konflikte ${bucket.conflictReports.length}`;
      return `<div class="agentConflictPanel ${panelClass}">
        <div class="agentConflictTitle">Konflikt-Matrix</div>
        <div class="agentConflictSummary">${escapeHtml(summary)}</div>
        <div class="agentConflictMatrix">${matrixRows}</div>
        ${rows ? `<div class="agentConflictRows">${rows}</div>` : '<div class="agentTextBox">Keine aktiven LONG/SHORT- oder Blocking-Konflikte.</div>'}
      </div>`;
    }
    function ceoDecisionParts(ceo, reports, brain, gate) {
      const signal = String(ceo?.signal || 'NEUTRAL').toUpperCase();
      const message = String(ceo?.message || '-');
      const reads = String(ceo?.reads || '-');
      const blockingReports = (reports || []).filter(report => report?.blocking);
      const longReports = (reports || []).filter(report => String(report?.signal || '').toUpperCase() === 'LONG');
      const shortReports = (reports || []).filter(report => String(report?.signal || '').toUpperCase() === 'SHORT');
      const gateAllowed = gate?.trade_allowed === true;
      const gateReason = gate?.reason || (gateAllowed ? 'trade_allowed' : '-');
      const decisionLabel = message.includes('BLOCKED') || blockingReports.length ? 'BLOCKED'
        : signal === 'LONG' ? 'LONG_BIAS'
        : signal === 'SHORT' ? 'SHORT_BIAS'
        : 'WAIT';
      return [
        { label:'Entscheidung', value:decisionLabel },
        { label:'CEO liest', value:reads },
        { label:'Richtung', value:`LONG ${longReports.length} / SHORT ${shortReports.length}` },
        { label:'Blocking', value:blockingReports.length ? blockingReports.map(report => report.agent_name || '-').join(', ') : 'keine Blocking-Agenten' },
        { label:'Brain', value:brain ? `${brain.signal || 'NEUTRAL'} · Score ${fmt(brain.score, 0)}` : 'kein Brain-Report' },
        { label:'Economic Gate', value:gate ? `${gateAllowed ? 'OK' : 'BLOCK'} · ${gateReason}` : 'noch nicht geprüft' },
        { label:'Begründung', value:message },
      ];
    }
    function renderCeoDecisionExplanation(ceo, reports, brain, gate) {
      const parts = ceoDecisionParts(ceo, reports, brain, gate);
      const decision = String(parts[0]?.value || 'WAIT').toLowerCase();
      const rows = parts.map(part => `<div class="ceoExplainRow"><span>${escapeHtml(part.label)}</span><strong>${escapeHtml(part.value)}</strong></div>`).join('');
      return `<div class="ceoExplainPanel ${escapeHtml(decision)}">
        <div class="ceoExplainTitle">CEO-Entscheidung erklärt</div>
        <div class="ceoExplainRows">${rows}</div>
      </div>`;
    }
    function brainDecisionParts(brain, candidate, memoryMatch, gate) {
      const features = candidate?.features || {};
      const gateAllowed = gate?.trade_allowed === true;
      const gateReason = gate?.reason || (gateAllowed ? 'trade_allowed' : '-');
      const memoryCount = memoryMatch?.count ?? features.memory_match_count ?? 0;
      const memoryWinRate = memoryMatch?.win_rate ?? features.memory_win_rate ?? null;
      const memoryAvgR = memoryMatch?.avg_r ?? features.memory_avg_r ?? null;
      const replayRule = features.replay_rule_weight || {};
      const replayRuleEnabled = features.replay_rule_weight_enabled ?? replayRule.enabled ?? false;
      const replayRuleMatched = features.replay_rule_weight_matched ?? replayRule.matched ?? false;
      const replayRuleAdjustment = features.replay_rule_weight_adjustment ?? replayRule.adjustment ?? 0;
      const replayRuleQuality = features.replay_rule_weight_quality ?? replayRule.quality ?? (replayRuleEnabled ? 'WATCH' : 'OFF');
      const replayRuleKey = features.replay_rule_weight_key ?? replayRule.key ?? memoryMatch?.pattern_key ?? candidate?.pattern_key ?? features.brain_pattern_key ?? '-';
      const replayRuleSymbol = features.replay_rule_weight_symbol ?? replayRule.symbol ?? candidate?.symbol ?? '-';
      const replayRuleScope = features.replay_rule_weight_scope ?? replayRule.scope ?? latestConfig?.replay_rule_scope ?? 'asset';
      const replayRuleCount = replayRule.count ?? '-';
      const replayRuleReason = replayRule.reason || (replayRuleMatched ? 'Replay-Regel trifft Pattern-Key.' : replayRuleEnabled ? 'Keine passende Replay-Regel.' : 'Replay-Gewichtung ist deaktiviert.');
      return [
        { label:'Brain Signal', value:brain ? `${brain.signal || 'NEUTRAL'} · Score ${fmt(brain.score, 0)}` : 'kein Brain-Report' },
        { label:'Replay-Lernregel', value:`${replayRuleEnabled ? 'aktiv' : 'aus'} · ${replayRuleMatched ? 'Treffer' : 'kein Treffer'} · ${replayRuleQuality} · ${Number(replayRuleAdjustment) >= 0 ? '+' : ''}${fmt(replayRuleAdjustment, 0)}` },
        { label:'Replay-Key', value:replayRuleKey },
        { label:'Replay-Scope', value:`${replayRuleScope} · ${replayRuleSymbol}` },
        { label:'Replay-Lernregel-Daten', value:`Count ${fmt(replayRuleCount)} · ${replayRuleReason}` },
        { label:'Entry-Methode', value:candidate?.entry_method || features.entry_method || 'kein Candidate' },
        { label:'SL-Methode', value:features.stop_loss_mode || features.sl_method || features.stop_method || 'nicht angegeben' },
        { label:'TP-Methode', value:candidate?.target_method || features.target_method || 'nicht angegeben' },
        { label:'Memory', value:`Matches ${fmt(memoryCount, 0)} · Winrate ${pct(memoryWinRate)} · AvgR ${fmt(memoryAvgR)}` },
        { label:'Pattern', value:memoryMatch?.pattern_key || candidate?.pattern_key || features.brain_pattern_key || '-' },
        { label:'Entry / SL / TP', value:candidate ? `${fmt(candidate.entry_price)} / ${fmt(candidate.sl_price)} / ${fmt(candidate.tp_price)}` : '-' },
        { label:'Economic Gate', value:gate ? `${gateAllowed ? 'OK' : 'BLOCK'} · ${gateReason}` : 'noch nicht geprüft' },
        { label:'Brain Grund', value:brain?.message || candidate?.reason || '-' },
      ];
    }
    function renderBrainDecisionExplanation(brain, candidate, memoryMatch, gate) {
      const parts = brainDecisionParts(brain, candidate, memoryMatch, gate);
      const signal = String(brain?.signal || 'NEUTRAL').toLowerCase();
      const rows = parts.map(part => `<div class="ceoExplainRow"><span>${escapeHtml(part.label)}</span><strong>${escapeHtml(part.value)}</strong></div>`).join('');
      return `<div class="ceoExplainPanel brainExplain ${escapeHtml(signal)}">
        <div class="ceoExplainTitle">Brain-Entscheidung erklärt</div>
        ${renderBrainScoreBreakdown(brain, candidate)}
        <div class="ceoExplainRows">${rows}</div>
      </div>`;
    }
    function renderRiskDetailRows(details) {
      if (!details) return '';
      const active = details.active_trades || {};
      const gate = details.economic_gate || {};
      const broker = details.broker || {};
      const hardBlocks = Array.isArray(details.hard_blocks) ? details.hard_blocks.join(' · ') : '-';
      const warnings = Array.isArray(details.warnings) ? details.warnings.join(' · ') : '-';
      const rows = [
        ['Gate', gate.trade_allowed === true ? 'OK' : gate.trade_allowed === false ? `BLOCK · ${gate.reason || '-'}` : 'pending'],
        ['Broker', broker.allowed === true ? 'OK' : broker.allowed === false ? `BLOCK · ${broker.reason || '-'}` : 'pending'],
        ['Offen', `${fmt(active.total, 0)} gesamt · ${fmt(active.same_asset, 0)} gleiches Asset`],
        ['Korrelation', `${fmt(active.correlation_group)} · gleiche Richtung ${fmt(active.correlated_same_direction, 0)}`],
        ['SL-Distanz', details.risk_fraction === null || details.risk_fraction === undefined ? '-' : `${percentDisplay(details.risk_fraction)} / max ${percentDisplay(details.max_sl_distance_fraction)}`],
        ['RR', `${fmt(details.rr)} / min ${fmt(details.min_rr)}`],
        ['Netto', details.net_profit_fraction === null || details.net_profit_fraction === undefined ? '-' : `${percentDisplay(details.net_profit_fraction)} / min ${percentDisplay(details.min_net_profit_fraction)}`],
        ['Hard Blocks', hardBlocks || '-'],
        ['Warnungen', warnings || '-'],
      ];
      return `<div class="agentRiskDetails">${rows.map(([k, v]) => `<div class="ceoExplainRow"><span>${escapeHtml(k)}</span><strong>${escapeHtml(v)}</strong></div>`).join('')}</div>`;
    }


    function compactAgentInitials(name) {
      const words = String(name || 'Agent').replace(/Agent/gi, '').split(/[^A-Za-z0-9]+/).filter(Boolean);
      return (words.length ? words.map(word => word[0]).join('') : 'A').slice(0, 3).toUpperCase();
    }
    function compactAgentStatusClass(report) {
      const signal = String(report?.signal || 'NEUTRAL').toLowerCase();
      if (report?.blocking) return 'bad';
      if (report?.conflict) return 'warn';
      if (signal === 'long' || signal === 'short') return 'good';
      return 'neutral';
    }
    function compactAgentNote(report) {
      const quality = agentQualityProfile(report);
      if (report?.blocking) return ['Blockierend', 'bad'];
      if (report?.conflict) return ['Konflikt', 'warn'];
      if (String(quality.quality).toUpperCase() === 'OFFLINE') return ['Offline', 'bad'];
      if (String(quality.quality).toUpperCase() === 'WEAK') return ['Schwache Daten', 'warn'];
      return [agentQualityLabel(quality.quality), ''];
    }
    function renderAgentCompactDashboard(board, reports, brain, gate, tradePlan) {
      const activeReports = reports || [];
      const longCount = activeReports.filter(report => report?.signal === 'LONG').length;
      const shortCount = activeReports.filter(report => report?.signal === 'SHORT').length;
      const blockingCount = activeReports.filter(report => report?.blocking).length;
      const weakCount = activeReports.filter(report => String(agentQualityProfile(report).quality).toUpperCase() === 'WEAK').length;
      const offlineCount = activeReports.filter(report => String(agentQualityProfile(report).quality).toUpperCase() === 'OFFLINE').length;
      const avgScore = activeReports.length ? Math.round(activeReports.reduce((sum, report) => sum + Number(report?.score || 0), 0) / activeReports.length) : 0;
      const ceoSignal = board?.ceo?.signal || 'NEUTRAL';
      const brainScore = brain?.score ?? tradePlan?.score ?? '-';
      const gateText = gate?.trade_allowed === true ? 'OK' : gate?.trade_allowed === false ? 'BLOCK' : 'wartet';
      const gateClass = gate?.trade_allowed === true ? 'good' : gate?.trade_allowed === false ? 'bad' : 'neutral';
      const planText = tradePlan ? `${tradePlan.decision || '-'} · Entry ${fmt(tradePlan.entry_price)}` : 'kein Trade-Plan';
      const rows = activeReports.slice(0, 8).map(report => {
        const quality = agentQualityProfile(report);
        const [note, noteCls] = compactAgentNote(report);
        const role = agentRole(report);
        return `<div class="agentCompactRow">
          <div class="agentCompactName"><span class="agentCompactAvatar">${escapeHtml(compactAgentInitials(report?.agent_name))}</span><strong>${escapeHtml(report?.agent_name || '-')}</strong></div>
          <div>${escapeHtml(agentRoleLabel(role))}</div>
          <div><span class="agentCompactBadge ${escapeHtml(compactAgentStatusClass(report))}">${escapeHtml(report?.signal || 'NEUTRAL')}</span></div>
          <div>${fmt(report?.score, 0)}</div>
          <div><span class="agentQualityPill ${escapeHtml(String(quality.quality).toLowerCase())}">${escapeHtml(agentQualityLabel(quality.quality))}</span></div>
          <div class="agentCompactNote ${escapeHtml(noteCls)}">${escapeHtml(note)}</div>
        </div>`;
      }).join('') || '<div class="priorityEmpty">Keine Agentenberichte vorhanden.</div>';
      return `<div class="agentCompactBoard">
        <div class="agentCompactTop">
          <div class="agentCompactKpi"><span>CEO</span><strong>${escapeHtml(ceoSignal)}</strong><small>${escapeHtml(board?.ceo?.message || '-')}</small></div>
          <div class="agentCompactKpi"><span>Agenten</span><strong>${fmt(activeReports.length, 0)} aktiv</strong><small>LONG ${fmt(longCount, 0)} · SHORT ${fmt(shortCount, 0)} · Ø ${fmt(avgScore, 0)}</small></div>
          <div class="agentCompactKpi"><span>Qualität</span><strong>${fmt(weakCount, 0)} schwach · ${fmt(offlineCount, 0)} offline</strong><small>Blocking ${fmt(blockingCount, 0)}</small></div>
          <div class="agentCompactKpi"><span>Brain / Gate</span><strong>${escapeHtml(fmt(brainScore))} · <span class="${escapeHtml(gateClass)}">${escapeHtml(gateText)}</span></strong><small>${escapeHtml(planText)}</small></div>
        </div>
        <div class="agentCompactTable">
          <div class="agentCompactHead"><div>Agent</div><div>Rolle</div><div>Signal</div><div>Score</div><div>Qualität</div><div>Hinweis</div></div>
          ${rows}
        </div>
        <div class="agentCompactFooter"><span class="agentCompactBadge ${escapeHtml(gateClass)}">Economic Gate ${escapeHtml(gateText)}</span><span>kompakte Prioritätsansicht · detaillierte Karten darunter</span></div>
      </div>`;
    }

    function renderAgentCard(report, ceo=false) {
      const cls = signalClass(report?.signal);
      const conflict = report?.conflict ? ' conflict' : '';
      const score = Math.max(0, Math.min(100, Number(report?.score || 0)));
      const reads = escapeHtml(report?.reads || '-');
      const message = escapeHtml(report?.message || '-');
      const name = escapeHtml(report?.agent_name || '-');
      const fn = escapeHtml(report?.function || '-');
      const role = agentRole(report, ceo);
      const roleLabel = agentRoleLabel(role);
      const quality = agentQualityProfile(report);
      const blocking = report?.blocking ? ' · BLOCKING' : '';
      const riskDetails = role === 'risk' ? renderRiskDetailRows(report?.details || null) : '';
      const agentColor = ceo ? '' : agentColorForName(report?.agent_name);
      return `<div class="${ceo ? 'agentCeoCard' : 'agentCube'} ${cls}${conflict}" data-agent-role="${escapeHtml(role)}" style="--agent-card-color:${escapeHtml(agentColor)}">
        <div class="agentHead"><div class="agentName">${name}<div class="agentFunction">${fn}</div></div><div class="agentHeadBadges"><span class="agentQualityPill ${escapeHtml(String(quality.quality).toLowerCase())}">${escapeHtml(agentQualityLabel(quality.quality))} · ${fmt(quality.reliability, 0)}</span><span class="agentSignal ${cls}">${escapeHtml(report?.signal || 'NEUTRAL')} · ${score}</span></div></div>
        <div class="agentFunction">Rolle: ${escapeHtml(roleLabel)}${blocking} · Daten ${escapeHtml(quality.data)} · Stärke ${escapeHtml(quality.strength)}</div>
        <div class="agentScore"><span style="width:${score}%"></span></div>
        <div class="agentTextBox">Liest: ${reads}
Rueckmeldung: ${message}</div>
        ${riskDetails}
      </div>`;
    }
    function renderAgentViewer(data, cfg) {
      const agentStatus = document.getElementById('agentStatus');
      const agentGrid = document.getElementById('agentGrid');
      const agentRiskGrid = document.getElementById('agentRiskGrid');
      const agentCeo = document.getElementById('agentCeoCard');
      const agentLlmAudit = document.getElementById('agentLlmAuditCard');
      const agentConflictPanel = document.getElementById('agentConflictPanel');
      if (!agentStatus || !agentGrid || !agentRiskGrid || !agentCeo) return;
      const symbol = activeAgentSymbol();
      const board = data?.cycle?.agents?.[symbol] || data?.cycle?.symbols?.[symbol]?.agents || null;
      if (!board) {
        agentStatus.textContent = `${symbol} | noch keine Agenten-Daten`;
        agentCeo.innerHTML = renderAgentCard({agent_name:'CEO Agent', function:'Wartet auf Agentenberichte', signal:'NEUTRAL', score:0, reads:'keine Daten', message:'Scanner starten oder Reload abwarten.'}, true);
        if (agentLlmAudit) {
          if (llmAuditEnabled(cfg)) {
            agentLlmAudit.style.display = '';
            agentLlmAudit.innerHTML = `<h3>Ollama Audit</h3>${renderLlmAuditContent(llmLayerForSymbol(data, cfg, symbol), cfg)}`;
          } else {
            agentLlmAudit.style.display = 'none';
            agentLlmAudit.innerHTML = '';
          }
        }
        if (agentConflictPanel) agentConflictPanel.innerHTML = renderAgentConflictPanel([], {});
        agentGrid.innerHTML = '<div class="agentTextBox">Keine Indikator-Agenten geladen.</div>';
        agentRiskGrid.innerHTML = '<div class="agentTextBox">Keine Risk-/Pipeline-Agenten geladen.</div>';
        return;
      }
      const reports = board.reports || [];
      const visibleReports = cfg?.agent_show_offline_agents === false ? reports.filter(report => !isOfflineAgentReport(report)) : reports;
      const hiddenOfflineCount = reports.length - visibleReports.length;
      const roleFilter = document.getElementById('agentRoleFilter')?.value || agentRoleFilter || 'all';
      const sortedReports = sortAgentReports(filterAgentReportsByRole(visibleReports, roleFilter));
      const indicatorReports = sortedReports.filter(report => !isRiskPipelineReport(report));
      const riskReports = sortedReports.filter(report => isRiskPipelineReport(report));
      const brainState = data?.cycle?.brains?.[symbol] || data?.cycle?.symbols?.[symbol]?.brain || {};
      const brain = board.brain || brainState.brain || null;
      const tradePlan = board.trade_plan || brainState.candidate || null;
      const memoryMatch = board.memory_match || brainState.memory_match || tradePlan?.features?.memory_match || null;
      const gate = board.economic_gate || brainState.economic_gate || null;
      const llmLayer = board.llm_layer || brainState.llm_layer || null;
      const flowInfo = tradePlan
        ? `<div class="agentTextBox">Trade Plan: ${escapeHtml(tradePlan.decision)} | Entry ${escapeHtml(fmt(tradePlan.entry_price))} | SL ${escapeHtml(fmt(tradePlan.sl_price))} | TP ${escapeHtml(fmt(tradePlan.tp_price))}<br>Economic Gate: ${gateHtml(gate)}</div>`
        : `<div class="agentTextBox">Trade Plan: kein freigegebener Trade-Kandidat<br>Economic Gate: ${gateHtml(gate)}</div>`;
      const offlineInfo = hiddenOfflineCount > 0 ? ` | ${hiddenOfflineCount} Offline ausgeblendet` : '';
      const sortLabel = document.getElementById('agentSortMode')?.selectedOptions?.[0]?.textContent || 'Score hoch';
      const roleLabel = document.getElementById('agentRoleFilter')?.selectedOptions?.[0]?.textContent || 'Alle Rollen';
      agentStatus.textContent = `${board.symbol || symbol} | ${timeframeLabel(board.timeframe_seconds || cfg?.signal_timeframe_seconds || 0)} | ${indicatorReports.length} Indikator / ${riskReports.length} Risk${offlineInfo} | Sort: ${sortLabel} | Rolle: ${roleLabel} | ${board.ceo?.message || '-'}`;
      agentCeo.innerHTML = `${renderAgentCompactDashboard(board, sortedReports, brain, gate, tradePlan)}${renderAgentDecisionCenter(board, visibleReports, brain, gate, tradePlan)}${renderAgentCard(board.ceo || {}, true)}${renderCeoDecisionExplanation(board.ceo || {}, visibleReports, brain, gate)}${renderBrainDecisionExplanation(brain, tradePlan, memoryMatch, gate)}${brain ? renderAgentCard(brain, true) : ''}${flowInfo}`;
      if (agentLlmAudit) {
        if (llmAuditEnabled(cfg)) {
          agentLlmAudit.style.display = '';
          agentLlmAudit.innerHTML = `<h3>Ollama Audit</h3>${renderLlmAuditContent(llmLayer || llmLayerForSymbol(data, cfg, symbol), cfg)}`;
        } else {
          agentLlmAudit.style.display = 'none';
          agentLlmAudit.innerHTML = '';
        }
      }
      if (agentConflictPanel) agentConflictPanel.innerHTML = renderAgentConflictPanel(sortedReports, board.ceo || {});
      const structureReports = indicatorReports.filter(report => agentRole(report) === 'structure');
      const momentumReports = indicatorReports.filter(report => agentRole(report) === 'momentum');
      const otherReports = indicatorReports.filter(report => !['structure', 'momentum'].includes(agentRole(report)));
      agentGrid.innerHTML = [
        renderAgentRoleGroup('Struktur-Agenten', structureReports, 'structure'),
        renderAgentRoleGroup('Momentum-Agenten', momentumReports, 'momentum'),
        renderAgentRoleGroup('Weitere Signal-Agenten', otherReports, 'other'),
      ].filter(Boolean).join('') || '<div class="agentTextBox">Keine sichtbaren Indikator-Agenten.</div>';
      agentRiskGrid.innerHTML = renderAgentRoleGroup('Risk / Pipeline', riskReports, 'risk') || '<div class="agentTextBox">Keine sichtbaren Risk-/Pipeline-Agenten.</div>';
    }
    function isOfflineAgentReport(report) {
      const reads = String(report?.reads || '').toLowerCase();
      const message = String(report?.message || '').toLowerCase();
      return reads.includes('_enabled=false') || reads.includes('indicator_show_') || message.includes('deaktiviert') || message.includes('ausgeschaltet');
    }
    function isRiskPipelineReport(report) {
      const name = String(report?.agent_name || '').toLowerCase();
      const fn = String(report?.function || '').toLowerCase();
      return name.includes('risk') || name.includes('gate') || fn.includes('risk') || fn.includes('gate') || fn.includes('pipeline');
    }
    async function loadChartData(force) {
      const asset = activeChartSymbol();
      const resolution = document.getElementById('chartTimeframe').value || '60';
      const limit = Number(document.getElementById('chartCandleLimit').value || 100);
      const cfgKey = JSON.stringify(indicatorConfig());
      const key = `${asset}:${resolution}:${limit}:${cfgKey}`;
      if (!force && key === lastChartKey) return;
      lastChartKey = key;
      document.getElementById('chartStatus').textContent = 'Lade Phemex-Kerzen...';
      const response = await fetch(`/api/chart-data?symbol=${encodeURIComponent(asset)}&resolution=${encodeURIComponent(resolution)}&limit=${encodeURIComponent(limit)}`, { cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) {
        document.getElementById('chartStatus').textContent = data.error || 'Chart Fehler';
        clearKlineChart();
        return;
      }
      const statusResponse = await fetch('/api/status', { cache: 'no-store' });
      const indicatorData = await loadCustomIndicatorData(asset, resolution, limit);
      const statusData = statusResponse.ok ? await statusResponse.json() : {};
      const overlay = buildChartOverlay(asset, statusData);
      drawChart(data.candles || [], overlay, indicatorData);
      const minutes = Number(data.resolution) / 60;
      const indicatorLabel = indicatorData?.label || 'Market Structure nicht geladen';
      document.getElementById('chartStatus').textContent = `${data.chart_symbol || data.symbol} | ${minutes}m | ${data.candles.length} Kerzen | ${indicatorLabel} | ${overlay.status}`;
      document.getElementById('chartMeta').textContent = data.candles.length
        ? `${overlay.summary} | Indikator: ${indicatorLabel} | letzte Kerze: ${new Date(data.candles[data.candles.length - 1].timestamp * 1000).toISOString()} | Close: ${data.candles[data.candles.length - 1].close}`
        : 'Keine Kerzen erhalten.';
    }
    function buildChartOverlay(asset, statusData) {
      const cycle = statusData.cycle || {};
      const symbolInfo = (cycle.symbols || {})[asset] || {};
      const scan = symbolInfo.scan || {};
      const events = cycle.events || [];
      const setupEvent = events.find(event => event.setup?.symbol === asset) || null;
      const tradeEvent = events.find(event => event.trade?.setup?.symbol === asset) || null;
      const trade = tradeEvent?.trade || null;
      const setup = setupEvent?.setup || trade?.setup || null;
      const side = setup?.side || scan.side || '-';
      const zoneLow = scan.zone_low;
      const zoneHigh = scan.zone_high;
      const entryZoneLow = setup?.fvg_low ?? scan.entry_zone_low ?? scan.fvg_low;
      const entryZoneHigh = setup?.fvg_high ?? scan.entry_zone_high ?? scan.fvg_high;
      const entry = setup?.entry ?? scan.entry;
      const stop = setup?.stop_loss ?? scan.stop_loss;
      const tp = setup?.take_profit;
      const status = setup
        ? (setupEvent?.reason === 'value_gate' ? 'Setup blockiert: Value Gate' : `Setup ${String(side).toUpperCase()}`)
        : `Kein Setup: ${scan.reason || 'noch kein Scan'}`;
      const zoneReady = Number.isFinite(Number(zoneLow)) && Number.isFinite(Number(zoneHigh));
      const entryZoneReady = Number.isFinite(Number(entryZoneLow)) && Number.isFinite(Number(entryZoneHigh));
      const valueGateBlocked = setupEvent?.reason === 'value_gate';
      const diagnostics = [
        {
          label: `Swing-Level ${zoneReady ? 'OK' : 'fehlt'}`,
          detail: zoneReady ? `${fmt(scan.zone_type)} ${fmt(zoneLow)} - ${fmt(zoneHigh)}` : scan.reason || '-',
          state: zoneReady ? 'ok' : 'fail'
        },
        {
          label: `Swing Score ${fmt(scan.swing_level_score || scan.zone_score)}`,
          detail: `Age ${fmt(scan.swing_level_age_candles)} | Target ${fmt(scan.target_level)}`,
          state: zoneReady ? 'ok' : 'neutral'
        },
        {
          label: scan.entry_method ? `Reaction ${scan.entry_method}` : 'Reaction offen',
          detail: entryZoneReady ? `${fmt(entryZoneLow)} - ${fmt(entryZoneHigh)}` : scan.reason || '-',
          state: setup || scan.entry_method ? 'ok' : 'neutral'
        },
        {
          label: entryZoneReady ? 'Reaktionszone OK' : 'Reaktionszone fehlt',
          detail: entryZoneReady ? `${fmt(entryZoneLow)} - ${fmt(entryZoneHigh)}` : scan.reason || '-',
          state: entryZoneReady ? 'ok' : 'neutral'
        },
        {
          label: valueGateBlocked ? 'Value Gate blockiert' : setup ? 'Value Gate OK' : 'Value Gate offen',
          detail: valueGateBlocked ? gateDetailText(setupEvent?.value_result) : setup ? 'wirtschaftlich akzeptiert' : 'erst nach Setup',
          state: valueGateBlocked ? 'fail' : setup ? 'ok' : 'neutral'
        }
      ];
      const summaryParts = [
        status,
        scan.zone_type ? `${scan.zone_type} ${fmt(scan.zone_low)}-${fmt(scan.zone_high)}` : '',
        scan.entry_method ? `Entry ${scan.entry_method}` : '',
        diagnostics[0].label,
        diagnostics[2].label,
        entry ? `Entry ${fmt(entry)}` : '',
        stop ? `SL ${fmt(stop)}` : '',
        tp ? `TP ${fmt(tp)}` : '',
      ].filter(Boolean);
      return {
        asset,
        status,
        summary: summaryParts.join(' | '),
        scan,
        setup,
        diagnostics,
        levels: [
          scan.zone_low ? { price: Number(scan.zone_low), label: 'Zone Low', color: '#475569', time: scan.base_start_time } : null,
          scan.zone_high ? { price: Number(scan.zone_high), label: 'Zone High', color: '#475569', time: scan.base_end_time } : null,
          scan.structure_level ? { price: Number(scan.structure_level), label: scan.structure_level_type || 'Level', color: '#7c3aed', time: scan.structure_level_time } : null,
          entry ? { price: Number(entry), label: 'Entry', color: '#2357c6', strong: true } : null,
          stop ? { price: Number(stop), label: 'SL', color: '#b42318', strong: true } : null,
          tp ? { price: Number(tp), label: 'TP', color: '#047857', strong: true } : null,
        ].filter(Boolean),
        fvg: Number.isFinite(Number(entryZoneLow)) && Number.isFinite(Number(entryZoneHigh)) ? { low: Number(entryZoneLow), high: Number(entryZoneHigh), label: scan.has_fvg ? 'FVG Entry-Zone' : 'Entry-Zone' } : null,
        markers: [
          scan.signal_candle_time ? { time: Number(scan.signal_candle_time), label: scan.setup_found ? 'Zone + Setup' : 'Zone-Check', color: scan.setup_found ? '#0f766e' : '#d97706', lineColor: scan.setup_found ? 'rgba(15,118,110,.28)' : 'rgba(217,119,6,.28)' } : null,
          scan.confirmation_candle_time ? { time: Number(scan.confirmation_candle_time), label: 'Entry-Bestaetigung', color: '#2357c6', lineColor: 'rgba(35,87,198,.28)' } : null,
        ].filter(Boolean)
      };
    }
    function klinechartsApi() {
      return window.klinecharts || window.KLineCharts || window.KLineChart || null;
    }
    function safeHexColor(value, fallback) {
      const color = String(value || '').trim();
      return /^#[0-9a-fA-F]{6}$/.test(color) ? color : fallback;
    }
    function colorWithAlpha(hex, alpha = 1) {
      const color = safeHexColor(hex, '#000000');
      const r = parseInt(color.slice(1, 3), 16);
      const g = parseInt(color.slice(3, 5), 16);
      const b = parseInt(color.slice(5, 7), 16);
      return `rgba(${r},${g},${b},${alpha})`;
    }
    function chartColors() {
      const cfg = latestConfig || {};
      const candleBodyUp = safeHexColor(cfg.chart_candle_up_color, '#047857');
      const candleBodyDown = safeHexColor(cfg.chart_candle_down_color, '#b42318');
      const candleBodyNoChange = safeHexColor(cfg.chart_candle_no_change_color, '#667085');
      return {
        candleBodyUp,
        candleBodyDown,
        candleBodyNoChange,
        candleWickUp: safeHexColor(cfg.chart_candle_wick_up_color, candleBodyUp),
        candleWickDown: safeHexColor(cfg.chart_candle_wick_down_color, candleBodyDown),
        candleWickNoChange: safeHexColor(cfg.chart_candle_wick_no_change_color, candleBodyNoChange),
        candleBorderUp: safeHexColor(cfg.chart_candle_border_up_color, candleBodyUp),
        candleBorderDown: safeHexColor(cfg.chart_candle_border_down_color, candleBodyDown),
        candleBorderNoChange: safeHexColor(cfg.chart_candle_border_no_change_color, candleBodyNoChange),
        candleUp: candleBodyUp,
        candleDown: candleBodyDown,
        candleNoChange: candleBodyNoChange,
        grid: safeHexColor(cfg.chart_grid_color, '#d9e0ea'),
        background: safeHexColor(cfg.chart_background_color, (cfg.ui_theme === 'light' ? '#ffffff' : '#020617')),
        bosRising: safeHexColor(cfg.indicator_bos_rising_color || cfg.indicator_rising_color, '#047857'),
        bosFalling: safeHexColor(cfg.indicator_bos_falling_color || cfg.indicator_falling_color, '#b42318'),
        swingRising: safeHexColor(cfg.indicator_swing_rising_color || cfg.indicator_rising_color, '#047857'),
        swingFalling: safeHexColor(cfg.indicator_swing_falling_color || cfg.indicator_falling_color, '#b42318'),
        boxHigh: safeHexColor(cfg.indicator_box_high_color, '#b42318'),
        boxLow: safeHexColor(cfg.indicator_box_low_color, '#047857'),
        hma: safeHexColor(cfg.indicator_hma_color, '#7c3aed'),
        sma: safeHexColor(cfg.indicator_sma_color, '#06b6d4'),
        tripleEma: safeHexColor(cfg.indicator_triple_ema_color, '#d97706'),
        tripleEmaSlow: safeHexColor(cfg.indicator_triple_ema_slow_color, '#2563eb'),
        mfi: safeHexColor(cfg.indicator_mfi_color, '#db2777'),
        macd: safeHexColor(cfg.indicator_macd_color, '#0ea5e9'),
        macdSignal: safeHexColor(cfg.indicator_macd_signal_color, '#f97316'),
        macdHistogram: safeHexColor(cfg.indicator_macd_histogram_color, '#64748b'),
        srSupport: safeHexColor(cfg.indicator_sr_support_color, '#22c55e'),
        srResistance: safeHexColor(cfg.indicator_sr_resistance_color, '#ef4444'),
      };
    }
    function klineChartStyleOptions() {
      const colors = chartColors();
      return {
        grid: { show: true, horizontal: { show: true, color: colors.grid }, vertical: { show: true, color: colors.grid } },
        candle: {
          area: { backgroundColor: colors.background },
          bar: {
            upColor: colors.candleBodyUp,
            downColor: colors.candleBodyDown,
            noChangeColor: colors.candleBodyNoChange,
            upWickColor: colors.candleWickUp,
            downWickColor: colors.candleWickDown,
            noChangeWickColor: colors.candleWickNoChange,
            upBorderColor: colors.candleBorderUp,
            downBorderColor: colors.candleBorderDown,
            noChangeBorderColor: colors.candleBorderNoChange
          }
        }
      };
    }
    function updateKlineChartStyles() {
      const colors = chartColors();
      const container = document.getElementById('klineChart');
      if (container) container.style.backgroundColor = colors.background;
      if (!klineChart) return;
      const styles = klineChartStyleOptions();
      if (typeof klineChart.setStyles === 'function') {
        klineChart.setStyles(styles);
      } else if (typeof klineChart.applyStyles === 'function') {
        klineChart.applyStyles(styles);
      }
    }
    function marketStructureStyle(direction, alpha = 1, kind = 'bos') {
      const colors = chartColors();
      if (kind === 'box') {
        return colorWithAlpha(direction === 'rising' ? colors.boxLow : colors.boxHigh, alpha);
      }
      if (kind === 'swing') {
        return colorWithAlpha(direction === 'rising' ? colors.swingRising : colors.swingFalling, alpha);
      }
      return colorWithAlpha(direction === 'rising' ? colors.bosRising : colors.bosFalling, alpha);
    }
    function registerMarketStructureOverlays() {
      const api = klinechartsApi();
      if (marketStructureOverlaysRegistered || !api?.registerOverlay) return;
      const textStyle = (color, size = 11) => ({
        color,
        size,
        family: 'Arial',
        weight: 'normal',
        style: 'fill',
        backgroundColor: 'transparent',
        borderColor: 'transparent',
        borderSize: 0,
        paddingLeft: 0,
        paddingRight: 0,
        paddingTop: 0,
        paddingBottom: 0
      });
      api.registerOverlay({
        name: 'marketStructureLabel',
        totalStep: 1,
        lock: true,
        createPointFigures: ({ overlay, coordinates }) => {
          const point = coordinates[0];
          if (!point) return [];
          const data = overlay.extendData || {};
          const color = marketStructureStyle(data.direction, 1, 'swing');
          const isHigh = data.text === 'HH' || data.text === 'LH';
          const width = Math.max(22, String(data.text || '').length * 8 + 10);
          const x = point.x - width / 2;
          const y = point.y + (isHigh ? -26 : 10);
          return [
            { type: 'rect', attrs: { x, y, width, height: 18 }, styles: { style: 'stroke_fill', color: 'rgba(255,255,255,0.82)', borderColor: color }, ignoreEvent: true },
            { type: 'text', attrs: { x: point.x, y: y + 9, text: String(data.text || ''), align: 'center', baseline: 'middle' }, styles: textStyle(color, 11), ignoreEvent: true }
          ];
        }
      });
      api.registerOverlay({
        name: 'marketStructureBreakLine',
        totalStep: 2,
        lock: true,
        createPointFigures: ({ overlay, coordinates }) => {
          if (coordinates.length < 2) return [];
          const data = overlay.extendData || {};
          const color = marketStructureStyle(data.direction, 0.95);
          const y = coordinates[0].y;
          const labelX = coordinates[0].x + Math.max(24, (coordinates[1].x - coordinates[0].x) / 2);
          return [
            { type: 'line', attrs: { coordinates: [{ x: coordinates[0].x, y }, { x: coordinates[1].x, y }] }, styles: { color, size: data.text === 'CHoCH' ? 2 : 1 }, ignoreEvent: true },
            { type: 'text', attrs: { x: labelX, y: y - 10, text: String(data.text || ''), align: 'center', baseline: 'middle' }, styles: textStyle(color, 11), ignoreEvent: true }
          ];
        }
      });
      api.registerOverlay({
        name: 'marketStructureBox',
        totalStep: 2,
        lock: true,
        createPointFigures: ({ overlay, coordinates }) => {
          if (coordinates.length < 2) return [];
          const data = overlay.extendData || {};
          const color = marketStructureStyle(data.direction, 0.55, 'box');
          const fill = marketStructureStyle(data.direction, Number(data.opacity || 0.12), 'box');
          const x = Math.min(coordinates[0].x, coordinates[1].x);
          const y = Math.min(coordinates[0].y, coordinates[1].y);
          const width = Math.abs(coordinates[1].x - coordinates[0].x);
          const height = Math.max(2, Math.abs(coordinates[1].y - coordinates[0].y));
          const figures = [
            { type: 'rect', attrs: { x, y, width: Math.max(1, width), height }, styles: { style: 'stroke_fill', color: fill, borderColor: color }, ignoreEvent: true }
          ];
          if (data.text) {
            figures.push({ type: 'text', attrs: { x: x + Math.max(12, width - 18), y: y + 12, text: String(data.text), align: 'center', baseline: 'middle' }, styles: textStyle(marketStructureStyle(data.direction, 0.95, 'box'), 11), ignoreEvent: true });
          }
          return figures;
        }
      });
      api.registerOverlay({
        name: 'indicatorLineSegment',
        totalStep: 2,
        lock: true,
        createPointFigures: ({ overlay, coordinates }) => {
          if (coordinates.length < 2) return [];
          const data = overlay.extendData || {};
          const color = data.color || '#7c3aed';
          return [
            {
              type: 'line',
              attrs: { coordinates: [{ x: coordinates[0].x, y: coordinates[0].y }, { x: coordinates[1].x, y: coordinates[1].y }] },
              styles: { color, size: Number(data.size || 1) },
              ignoreEvent: true
            }
          ];
        }
      });
      marketStructureOverlaysRegistered = true;
    }
    function initKlineChart() {
      if (klineChart) return klineChart;
      const api = klinechartsApi();
      const container = document.getElementById('klineChart');
      if (!api?.init || !container) {
        document.getElementById('chartStatus').textContent = 'KLineChart konnte nicht geladen werden.';
        return null;
      }
      klineChart = api.init(container, {
        styles: klineChartStyleOptions()
      });
      updateKlineChartStyles();
      registerMarketStructureOverlays();
      return klineChart;
    }
    function indicatorConfig() {
      const cfg = latestConfig || {};
      const colors = chartColors();
      return {
        enabled: cfg.indicator_enabled !== false,
        showBosChoch: cfg.indicator_show_bos_choch !== false,
        showBoxes: cfg.indicator_show_boxes !== false,
        showSwingLabels: cfg.indicator_show_swing_labels !== false,
        showHma: cfg.indicator_show_hma === true,
        showSma: cfg.indicator_show_sma !== false,
        showTripleEma: cfg.indicator_show_triple_ema === true,
        showMfi: cfg.indicator_show_mfi !== false,
        showMacd: cfg.indicator_show_macd !== false,
        showSupportResistance: cfg.indicator_show_support_resistance !== false,
        swingSize: Number(cfg.indicator_swing_size ?? 5),
        hhllRange: Number(cfg.indicator_hhll_range ?? 50),
        hmaPeriod: Number(cfg.indicator_hma_period ?? 20),
        smaPeriod: Number(cfg.indicator_sma_period ?? 14),
        tripleEmaPeriod: Number(cfg.indicator_triple_ema_period ?? 20),
        tripleEmaSlowPeriod: Number(cfg.indicator_triple_ema_slow_period ?? 50),
        mfiPeriod: Number(cfg.indicator_mfi_period ?? 14),
        macdFastPeriod: Number(cfg.indicator_macd_fast_period ?? 12),
        macdSlowPeriod: Number(cfg.indicator_macd_slow_period ?? 26),
        macdSignalPeriod: Number(cfg.indicator_macd_signal_period ?? 9),
        srPivotPeriod: Number(cfg.indicator_sr_pivot_period ?? 10),
        srSource: String(cfg.indicator_sr_source || 'High/Low'),
        srMaxPivots: Number(cfg.indicator_sr_max_pivots ?? 20),
        srChannelWidthPercent: Number(cfg.indicator_sr_channel_width_percent ?? 10),
        srMaxLevels: Number(cfg.indicator_sr_max_levels ?? 5),
        srMinStrength: Number(cfg.indicator_sr_min_strength ?? 2),
        boxExtendCandles: Math.max(2, Number(cfg.indicator_box_extend_candles ?? 4)),
        bosChochLookbackDays: Number(cfg.indicator_bos_choch_lookback_days ?? cfg.indicator_lookback_days ?? 3),
        boxesLookbackDays: Number(cfg.indicator_boxes_lookback_days ?? cfg.indicator_lookback_days ?? 3),
        swingLabelsLookbackDays: Number(cfg.indicator_swing_labels_lookback_days ?? cfg.indicator_lookback_days ?? 3),
        hmaLookbackDays: Number(cfg.indicator_hma_lookback_days ?? 0),
        smaLookbackDays: Number(cfg.indicator_sma_lookback_days ?? 0),
        tripleEmaLookbackDays: Number(cfg.indicator_triple_ema_lookback_days ?? 0),
        mfiLookbackDays: Number(cfg.indicator_mfi_lookback_days ?? 0),
        macdLookbackDays: Number(cfg.indicator_macd_lookback_days ?? 0),
        bosConfirmation: String(cfg.indicator_bos_confirmation || 'Wicks'),
        hmaColor: colors.hma,
        smaColor: colors.sma,
        tripleEmaColor: colors.tripleEma,
        tripleEmaSlowColor: colors.tripleEmaSlow,
        mfiColor: colors.mfi,
        macdColor: colors.macd,
        macdSignalColor: colors.macdSignal,
        macdHistogramColor: colors.macdHistogram,
        srSupportColor: colors.srSupport,
        srResistanceColor: colors.srResistance,
      };
    }
    function renderIndicatorChartSettings(indicatorData) {
      const el = document.getElementById('indicatorChartSettings');
      if (!el) return;
      const cfg = indicatorConfig();
      if (!cfg.enabled) {
        el.textContent = 'Indikatoren: aus';
        return;
      }
      const labels = indicatorData?.labels?.length || 0;
      const breaks = indicatorData?.break_lines?.length || 0;
      const boxes = indicatorData?.boxes?.length || 0;
      const srLevels = indicatorData?.support_resistance?.length || 0;
      const lines = (indicatorData?.lines || []).map(line => `${line.label}: ${line.series?.length || 0}`).join(' · ');
      el.textContent = `Indikatoren: BOS/CHoCH ${breaks} (${cfg.bosChochLookbackDays}T) · Boxen ${boxes} (${cfg.boxesLookbackDays}T) · Swing Labels ${labels} (${cfg.swingLabelsLookbackDays}T) · S/R ${srLevels} · Box Auslauf ${cfg.boxExtendCandles} Kerzen${lines ? ' · ' + lines : ''}`;
    }
    async function loadCustomIndicatorData(asset, resolution, limit) {
      const cfg = indicatorConfig();
      if (!cfg.enabled) {
        lastIndicatorData = null;
        renderIndicatorChartSettings(null);
        return null;
      }
      try {
        const params = new URLSearchParams({
          symbol: asset,
          resolution: resolution,
          limit: String(limit),
          swing_size: String(cfg.swingSize),
          hhll_range: String(cfg.hhllRange),
          hma_period: String(cfg.hmaPeriod),
          sma_period: String(cfg.smaPeriod),
          triple_ema_period: String(cfg.tripleEmaPeriod),
          triple_ema_slow_period: String(cfg.tripleEmaSlowPeriod),
          mfi_period: String(cfg.mfiPeriod),
          macd_fast_period: String(cfg.macdFastPeriod),
          macd_slow_period: String(cfg.macdSlowPeriod),
          macd_signal_period: String(cfg.macdSignalPeriod),
          sr_pivot_period: String(cfg.srPivotPeriod),
          sr_source: cfg.srSource,
          sr_max_pivots: String(cfg.srMaxPivots),
          sr_channel_width_percent: String(cfg.srChannelWidthPercent),
          sr_max_levels: String(cfg.srMaxLevels),
          sr_min_strength: String(cfg.srMinStrength),
          box_extend_candles: String(cfg.boxExtendCandles),
          bos_choch_lookback_days: String(cfg.bosChochLookbackDays),
          boxes_lookback_days: String(cfg.boxesLookbackDays),
          swing_labels_lookback_days: String(cfg.swingLabelsLookbackDays),
          hma_lookback_days: String(cfg.hmaLookbackDays),
          sma_lookback_days: String(cfg.smaLookbackDays),
          triple_ema_lookback_days: String(cfg.tripleEmaLookbackDays),
          mfi_lookback_days: String(cfg.mfiLookbackDays),
          macd_lookback_days: String(cfg.macdLookbackDays),
          bos_confirmation: cfg.bosConfirmation,
          hma_color: cfg.hmaColor,
          sma_color: cfg.smaColor,
          triple_ema_color: cfg.tripleEmaColor,
          triple_ema_slow_color: cfg.tripleEmaSlowColor,
          mfi_color: cfg.mfiColor,
          macd_color: cfg.macdColor,
          macd_signal_color: cfg.macdSignalColor,
          macd_histogram_color: cfg.macdHistogramColor,
          sr_support_color: cfg.srSupportColor,
          sr_resistance_color: cfg.srResistanceColor,
          show_bos_choch: String(cfg.showBosChoch),
          show_boxes: String(cfg.showBoxes),
          show_swing_labels: String(cfg.showSwingLabels),
          show_hma: String(cfg.showHma),
          show_sma: String(cfg.showSma),
          show_triple_ema: String(cfg.showTripleEma),
          show_mfi: String(cfg.showMfi),
          show_macd: String(cfg.showMacd),
          show_support_resistance: String(cfg.showSupportResistance)
        });
        const response = await fetch(`/api/indicator-data?${params.toString()}`, { cache: 'no-store' });
        lastIndicatorData = response.ok ? await response.json() : null;
        renderIndicatorChartSettings(lastIndicatorData);
        return lastIndicatorData;
      } catch (error) {
        console.warn('indicator request failed', error);
        lastIndicatorData = null;
        renderIndicatorChartSettings(null);
        return null;
      }
    }
    function drawMarketStructureOverlay(rows, indicatorData) {
      if (!klineChart || !rows.length || !indicatorData || typeof klineChart.createOverlay !== 'function') return;
      registerMarketStructureOverlays();
      const toPoint = (timestamp, price) => ({ timestamp: Number(timestamp) * 1000, value: Number(price) });
      (indicatorData.lines || []).filter(line => (line.pane || 'price') === 'price').forEach(line => {
        const series = line.series || [];
        for (let index = 1; index < series.length; index += 1) {
          const previous = series[index - 1];
          const current = series[index];
          if (!Number.isFinite(Number(previous.timestamp)) || !Number.isFinite(Number(current.timestamp))) continue;
          if (!Number.isFinite(Number(previous.value)) || !Number.isFinite(Number(current.value))) continue;
          rememberKlineOverlay(klineChart.createOverlay({
            name: 'indicatorLineSegment',
            groupId: 'indicator_lines',
            lock: true,
            zLevel: 5,
            points: [toPoint(previous.timestamp, previous.value), toPoint(current.timestamp, current.value)],
            extendData: { color: line.color, label: line.label, size: 1 },
          }));
        }
      });
      (indicatorData.boxes || []).forEach(box => {
        if (!Number.isFinite(Number(box.start_timestamp)) || !Number.isFinite(Number(box.end_timestamp))) return;
        rememberKlineOverlay(klineChart.createOverlay({
          name: 'marketStructureBox',
          groupId: 'market_structure',
          lock: true,
          zLevel: 10,
          points: [toPoint(box.start_timestamp, box.top), toPoint(box.end_timestamp, box.bottom)],
          extendData: { text: box.text, direction: box.direction, opacity: box.opacity },
        }));
      });
      (indicatorData.support_resistance || []).forEach(level => {
        if (!Number.isFinite(Number(level.price))) return;
        rememberKlineOverlay(klineChart.createOverlay({
          name: 'horizontalStraightLine',
          groupId: 'indicator_sr_levels',
          lock: true,
          zLevel: 14,
          points: [{ timestamp: rows[rows.length - 1]?.timestamp, value: Number(level.price) }],
          extendData: level.label || `${level.kind || 'SR'} ${Number(level.price).toFixed(4)}`,
          styles: { line: { color: level.color || (level.kind === 'support' ? chartColors().srSupport : chartColors().srResistance), size: 1, style: 'dashed' } }
        }));
      });
      (indicatorData.break_lines || []).forEach(line => {
        if (!Number.isFinite(Number(line.start_timestamp)) || !Number.isFinite(Number(line.end_timestamp))) return;
        rememberKlineOverlay(klineChart.createOverlay({
          name: 'marketStructureBreakLine',
          groupId: 'market_structure',
          lock: true,
          zLevel: 20,
          points: [toPoint(line.start_timestamp, line.price), toPoint(line.end_timestamp, line.price)],
          extendData: { text: line.text, direction: line.direction },
        }));
      });
      (indicatorData.labels || []).forEach(label => {
        if (!Number.isFinite(Number(label.timestamp))) return;
        rememberKlineOverlay(klineChart.createOverlay({
          name: 'marketStructureLabel',
          groupId: 'market_structure',
          lock: true,
          zLevel: 30,
          points: [toPoint(label.timestamp, label.price)],
          extendData: { text: label.text, direction: label.direction },
        }));
      });
    }
    function resizeKlineChart() {
      if (!klineChart) return;
      if (typeof klineChart.resize === 'function') {
        klineChart.resize();
      }
    }
    function clearKlineChart() {
      if (!klineChart) return;
      clearKlineOverlays();
      if (typeof klineChart.clearData === 'function') {
        klineChart.clearData();
      } else if (typeof klineChart.applyNewData === 'function') {
        klineChart.applyNewData([]);
      }
    }
    function candleToKlineData(candle) {
      return {
        timestamp: Number(candle.timestamp) * 1000,
        open: Number(candle.open),
        high: Number(candle.high),
        low: Number(candle.low),
        close: Number(candle.close),
        volume: Number(candle.volume || 0),
        turnover: Number(candle.turnover || 0)
      };
    }
    function drawChart(candles, overlay, indicatorData) {
      const chart = initKlineChart();
      if (!chart) return;
      const rows = candles.map(candleToKlineData).filter(row =>
        Number.isFinite(row.timestamp) && Number.isFinite(row.open) && Number.isFinite(row.high) &&
        Number.isFinite(row.low) && Number.isFinite(row.close)
      );
      if (typeof chart.applyNewData !== 'function') {
        document.getElementById('chartStatus').textContent = 'KLineChart Version ohne applyNewData geladen.';
        return;
      }
      chart.applyNewData(rows, false);
      lastChartRows = rows;
      resizeKlineChart();
      renderKlineStrategyOverlay(rows, overlay);
      drawMarketStructureOverlay(rows, indicatorData);
    }
    function clearKlineOverlays() {
      if (!klineChart || typeof klineChart.removeOverlay !== 'function') {
        klineOverlayIds = [];
        return;
      }
      klineOverlayIds.forEach(id => {
        try { klineChart.removeOverlay({ id }); } catch (error) { try { klineChart.removeOverlay(id); } catch (_) {} }
      });
      klineOverlayIds = [];
    }
    function rememberKlineOverlay(result) {
      if (Array.isArray(result)) {
        result.filter(Boolean).forEach(id => klineOverlayIds.push(id));
      } else if (result) {
        klineOverlayIds.push(result);
      }
    }
    function overlayPoint(rows, price, timestamp = null) {
      const time = timestamp ? Number(timestamp) * 1000 : rows[rows.length - 1]?.timestamp;
      return { timestamp: time, value: Number(price) };
    }
    function renderKlineStrategyOverlay(rows, overlay) {
      clearKlineOverlays();
      if (!klineChart || !rows.length || !overlay || typeof klineChart.createOverlay !== 'function') return;
      (overlay.levels || []).forEach(level => {
        if (!Number.isFinite(Number(level.price))) return;
        rememberKlineOverlay(klineChart.createOverlay({
          name: 'horizontalStraightLine',
          groupId: 'strategy',
          lock: true,
          points: [overlayPoint(rows, level.price, level.time)],
          extendData: `${level.label} ${Number(level.price).toFixed(4)}`,
          styles: { line: { color: level.color, size: level.strong ? 2 : 1, style: level.strong ? 'solid' : 'dashed' } }
        }));
      });
      if (overlay.fvg) {
        [
          { price: overlay.fvg.low, label: `${overlay.fvg.label} Low` },
          { price: overlay.fvg.high, label: `${overlay.fvg.label} High` }
        ].forEach(item => rememberKlineOverlay(klineChart.createOverlay({
          name: 'horizontalStraightLine',
          groupId: 'strategy',
          lock: true,
          points: [overlayPoint(rows, item.price)],
          extendData: `${item.label} ${Number(item.price).toFixed(4)}`,
          styles: { line: { color: '#2357c6', size: 1, style: 'dashed' } }
        })));
      }
      (overlay.markers || []).forEach(marker => {
        if (!Number.isFinite(Number(marker.time))) return;
        rememberKlineOverlay(klineChart.createOverlay({
          name: 'verticalStraightLine',
          groupId: 'strategy',
          lock: true,
          points: [{ timestamp: Number(marker.time) * 1000 }],
          extendData: marker.label,
          styles: { line: { color: marker.color, size: 1, style: 'dashed' } }
        }));
      });
    }
    function applyIndicatorSettingsToForm(data) {
      document.getElementById('cfgIndicatorEnabled').checked = data.indicator_enabled !== false;
      document.getElementById('cfgIndicatorShowBosChoch').checked = data.indicator_show_bos_choch !== false;
      document.getElementById('cfgIndicatorShowBoxes').checked = data.indicator_show_boxes !== false;
      document.getElementById('cfgIndicatorShowSwingLabels').checked = data.indicator_show_swing_labels !== false;
      document.getElementById('cfgIndicatorShowHma').checked = data.indicator_show_hma === true;
      document.getElementById('cfgIndicatorShowSma').checked = data.indicator_show_sma !== false;
      document.getElementById('cfgIndicatorShowTripleEma').checked = data.indicator_show_triple_ema === true;
      document.getElementById('cfgIndicatorShowMfi').checked = data.indicator_show_mfi !== false;
      document.getElementById('cfgIndicatorShowMacd').checked = data.indicator_show_macd !== false;
      document.getElementById('cfgIndicatorShowSupportResistance').checked = data.indicator_show_support_resistance !== false;
      document.getElementById('cfgIndicatorSwingSize').value = data.indicator_swing_size ?? 5;
      document.getElementById('cfgIndicatorHhllRange').value = data.indicator_hhll_range ?? 50;
      document.getElementById('cfgIndicatorBoxExtendCandles').value = data.indicator_box_extend_candles ?? 4;
      document.getElementById('cfgIndicatorBosChochLookbackDays').value = data.indicator_bos_choch_lookback_days ?? data.indicator_lookback_days ?? 3;
      document.getElementById('cfgIndicatorBoxesLookbackDays').value = data.indicator_boxes_lookback_days ?? data.indicator_lookback_days ?? 3;
      document.getElementById('cfgIndicatorSwingLabelsLookbackDays').value = data.indicator_swing_labels_lookback_days ?? data.indicator_lookback_days ?? 3;
      document.getElementById('cfgIndicatorHmaLookbackDays').value = data.indicator_hma_lookback_days ?? 0;
      document.getElementById('cfgIndicatorSmaLookbackDays').value = data.indicator_sma_lookback_days ?? 0;
      document.getElementById('cfgIndicatorTripleEmaLookbackDays').value = data.indicator_triple_ema_lookback_days ?? 0;
      document.getElementById('cfgIndicatorMfiLookbackDays').value = data.indicator_mfi_lookback_days ?? 0;
      document.getElementById('cfgIndicatorMacdLookbackDays').value = data.indicator_macd_lookback_days ?? 0;
      document.getElementById('cfgIndicatorBosConfirmation').value = data.indicator_bos_confirmation || 'Wicks';
      document.getElementById('cfgIndicatorHmaPeriod').value = data.indicator_hma_period ?? 20;
      document.getElementById('cfgIndicatorSmaPeriod').value = data.indicator_sma_period ?? 50;
      document.getElementById('cfgIndicatorTripleEmaPeriod').value = data.indicator_triple_ema_period ?? 20;
      document.getElementById('cfgIndicatorTripleEmaSlowPeriod').value = data.indicator_triple_ema_slow_period ?? 50;
      document.getElementById('cfgIndicatorMfiPeriod').value = data.indicator_mfi_period ?? 14;
      document.getElementById('cfgIndicatorMacdFastPeriod').value = data.indicator_macd_fast_period ?? 12;
      document.getElementById('cfgIndicatorMacdSlowPeriod').value = data.indicator_macd_slow_period ?? 26;
      document.getElementById('cfgIndicatorMacdSignalPeriod').value = data.indicator_macd_signal_period ?? 9;
      document.getElementById('cfgIndicatorSrPivotPeriod').value = data.indicator_sr_pivot_period ?? 10;
      document.getElementById('cfgIndicatorSrSource').value = data.indicator_sr_source || 'High/Low';
      document.getElementById('cfgIndicatorSrMaxPivots').value = data.indicator_sr_max_pivots ?? 20;
      document.getElementById('cfgIndicatorSrChannelWidthPercent').value = data.indicator_sr_channel_width_percent ?? 10;
      document.getElementById('cfgIndicatorSrMaxLevels').value = data.indicator_sr_max_levels ?? 5;
      document.getElementById('cfgIndicatorSrMinStrength').value = data.indicator_sr_min_strength ?? 2;
      applyChartSettingsToForm(data);
      document.getElementById('cfgIndicatorRisingColor').value = safeHexColor(data.indicator_bos_rising_color || data.indicator_rising_color, '#047857');
      document.getElementById('cfgIndicatorFallingColor').value = safeHexColor(data.indicator_bos_falling_color || data.indicator_falling_color, '#b42318');
      document.getElementById('cfgIndicatorSwingRisingColor').value = safeHexColor(data.indicator_swing_rising_color || data.indicator_rising_color, '#047857');
      document.getElementById('cfgIndicatorSwingFallingColor').value = safeHexColor(data.indicator_swing_falling_color || data.indicator_falling_color, '#b42318');
      document.getElementById('cfgIndicatorBoxHighColor').value = safeHexColor(data.indicator_box_high_color, '#b42318');
      document.getElementById('cfgIndicatorBoxLowColor').value = safeHexColor(data.indicator_box_low_color, '#047857');
      document.getElementById('cfgIndicatorHmaColor').value = safeHexColor(data.indicator_hma_color, '#7c3aed');
      document.getElementById('cfgIndicatorSmaColor').value = safeHexColor(data.indicator_sma_color, '#06b6d4');
      document.getElementById('cfgIndicatorTripleEmaColor').value = safeHexColor(data.indicator_triple_ema_color, '#d97706');
      document.getElementById('cfgIndicatorTripleEmaSlowColor').value = safeHexColor(data.indicator_triple_ema_slow_color, '#2563eb');
      document.getElementById('cfgIndicatorMfiColor').value = safeHexColor(data.indicator_mfi_color, '#db2777');
      document.getElementById('cfgIndicatorMacdColor').value = safeHexColor(data.indicator_macd_color, '#0ea5e9');
      document.getElementById('cfgIndicatorMacdSignalColor').value = safeHexColor(data.indicator_macd_signal_color, '#f97316');
      document.getElementById('cfgIndicatorMacdHistogramColor').value = safeHexColor(data.indicator_macd_histogram_color, '#64748b');
      document.getElementById('cfgIndicatorSrSupportColor').value = safeHexColor(data.indicator_sr_support_color, '#22c55e');
      document.getElementById('cfgIndicatorSrResistanceColor').value = safeHexColor(data.indicator_sr_resistance_color, '#ef4444');
      syncAllSwitchStates();
    }
    function indicatorSettingsPayload() {
      return {
        indicator_enabled: document.getElementById('cfgIndicatorEnabled').checked,
        indicator_show_bos_choch: document.getElementById('cfgIndicatorShowBosChoch').checked,
        indicator_show_boxes: document.getElementById('cfgIndicatorShowBoxes').checked,
        indicator_show_swing_labels: document.getElementById('cfgIndicatorShowSwingLabels').checked,
        indicator_show_hma: document.getElementById('cfgIndicatorShowHma').checked,
        indicator_show_sma: document.getElementById('cfgIndicatorShowSma').checked,
        indicator_show_triple_ema: document.getElementById('cfgIndicatorShowTripleEma').checked,
        indicator_show_mfi: document.getElementById('cfgIndicatorShowMfi').checked,
        indicator_show_macd: document.getElementById('cfgIndicatorShowMacd').checked,
        indicator_show_support_resistance: document.getElementById('cfgIndicatorShowSupportResistance').checked,
        indicator_swing_size: Number(document.getElementById('cfgIndicatorSwingSize').value),
        indicator_hhll_range: Number(document.getElementById('cfgIndicatorHhllRange').value),
        indicator_box_extend_candles: Number(document.getElementById('cfgIndicatorBoxExtendCandles').value),
        indicator_bos_choch_lookback_days: Number(document.getElementById('cfgIndicatorBosChochLookbackDays').value),
        indicator_boxes_lookback_days: Number(document.getElementById('cfgIndicatorBoxesLookbackDays').value),
        indicator_swing_labels_lookback_days: Number(document.getElementById('cfgIndicatorSwingLabelsLookbackDays').value),
        indicator_hma_lookback_days: Number(document.getElementById('cfgIndicatorHmaLookbackDays').value),
        indicator_sma_lookback_days: Number(document.getElementById('cfgIndicatorSmaLookbackDays').value),
        indicator_triple_ema_lookback_days: Number(document.getElementById('cfgIndicatorTripleEmaLookbackDays').value),
        indicator_mfi_lookback_days: Number(document.getElementById('cfgIndicatorMfiLookbackDays').value),
        indicator_macd_lookback_days: Number(document.getElementById('cfgIndicatorMacdLookbackDays').value),
        indicator_bos_confirmation: document.getElementById('cfgIndicatorBosConfirmation').value,
        indicator_hma_period: Number(document.getElementById('cfgIndicatorHmaPeriod').value),
        indicator_sma_period: Number(document.getElementById('cfgIndicatorSmaPeriod').value),
        indicator_triple_ema_period: Number(document.getElementById('cfgIndicatorTripleEmaPeriod').value),
        indicator_triple_ema_slow_period: Number(document.getElementById('cfgIndicatorTripleEmaSlowPeriod').value),
        indicator_mfi_period: Number(document.getElementById('cfgIndicatorMfiPeriod').value),
        indicator_macd_fast_period: Number(document.getElementById('cfgIndicatorMacdFastPeriod').value),
        indicator_macd_slow_period: Number(document.getElementById('cfgIndicatorMacdSlowPeriod').value),
        indicator_macd_signal_period: Number(document.getElementById('cfgIndicatorMacdSignalPeriod').value),
        indicator_sr_pivot_period: Number(document.getElementById('cfgIndicatorSrPivotPeriod').value),
        indicator_sr_source: document.getElementById('cfgIndicatorSrSource').value,
        indicator_sr_max_pivots: Number(document.getElementById('cfgIndicatorSrMaxPivots').value),
        indicator_sr_channel_width_percent: Number(document.getElementById('cfgIndicatorSrChannelWidthPercent').value),
        indicator_sr_max_levels: Number(document.getElementById('cfgIndicatorSrMaxLevels').value),
        indicator_sr_min_strength: Number(document.getElementById('cfgIndicatorSrMinStrength').value),
        indicator_bos_rising_color: document.getElementById('cfgIndicatorRisingColor').value,
        indicator_bos_falling_color: document.getElementById('cfgIndicatorFallingColor').value,
        indicator_swing_rising_color: document.getElementById('cfgIndicatorSwingRisingColor').value,
        indicator_swing_falling_color: document.getElementById('cfgIndicatorSwingFallingColor').value,
        indicator_box_high_color: document.getElementById('cfgIndicatorBoxHighColor').value,
        indicator_box_low_color: document.getElementById('cfgIndicatorBoxLowColor').value,
        indicator_hma_color: document.getElementById('cfgIndicatorHmaColor').value,
        indicator_sma_color: document.getElementById('cfgIndicatorSmaColor').value,
        indicator_triple_ema_color: document.getElementById('cfgIndicatorTripleEmaColor').value,
        indicator_triple_ema_slow_color: document.getElementById('cfgIndicatorTripleEmaSlowColor').value,
        indicator_mfi_color: document.getElementById('cfgIndicatorMfiColor').value,
        indicator_macd_color: document.getElementById('cfgIndicatorMacdColor').value,
        indicator_macd_signal_color: document.getElementById('cfgIndicatorMacdSignalColor').value,
        indicator_macd_histogram_color: document.getElementById('cfgIndicatorMacdHistogramColor').value,
        indicator_sr_support_color: document.getElementById('cfgIndicatorSrSupportColor').value,
        indicator_sr_resistance_color: document.getElementById('cfgIndicatorSrResistanceColor').value,
      };
    }
    function applyChartSettingsToForm(data) {
      document.getElementById('cfgChartCandleUpColor').value = safeHexColor(data.chart_candle_up_color, '#047857');
      document.getElementById('cfgChartCandleDownColor').value = safeHexColor(data.chart_candle_down_color, '#b42318');
      document.getElementById('cfgChartCandleNoChangeColor').value = safeHexColor(data.chart_candle_no_change_color, '#667085');
      document.getElementById('cfgChartCandleWickUpColor').value = safeHexColor(data.chart_candle_wick_up_color, safeHexColor(data.chart_candle_up_color, '#047857'));
      document.getElementById('cfgChartCandleWickDownColor').value = safeHexColor(data.chart_candle_wick_down_color, safeHexColor(data.chart_candle_down_color, '#b42318'));
      document.getElementById('cfgChartCandleWickNoChangeColor').value = safeHexColor(data.chart_candle_wick_no_change_color, safeHexColor(data.chart_candle_no_change_color, '#667085'));
      document.getElementById('cfgChartCandleBorderUpColor').value = safeHexColor(data.chart_candle_border_up_color, safeHexColor(data.chart_candle_up_color, '#047857'));
      document.getElementById('cfgChartCandleBorderDownColor').value = safeHexColor(data.chart_candle_border_down_color, safeHexColor(data.chart_candle_down_color, '#b42318'));
      document.getElementById('cfgChartCandleBorderNoChangeColor').value = safeHexColor(data.chart_candle_border_no_change_color, safeHexColor(data.chart_candle_no_change_color, '#667085'));
      document.getElementById('cfgChartGridColor').value = safeHexColor(data.chart_grid_color, '#d9e0ea');
      document.getElementById('cfgChartBackgroundColor').value = safeHexColor(data.chart_background_color, '#ffffff');
      updateChartSetupPreview();
    }
    function chartSettingsPayload() {
      return {
        chart_candle_up_color: document.getElementById('cfgChartCandleUpColor').value,
        chart_candle_down_color: document.getElementById('cfgChartCandleDownColor').value,
        chart_candle_no_change_color: document.getElementById('cfgChartCandleNoChangeColor').value,
        chart_candle_wick_up_color: document.getElementById('cfgChartCandleWickUpColor').value,
        chart_candle_wick_down_color: document.getElementById('cfgChartCandleWickDownColor').value,
        chart_candle_wick_no_change_color: document.getElementById('cfgChartCandleWickNoChangeColor').value,
        chart_candle_border_up_color: document.getElementById('cfgChartCandleBorderUpColor').value,
        chart_candle_border_down_color: document.getElementById('cfgChartCandleBorderDownColor').value,
        chart_candle_border_no_change_color: document.getElementById('cfgChartCandleBorderNoChangeColor').value,
        chart_grid_color: document.getElementById('cfgChartGridColor').value,
        chart_background_color: document.getElementById('cfgChartBackgroundColor').value,
      };
    }
    const CHART_SETUP_COLOR_INPUT_IDS = [
      'cfgChartCandleUpColor', 'cfgChartCandleDownColor', 'cfgChartCandleNoChangeColor',
      'cfgChartCandleWickUpColor', 'cfgChartCandleWickDownColor', 'cfgChartCandleWickNoChangeColor',
      'cfgChartCandleBorderUpColor', 'cfgChartCandleBorderDownColor', 'cfgChartCandleBorderNoChangeColor',
      'cfgChartGridColor', 'cfgChartBackgroundColor'
    ];
    function applyPreviewCandle(kind, bodyColor, wickColor, borderColor) {
      const candle = document.querySelector(`[data-candle-preview="${kind}"]`);
      if (!candle) return;
      const wick = candle.querySelector('.previewCandleWick');
      const body = candle.querySelector('.previewCandleBody');
      if (wick) wick.style.backgroundColor = wickColor;
      if (body) {
        body.style.backgroundColor = bodyColor;
        body.style.borderColor = borderColor;
      }
    }
    function updateChartSetupPreview() {
      const canvas = document.getElementById('chartPreviewCanvas');
      if (!canvas || !document.getElementById('cfgChartCandleUpColor')) return;
      const payload = chartSettingsPayload();
      canvas.style.backgroundColor = payload.chart_background_color;
      canvas.style.setProperty('--chart-preview-grid', payload.chart_grid_color);
      applyPreviewCandle('up', payload.chart_candle_up_color, payload.chart_candle_wick_up_color, payload.chart_candle_border_up_color);
      applyPreviewCandle('down', payload.chart_candle_down_color, payload.chart_candle_wick_down_color, payload.chart_candle_border_down_color);
      applyPreviewCandle('nochange', payload.chart_candle_no_change_color, payload.chart_candle_wick_no_change_color, payload.chart_candle_border_no_change_color);
    }
    function bindChartSetupPreviewInputs() {
      CHART_SETUP_COLOR_INPUT_IDS.forEach(id => {
        const input = document.getElementById(id);
        if (!input || input.dataset.previewBound === '1') return;
        input.dataset.previewBound = '1';
        input.addEventListener('input', updateChartSetupPreview);
        input.addEventListener('change', updateChartSetupPreview);
      });
    }
    async function loadChartSetupSettings() {
      const response = await fetch('/api/config-json', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = { ...latestConfig, ...data };
      applyChartSettingsToForm(data);
      bindChartSetupPreviewInputs();
      updateChartSetupPreview();
      document.getElementById('chartSetupStatus').textContent = 'Chart View Setup: Vorschau zeigt Koerper, Docht, Rand, Grid und Hintergrund.';
      openModal('chartSetupModal');
    }
    async function saveChartSetupSettings() {
      updateChartSetupPreview();
      const parsed = chartSettingsPayload();
      const response = await fetch('/api/config-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const result = await response.json();
      document.getElementById('chartSetupStatus').textContent = response.ok ? 'Chart-Farben gespeichert.' : (result.error || 'Fehler');
      if (response.ok) {
        latestConfig = { ...latestConfig, ...parsed };
        updateChartSetupPreview();
        updateKlineChartStyles();
        lastChartKey = '';
        if (currentView === 'chart') await loadChartData(true);
      }
    }
    async function loadIndicatorSettings() {
      await loadAgentSettings();
    }
    async function saveIndicatorSettings() {
      await saveAgentSettings();
    }
    const AGENT_SETTING_DEFS = [
      ['bos_choch', 'BOS / CHoCH Agent', 'liest BOS / CHoCH aus den Break-Lines', 'indicator_show_bos_choch', null],
      ['box', 'LL / HH Box Agent', 'liest aktive Strukturboxen', 'indicator_show_boxes', null],
      ['support_resistance', 'Support / Resistance Agent', 'liest dynamische Support-/Resistance-Level', 'indicator_show_support_resistance', null],
      ['swing_labels', 'HH / LH / HL / LL Agent', 'liest Swing Labels', 'indicator_show_swing_labels', null],
      ['hma', 'HMA Agent', 'liest HMA Trend / Momentum', 'indicator_show_hma', null],
      ['sma', 'SMA Agent', 'liest Preisposition und SMA-Neigung', 'indicator_show_sma', null],
      ['triple_ema', 'Triple EMA Agent', 'liest Fast / Slow Triple EMA', 'indicator_show_triple_ema', null],
      ['macd', 'MACD Agent', 'liest MACD Linie, Signal und Histogramm', 'indicator_show_macd', null],
      ['mfi', 'MFI Agent', 'liest Money Flow Index und Kapitalfluss', 'indicator_show_mfi', null],
      ['rsi', 'RSI Agent', 'liest RSI Momentum und Ueberdehnung', null, { id:'cfgAgentRsiPeriod', key:'agent_rsi_period', label:'RSI Period', fallback:14, help:'Anzahl Kerzen fuer die RSI-Berechnung.' }],
      ['vwap', 'VWAP Agent', 'liest Preis relativ zum VWAP-Fair-Value', null, { id:'cfgAgentVwapLookback', key:'agent_vwap_lookback_candles', label:'VWAP Lookback Kerzen', fallback:96, help:'Anzahl Kerzen fuer den VWAP-Kontext.' }],
      ['breakout_fakeout', 'Breakout / Fakeout Agent', 'liest Range-Ausbruch und Fakeout-Rejection', null, { id:'cfgAgentBreakoutFakeoutLookback', key:'agent_breakout_fakeout_lookback', label:'Range Lookback', fallback:20, help:'Anzahl Kerzen fuer die lokale Breakout-/Fakeout-Range.' }],
      ['volume', 'Volume Agent', 'liest Kerzenvolumen', null, { id:'cfgAgentVolumePeriod', key:'agent_volume_period', label:'Volume Period', fallback:20, help:'Anzahl Kerzen fuer den Volumen-Durchschnitt des Volume Agents.' }],
      ['volatility_regime', 'Volatility Regime Agent', 'liest ATR-Regime und Risiko-Umfeld', null, { id:'cfgAgentVolatilityAtrPeriod', key:'agent_volatility_atr_period', label:'ATR Period', fallback:14, help:'Anzahl Kerzen fuer die ATR-Berechnung des Volatilitaets-Agenten.' }],
      ['risk', 'Risk Agent', 'liest Pipeline- und Gate-Kontext', null, null],
    ];
    function indicatorShowInputId(configKey) {
      return {
        indicator_show_bos_choch: 'cfgIndicatorShowBosChoch',
        indicator_show_boxes: 'cfgIndicatorShowBoxes',
        indicator_show_support_resistance: 'cfgIndicatorShowSupportResistance',
        indicator_show_swing_labels: 'cfgIndicatorShowSwingLabels',
        indicator_show_hma: 'cfgIndicatorShowHma',
        indicator_show_sma: 'cfgIndicatorShowSma',
        indicator_show_triple_ema: 'cfgIndicatorShowTripleEma',
        indicator_show_macd: 'cfgIndicatorShowMacd',
        indicator_show_mfi: 'cfgIndicatorShowMfi',
      }[configKey] || null;
    }
    function syncLinkedIndicatorInputsFromAgents() {
      let anyLinkedAgentActive = false;
      for (const [key, _title, _info, linked] of AGENT_SETTING_DEFS) {
        if (!linked) continue;
        const agentInput = document.getElementById(`cfgAgent${key}Enabled`);
        const indicatorInputId = indicatorShowInputId(linked);
        const indicatorInput = indicatorInputId ? document.getElementById(indicatorInputId) : null;
        const enabled = !!agentInput?.checked;
        if (indicatorInput) indicatorInput.checked = enabled;
        setAgentIndicatorCollapsed(key, enabled);
        anyLinkedAgentActive = anyLinkedAgentActive || enabled;
      }
      const indicatorEnabled = document.getElementById('cfgIndicatorEnabled');
      if (indicatorEnabled) indicatorEnabled.checked = anyLinkedAgentActive;
      syncAllSwitchStates();
    }
    function defaultAgentColor(key) {
      const map = {
        bos_choch: '#2dd4bf',
        box: '#22c55e',
        support_resistance: '#60a5fa',
        swing_labels: '#a78bfa',
        hma: '#f59e0b',
        sma: '#38bdf8',
        triple_ema: '#facc15',
        macd: '#fb7185',
        mfi: '#c084fc',
        volume: '#94a3b8',
        risk: '#f87171'
      };
      return map[key] || '#2dd4bf';
    }
    function safeColor(value, fallback) {
      const text = String(value || '').trim();
      return /^#[0-9a-fA-F]{6}$/.test(text) ? text : fallback;
    }
    function agentColorValue(data, key) {
      return safeColor(data?.[`agent_${key}_color`], defaultAgentColor(key));
    }
    function agentColorForName(name) {
      const text = String(name || '').toLowerCase();
      const found = AGENT_SETTING_DEFS.find(([key, title]) => text.includes(key.replace(/_/g, ' ')) || text.includes(String(title).replace(/ agent/i, '').toLowerCase()));
      return agentColorValue(latestConfig || {}, found ? found[0] : '');
    }
    function setAgentSetupToggleState(button, open) {
      if (!button) return;
      button.classList.toggle('active', !!open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
      button.setAttribute('title', open ? 'Setup schließen' : 'Setup öffnen');
      button.setAttribute('aria-label', open ? 'Setup schließen' : 'Setup öffnen');
      button.innerHTML = '<span class="agentSetupIcon" aria-hidden="true">⚙</span>';
    }
    function bindAgentSetupToggles(root = document) {
      root.querySelectorAll('[data-agent-setup-toggle]').forEach(button => {
        setAgentSetupToggleState(button, button.classList.contains('active'));
        if (button.dataset.bound === 'true') return;
        button.dataset.bound = 'true';
        button.addEventListener('click', () => {
          const panel = document.getElementById(button.dataset.agentSetupToggle);
          const open = !!panel && !panel.classList.contains('open');
          document.querySelectorAll('.agentSetupPanel.open').forEach(item => item.classList.remove('open'));
          document.querySelectorAll('[data-agent-setup-toggle]').forEach(item => setAgentSetupToggleState(item, false));
          if (panel) panel.classList.toggle('open', open);
          setAgentSetupToggleState(button, open);
        });
      });
      root.querySelectorAll('[data-agent-setup-close]').forEach(button => {
        if (button.dataset.bound === 'true') return;
        button.dataset.bound = 'true';
        button.addEventListener('click', () => {
          const panel = button.closest('.agentSetupPanel');
          if (panel) panel.classList.remove('open');
          const toggle = document.querySelector(`[data-agent-setup-toggle="${panel?.id || ''}"]`);
          if (toggle) setAgentSetupToggleState(toggle, false);
        });
      });
    }
    function prepareAgentGroupHeaders(root = document) {
      root.querySelectorAll('.agentIndicatorGroup, .agentDirectGroup, .agentUtilityGroup').forEach(group => {
        if (group.dataset.agentGroupPrepared === 'true') return;
        const title = group.querySelector(':scope > h3');
        if (!title) return;
        const sectionKey = group.dataset.agentSection || title.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
        const indicatorButton = group.classList.contains('agentIndicatorGroup');
        const header = document.createElement('div');
        header.className = 'agentGroupHeader';
        const stateLabel = group.classList.contains('agentUtilityGroup') ? 'SETUP' : 'Bereit';
        header.innerHTML = `<div><h3>${escapeHtml(title.textContent)}</h3><div class="label agentGroupState" data-agent-group-state="${escapeHtml(sectionKey)}">${stateLabel}</div></div><button class="agentGroupToggle" type="button" data-agent-group-toggle="${escapeHtml(sectionKey)}" aria-expanded="false">${indicatorButton ? 'Indikator' : 'Ausblenden'}</button>`;
        title.replaceWith(header);
        group.dataset.agentGroupPrepared = 'true';
      });
    }
    function bindAgentGroupToggles(root = document) {
      prepareAgentGroupHeaders(root);
      root.querySelectorAll('[data-agent-group-toggle]').forEach(button => {
        if (button.dataset.bound === 'true') return;
        button.dataset.bound = 'true';
        button.addEventListener('click', () => {
          const group = button.closest('.agentIndicatorGroup, .agentDirectGroup, .agentUtilityGroup');
          if (!group) return;
          if (group.classList.contains('agentIndicatorGroup')) {
            const open = !group.classList.contains('indicator-settings-open');
            group.classList.toggle('indicator-settings-open', open);
            button.setAttribute('aria-expanded', open ? 'true' : 'false');
            button.textContent = open ? 'Indikator ▲' : 'Indikator';
            return;
          }
          const collapsed = !group.classList.contains('agent-group-collapsed');
          group.classList.toggle('agent-group-collapsed', collapsed);
          button.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
          button.textContent = collapsed ? 'Einblenden' : 'Ausblenden';
        });
      });
    }
    function setAgentCardColor(key, color) {
      const safe = safeColor(color, defaultAgentColor(key));
      const group = document.querySelector(`[data-agent-section="${key}"]`);
      const inline = document.getElementById(`agentInline_${key}`);
      const panel = document.getElementById(`agentSetupPanel_${key.replace(/[^a-zA-Z0-9]/g, '_')}`);
      const line = document.getElementById(`cfgAgent${key}ColorLine`);
      [group, inline, panel].forEach(item => {
        if (item) item.style.setProperty('--agent-card-color', safe);
      });
      if (line) line.style.background = safe;
    }
    function setAgentGroupState(key, enabled) {
      const state = document.querySelector(`[data-agent-group-state="${key}"]`);
      if (!state) return;
      state.textContent = enabled ? 'AKTIV' : 'AUS';
      state.classList.toggle('active', !!enabled);
    }
    function syncUtilityAgentGroupStates() {
      const brainActive = document.getElementById('cfgBrainEnabled')?.checked !== false;
      const ollamaActive = !!document.getElementById('cfgOllamaEnabled')?.checked || !!document.getElementById('cfgBrainLlmLayer')?.checked;
      setAgentGroupState('brain_ceo', brainActive);
      setAgentGroupState('ollama_audit', ollamaActive);
    }
    function agentControlMarkup(key, title, info, linked, period, data) {
      const prefix = `agent_${key}`;
      const linkedText = linked ? 'Chart-Indikator folgt Agent aktiv' : 'Direkter Agent ohne Chart-Indikator-Pflicht';
      const safeKey = key.replace(/[^a-zA-Z0-9]/g, '_');
      const periodField = period
        ? `<div><label class="fieldLabel" for="${period.id}">${escapeHtml(period.label)} <button class="helpButton" type="button" data-help-target="agent_${safeKey}_period_help">?</button></label><input id="${period.id}" type="number" min="2" max="500" step="1" value="${Number(data[period.key] ?? period.fallback)}"><div id="agent_${safeKey}_period_help" class="helpText">${escapeHtml(period.help)}</div></div>`
        : '';
      const collapseHint = linked ? '<div class="agentCollapsedHint fullWidth">Agent und Chart-Indikator sind aus.</div>' : '';
      const color = agentColorValue(data, key);
      return `
        <div id="cfgAgent${key}ColorLine" class="agentCardColorLine fullWidth" style="background:${escapeHtml(color)}"></div>
        <div class="agentControlHeader fullWidth">
          <div><div class="switchLine"><input id="cfgAgent${key}Enabled" data-agent-enabled="${prefix}" class="switchInput" type="checkbox"><label class="fieldLabel" for="cfgAgent${key}Enabled">Agent aktiv <button class="helpButton" type="button" data-help-target="agent_${safeKey}_enabled_help">?</button></label><span id="cfgAgent${key}EnabledState" class="switchState">Aus</span></div><div id="agent_${safeKey}_enabled_help" class="helpText">Schaltet diesen Agenten ein oder aus. Bei Aus liefert er keine aktive Bewertung.</div></div>
          <button class="agentSetupToggle" type="button" data-agent-setup-toggle="agentSetupPanel_${safeKey}" aria-expanded="false" aria-label="Setup öffnen" title="Setup öffnen"><span class="agentSetupIcon" aria-hidden="true">⚙</span></button>
        </div>
        <div id="agentSetupPanel_${safeKey}" class="agentSetupPanel fullWidth" style="--agent-card-color:${escapeHtml(color)}">
          <div class="agentSetupPopupHeader"><strong>${escapeHtml(title)} Setup</strong><button class="agentSetupClose" type="button" data-agent-setup-close>Schließen</button></div>
          ${collapseHint}
          <div><label class="fieldLabel" for="cfgAgent${key}Weight">Gewichtung <button class="helpButton" type="button" data-help-target="agent_${safeKey}_weight_help">?</button></label><input id="cfgAgent${key}Weight" type="number" min="0" max="5" step="0.1"><div id="agent_${safeKey}_weight_help" class="helpText">Multiplikator fuer den Agenten-Score. 1 = normal, 0 = keine Wirkung, ueber 1 = staerkerer Einfluss.</div></div>
          <div><label class="fieldLabel" for="cfgAgent${key}MinScore">Mindestscore <button class="helpButton" type="button" data-help-target="agent_${safeKey}_min_help">?</button></label><input id="cfgAgent${key}MinScore" type="number" min="0" max="100" step="1"><div id="agent_${safeKey}_min_help" class="helpText">Unter diesem Score wird das Agentensignal auf neutral gesetzt.</div></div>
          ${periodField}
          <div class="fullWidth"><div class="switchLine"><input id="cfgAgent${key}Blocking" data-agent-blocking="${prefix}" class="switchInput" type="checkbox"><label class="fieldLabel" for="cfgAgent${key}Blocking">blockierend wenn keine Freigabe <button class="helpButton" type="button" data-help-target="agent_${safeKey}_blocking_help">?</button></label><span id="cfgAgent${key}BlockingState" class="switchState">Info</span></div><div id="agent_${safeKey}_blocking_help" class="helpText">Wenn aktiv, kann dieser Agent einen Trade blockieren, sobald seine Mindestanforderung nicht erfuellt ist.</div></div>
          <div class="agentColorRow fullWidth">
            <div><label class="fieldLabel" for="cfgAgent${key}Color">Agent-Farbe</label><input id="cfgAgent${key}Color" type="color" value="${escapeHtml(color)}"></div>
            <div class="agentColorPreview" id="cfgAgent${key}ColorPreview"></div>
          </div>
          <div class="label fullWidth">${escapeHtml(info)} · ${escapeHtml(linkedText)}</div>
        </div>`;
    }
    function prepareAgentIndicatorGroups() {
      document.querySelectorAll('.agentIndicatorGroup .settingsGroupGrid').forEach(grid => {
        Array.from(grid.children).forEach(child => {
          if (child.classList.contains('agentInlineControls')) return;
          if (child.classList.contains('agentSetupPanel')) return;
          if (child.matches('input[hidden], span[hidden]')) return;
          child.classList.add('indicatorDetail');
        });
      });
    }
    function setAgentIndicatorCollapsed(key, enabled) {
      const group = document.querySelector(`.agentIndicatorGroup[data-agent-section="${key}"]`);
      if (!group) return;
      group.classList.toggle('agent-collapsed', !enabled);
      group.classList.toggle('agent-active', !!enabled);
      setAgentGroupState(key, enabled);
    }
    function renderInlineAgentSettings(data) {
      for (const [key, title, info, linked, period] of AGENT_SETTING_DEFS) {
        if (!linked) continue;
        const target = document.getElementById(`agentInline_${key}`);
        if (!target) continue;
        const color = agentColorValue(data, key);
        target.style.setProperty('--agent-card-color', color);
        const group = document.querySelector(`.agentIndicatorGroup[data-agent-section="${key}"]`);
        if (group) group.style.setProperty('--agent-card-color', color);
        target.innerHTML = agentControlMarkup(key, title, info, linked, period, data);
      }
      prepareAgentIndicatorGroups();
      prepareAgentGroupHeaders(document.getElementById('agentSetupView') || document);
      syncUtilityAgentGroupStates();
    }
    function renderAgentSettingsGroups(data) {
      const wrap = document.getElementById('agentSettingsGroups');
      renderInlineAgentSettings(data);
      const directAgentHtml = AGENT_SETTING_DEFS
        .filter(([_key, _title, _info, linked]) => !linked)
        .map(([key, title, info, linked, period]) => {
          const color = agentColorValue(data, key);
          return `<div class="settingsGroup agentDirectGroup" data-agent-section="${escapeHtml(key)}" style="--agent-card-color:${escapeHtml(color)}">
            <h3>${escapeHtml(title)}</h3>
            <div class="settingsGroupGrid">
              ${agentControlMarkup(key, title, info, linked, period, data)}
            </div>
          </div>`;
        })
        .join('');
      wrap.innerHTML = directAgentHtml ? `<div class="settingsGroup"><h3>Direkte Agenten ohne Chart-Indikator</h3><div class="label">Diese Agenten bleiben sichtbar, weil sie keinen eigenen Preis-Indikator im Chart haben.</div></div>${directAgentHtml}` : '';
      for (const [key] of AGENT_SETTING_DEFS) {
        document.getElementById(`cfgAgent${key}Enabled`).checked = data[`agent_${key}_enabled`] !== false;
        document.getElementById(`cfgAgent${key}Weight`).value = data[`agent_${key}_weight`] ?? 1;
        document.getElementById(`cfgAgent${key}MinScore`).value = data[`agent_${key}_min_score`] ?? 0;
        document.getElementById(`cfgAgent${key}Blocking`).checked = data[`agent_${key}_blocking`] === true;
        const colorInput = document.getElementById(`cfgAgent${key}Color`);
        const colorPreview = document.getElementById(`cfgAgent${key}ColorPreview`);
        if (colorInput) {
          colorInput.value = agentColorValue(data, key);
          setAgentCardColor(key, colorInput.value);
          if (colorPreview) colorPreview.style.background = colorInput.value;
          colorInput.addEventListener('input', () => {
            if (colorPreview) colorPreview.style.background = colorInput.value;
            setAgentCardColor(key, colorInput.value);
          });
        }
      }
      syncLinkedIndicatorInputsFromAgents();
      for (const [key] of AGENT_SETTING_DEFS) {
        const enabled = document.getElementById(`cfgAgent${key}Enabled`)?.checked !== false;
        const direct = document.querySelector(`.agentDirectGroup[data-agent-section="${key}"]`);
        if (direct) {
          direct.classList.toggle('agent-active', !!enabled);
          setAgentGroupState(key, enabled);
        }
      }
      document.querySelectorAll('[data-agent-enabled],[data-agent-blocking]').forEach(input => {
        input.addEventListener('change', () => {
          syncLinkedIndicatorInputsFromAgents();
          for (const [key] of AGENT_SETTING_DEFS) {
            const enabled = document.getElementById(`cfgAgent${key}Enabled`)?.checked !== false;
            const direct = document.querySelector(`.agentDirectGroup[data-agent-section="${key}"]`);
            if (direct) direct.classList.toggle('agent-active', !!enabled);
            setAgentGroupState(key, enabled);
          }
          syncAllSwitchStates();
        });
      });
      bindHelpButtons(document.getElementById('agentSetupView') || document);
      bindAgentSetupToggles(document.getElementById('agentSetupView') || document);
      bindAgentGroupToggles(document.getElementById('agentSetupView') || document);
      syncUtilityAgentGroupStates();
    }
    async function loadAgentSettings() {
      const response = await fetch('/api/settings', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data;
      applyIndicatorSettingsToForm(data);
      document.getElementById('cfgBrainEnabled').checked = data.brain_enabled !== false;
      document.getElementById('cfgBrainMinScore').value = data.brain_min_score ?? 58;
      document.getElementById('cfgBrainMinScoreGap').value = data.brain_min_score_gap ?? 18;
      document.getElementById('cfgBrainMinAlignment').value = data.brain_min_agent_alignment ?? 2;
      document.getElementById('cfgBrainMemoryMinCount').value = data.brain_memory_min_count ?? 3;
      document.getElementById('cfgBrainEntryBoxOffset').value = data.brain_entry_box_offset ?? 0.35;
      document.getElementById('cfgBrainRequireBox').checked = data.brain_require_box_for_trade === true;
      document.getElementById('cfgBrainLlmLayer').checked = data.brain_llm_layer_enabled === true;
      document.getElementById('cfgOllamaEnabled').checked = data.ollama_enabled === true;
      document.getElementById('cfgOllamaBaseUrl').value = data.ollama_base_url || 'http://127.0.0.1:11434';
      document.getElementById('cfgOllamaModel').value = data.ollama_model || 'qwen2.5:3b';
      document.getElementById('cfgOllamaTimeout').value = data.ollama_timeout_seconds ?? 5;
      document.getElementById('cfgOllamaMaxPrompt').value = data.ollama_max_prompt_chars ?? 4000;
      document.getElementById('cfgOllamaTemperature').value = data.ollama_temperature ?? 0;
      document.getElementById('cfgOllamaBlockHint').checked = data.ollama_block_hint_enabled === true;
      document.getElementById('cfgAgentShowOffline').checked = data.agent_show_offline_agents !== false;
      renderAgentSettingsGroups(data);
      syncLinkedIndicatorInputsFromAgents();
      syncAllSwitchStates();
      bindAgentGroupToggles(document.getElementById('agentSetupView') || document);
      syncUtilityAgentGroupStates();
      document.getElementById('agentSettingsStatus').textContent = '';
    }
    async function saveAgentSettings() {
      syncLinkedIndicatorInputsFromAgents();
      const parsed = {
        ...indicatorSettingsPayload(),
        trade_decision_mode: 'brain',
        brain_enabled: document.getElementById('cfgBrainEnabled').checked,
        brain_min_score: Number(document.getElementById('cfgBrainMinScore').value),
        brain_min_score_gap: Number(document.getElementById('cfgBrainMinScoreGap').value),
        brain_min_agent_alignment: Number(document.getElementById('cfgBrainMinAlignment').value),
        brain_memory_min_count: Number(document.getElementById('cfgBrainMemoryMinCount').value),
        brain_entry_box_offset: Number(document.getElementById('cfgBrainEntryBoxOffset').value),
        brain_require_box_for_trade: document.getElementById('cfgBrainRequireBox').checked,
        brain_llm_layer_enabled: document.getElementById('cfgBrainLlmLayer').checked,
        ollama_enabled: document.getElementById('cfgOllamaEnabled').checked,
        ollama_base_url: document.getElementById('cfgOllamaBaseUrl').value.trim(),
        ollama_model: document.getElementById('cfgOllamaModel').value.trim(),
        ollama_timeout_seconds: Number(document.getElementById('cfgOllamaTimeout').value),
        ollama_max_prompt_chars: Number(document.getElementById('cfgOllamaMaxPrompt').value),
        ollama_temperature: Number(document.getElementById('cfgOllamaTemperature').value),
        ollama_block_hint_enabled: document.getElementById('cfgOllamaBlockHint').checked,
        agent_show_offline_agents: document.getElementById('cfgAgentShowOffline').checked,
      };
      for (const [key, _title, _info, linked, period] of AGENT_SETTING_DEFS) {
        const agentEnabled = document.getElementById(`cfgAgent${key}Enabled`).checked;
        parsed[`agent_${key}_enabled`] = agentEnabled;
        if (linked) parsed[linked] = agentEnabled;
        parsed[`agent_${key}_weight`] = Number(document.getElementById(`cfgAgent${key}Weight`).value);
        parsed[`agent_${key}_min_score`] = Number(document.getElementById(`cfgAgent${key}MinScore`).value);
        parsed[`agent_${key}_blocking`] = document.getElementById(`cfgAgent${key}Blocking`).checked;
        parsed[`agent_${key}_color`] = safeColor(document.getElementById(`cfgAgent${key}Color`)?.value, defaultAgentColor(key));
        if (period) {
          parsed[period.key] = Number(document.getElementById(period.id)?.value || latestConfig[period.key] || period.fallback);
          if (key === 'volatility_regime') parsed.agent_volatility_lookback = Number(latestConfig.agent_volatility_lookback || 50);
        }
      }
      parsed.indicator_enabled = AGENT_SETTING_DEFS.some(([key, _title, _info, linked]) => linked && parsed[`agent_${key}_enabled`]);
      parsed.agent_sma_period = parsed.indicator_sma_period;
      parsed.agent_mfi_period = parsed.indicator_mfi_period;
      const response = await fetch('/api/config-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const result = await response.json();
      document.getElementById('agentSettingsStatus').textContent = response.ok ? 'Gespeichert.' : (result.error || 'Fehler');
      if (response.ok) {
        latestConfig = { ...latestConfig, ...parsed };
        updateChartSetupPreview();
        updateKlineChartStyles();
        lastChartKey = '';
        await refresh();
        if (currentView === 'chart') await loadChartData(true);
      }
    }
    async function saveSettings() {
      persistCurrentTradeSizeDraft();
      const payload = {
        paper_trading_enabled: document.getElementById('paperToggle').checked,
        trade_size_mode: document.getElementById('sizeMode').value,
        trade_size_usd: Number(document.getElementById('sizeUsd').value || 0),
        trade_size_asset: Number(document.getElementById('sizeAsset').value || 0),
        trade_sizes_by_symbol: localTradeSizes
      };
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      document.getElementById('settingsStatus').textContent = response.ok ? 'Gespeichert' : (result.error || 'Fehler');
      if (response.ok) {
        closeModal('tradingModal');
        await refresh();
      }
    }
    async function botControl(action) {
      const dropdownValue = document.getElementById('assetFilter')?.value || selectedAssetValue();
      const resetSymbol = dropdownValue === ALL_ASSETS_VALUE ? null : dropdownValue;
      const resetLabel = resetSymbol || 'Gesamt';
      if (action === 'reset') {
        const scopeText = resetSymbol
          ? `nur fuer ${resetSymbol}`
          : 'fuer alle Assets';
        const ok = window.confirm(`Reset ${scopeText} wirklich ausfuehren? Das loescht Paper-Trades und Lernspeicher ${scopeText} und setzt den Scanner auf Stop.`);
        if (!ok) return;
      }
      const pendingLabels = {
        start: 'Scanner wird gestartet...',
        stop: 'Scanner wird gestoppt...',
        reset: `Reset ${resetLabel} in Arbeit...`
      };
      setControlMessage(pendingLabels[action] || 'Aktion in Arbeit...', 'warn');
      const response = await fetch('/api/bot-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, symbol: action === 'reset' ? resetSymbol : null })
      });
      const result = await response.json();
      const doneLabels = {
        start: 'Scanner gestartet',
        stop: 'Scanner gestoppt',
        reset: `Speicher ${resetLabel} zurueckgesetzt`
      };
      setControlMessage(response.ok ? (doneLabels[action] || 'Aktion ausgefuehrt') : (result.error || 'Fehler'), response.ok ? 'ok' : 'warn');
      await refresh();
    }
    async function reloadDashboardData() {
      flashButton('reloadBot');
      setControlMessage('Reload in Arbeit...', 'warn');
      lastChartKey = '';
      await refresh();
      if (currentView === 'chart') await loadChartData(true);
      setControlMessage('Reload abgeschlossen', 'ok');
    }
    function updateSizeVisibility() {
      const mode = document.getElementById('sizeMode').value;
      document.getElementById('sizeUsdWrap').style.display = mode === 'usd' ? 'block' : 'none';
      document.getElementById('sizeAssetWrap').style.display = mode === 'asset' ? 'block' : 'none';
    }
    function renderTradeSizeAssetSelector(cfg) {
      const wrap = document.getElementById('tradeSizeAssetSelectorWrap');
      const select = document.getElementById('tradeSizeAssetSelector');
      const isMulti = cfg.observer_asset_mode === 'multi';
      wrap.style.display = isMulti ? 'block' : 'none';
      const symbols = isMulti ? (cfg.symbols || []) : [(cfg.symbols || [selectedAsset || 'BTCUSDT'])[0]];
      const watchlist = cfg.watchlist_assets || [];
      select.innerHTML = symbols.map(symbol => {
        const item = watchlist.find(asset => asset.symbol === symbol);
        return `<option value="${symbol}">${item ? item.label : symbol}</option>`;
      }).join('');
      if (selectedAsset && symbols.includes(selectedAsset)) select.value = selectedAsset;
      activeTradeSizeSymbol = select.value || symbols[0] || null;
    }
    function persistCurrentTradeSizeDraft(symbolOverride = null) {
      const selector = document.getElementById('tradeSizeAssetSelector');
      const symbol = symbolOverride || activeTradeSizeSymbol || selector.value || (latestConfig.symbols || [selectedAsset || 'BTCUSDT'])[0];
      if (!symbol) return;
      localTradeSizes[symbol] = {
        mode: document.getElementById('sizeMode').value,
        usd: Number(document.getElementById('sizeUsd').value || 0),
        asset: Number(document.getElementById('sizeAsset').value || 0)
      };
    }
    function loadTradeSizeForSelectedAsset() {
      const selector = document.getElementById('tradeSizeAssetSelector');
      const symbol = selector.value || (latestConfig.symbols || [selectedAsset || 'BTCUSDT'])[0];
      activeTradeSizeSymbol = symbol;
      const size = localTradeSizes[symbol] || {
        mode: latestConfig.trade_size_mode || 'usd',
        usd: latestConfig.trade_size_usd || 0,
        asset: latestConfig.trade_size_asset || 0
      };
      document.getElementById('sizeMode').value = size.mode || 'usd';
      document.getElementById('sizeUsd').value = fmt(size.usd, 0);
      document.getElementById('sizeAsset').value = fmt(size.asset, 0);
      updateSizeVisibility();
    }
    async function loadTradingSettings() {
      const response = await fetch('/api/status', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data.config || {};
      document.getElementById('paperToggle').checked = !!latestConfig.paper_trading_enabled;
      syncSwitchState('paperToggle', 'paperToggleState', 'Aktiv', 'Aus', 'paperToggleBox');
      localTradeSizes = JSON.parse(JSON.stringify(latestConfig.trade_sizes_by_symbol || {}));
      renderTradeSizeAssetSelector(latestConfig);
      loadTradeSizeForSelectedAsset();
      openModal('tradingModal');
    }
    async function openSetupFile(target) {
      const response = await fetch('/api/open-setup-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
      });
      const result = await response.json();
      document.getElementById('settingsStatus').textContent = response.ok ? `Geoeffnet: ${result.opened}` : (result.error || 'Fehler');
    }
    function openModal(id) { document.getElementById(id).classList.add('open'); }
    function switchReplayTab(tabName) {
      const safeTab = ['overview', 'trades', 'memory', 'history', 'compare', 'rules'].includes(tabName) ? tabName : 'overview';
      document.querySelectorAll('[data-replay-tab]').forEach(button => {
        button.classList.toggle('active', button.dataset.replayTab === safeTab);
      });
      document.querySelectorAll('.replayTabPanel').forEach(panel => panel.classList.remove('active'));
      const panel = document.getElementById(`replayTab${safeTab.charAt(0).toUpperCase()}${safeTab.slice(1)}`);
      if (panel) panel.classList.add('active');
    }
    function openReplayView() {
      syncReplayAssetOptions(latestConfig || {});
      renderReplayRuleWeightStatus();
      switchReplayTab('overview');
      setView(currentView === 'replay' ? 'dashboard' : 'replay');
      if (currentView === 'replay') loadReplayHistory();
    }
    function closeModal(id) { document.getElementById(id).classList.remove('open'); }
    async function loadApiSettings() {
      const response = await fetch('/api/env-settings', { cache: 'no-store' });
      const data = await response.json();
      document.getElementById('apiBaseUrl').value = data.base_url || 'https://api.phemex.com';
      document.getElementById('apiKey').value = '';
      document.getElementById('apiSecret').value = '';
      document.getElementById('apiPreview').textContent =
        `Key: ${data.api_key_present ? data.api_key_preview : 'nicht gesetzt'} | Secret: ${data.api_secret_present ? data.api_secret_preview : 'nicht gesetzt'}`;
      document.getElementById('apiStatus').textContent = '';
      openModal('apiModal');
    }
    async function saveApiSettings() {
      const payload = {
        base_url: document.getElementById('apiBaseUrl').value,
        api_key: document.getElementById('apiKey').value,
        api_secret: document.getElementById('apiSecret').value
      };
      const response = await fetch('/api/env-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      document.getElementById('apiStatus').textContent = response.ok ? 'Gespeichert und im laufenden Bot aktualisiert.' : (result.error || 'Fehler');
      if (response.ok) {
        document.getElementById('apiPreview').textContent =
          `Key: ${result.api_key_present ? result.api_key_preview : 'nicht gesetzt'} | Secret: ${result.api_secret_present ? result.api_secret_preview : 'nicht gesetzt'}`;
        document.getElementById('apiKey').value = '';
        document.getElementById('apiSecret').value = '';
        await refresh();
      }
    }
    async function loadStrategySettings() {
      const response = await fetch('/api/strategy-md', { cache: 'no-store' });
      const data = await response.json();
      document.getElementById('strategyPath').textContent = response.ok ? data.path : '';
      document.getElementById('strategyContent').value = response.ok ? data.content : '';
      document.getElementById('strategyStatus').textContent = response.ok ? '' : (data.error || 'Fehler');
      openModal('strategyModal');
    }
    async function loadConfigSettings() {
      const response = await fetch('/api/config-json', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data;
      document.getElementById('cfgUiTheme').value = data.ui_theme === 'dark' ? 'dark' : 'light';
      document.getElementById('cfgAssetMode').value = data.observer_asset_mode || 'single';
      localMinProfitFractions = {};
      Object.entries(data.min_net_profit_fraction_by_symbol || {}).forEach(([symbol, value]) => {
        localMinProfitFractions[symbol] = percentInputValue(value);
      });
      localMaxSlDistanceFractions = {};
      Object.entries(data.max_sl_distance_fraction_by_symbol || {}).forEach(([symbol, value]) => {
        localMaxSlDistanceFractions[symbol] = percentInputValue(value);
      });
      renderConfigSingleAsset(data);
      document.getElementById('cfgMaxOpenTotal').value = data.max_open_trades_total ?? 3;
      document.getElementById('cfgMaxOpenAsset').value = data.max_open_trades_per_asset ?? 1;
      document.getElementById('cfgCorrelationBlock').checked = data.block_same_direction_correlated_trades !== false;
      renderConfigWatchlist(data);
      document.getElementById('cfgSignalTf').value = String(data.signal_timeframe_seconds ?? 900);
      document.getElementById('cfgConfirmTf').value = String(data.confirmation_timeframe_seconds ?? 300);
      updateMultiAssetVisibility();
      document.getElementById('cfgPhemexPoll').value = data.phemex_poll_seconds ?? data.poll_seconds ?? 20;
      document.getElementById('cfgSystemLoop').value = data.system_loop_seconds ?? 1;
      document.getElementById('cfgKlineLimit').value = data.kline_limit ?? 500;
      const riskUnit = data.risk_unit ?? 1;
      document.getElementById('cfgRiskUnit').value = riskUnit;
      document.getElementById('cfgRewardRisk').value = (data.reward_risk ?? 2) * riskUnit;
      document.getElementById('cfgEcoStopMode').value = data.stop_loss_mode === 'atr' ? 'atr' : 'structure';
      document.getElementById('cfgEcoStopBuffer').value = data.stop_loss_buffer_percent ?? 0;
      document.getElementById('cfgAtrPeriod').value = data.stop_loss_atr_period ?? 14;
      document.getElementById('cfgAtrMultiplier').value = data.stop_loss_atr_multiplier ?? 1.5;
      updateStopLossVisibility();
      renderConfigProfitAssetSelector(data);
      loadMinProfitForSelectedAsset(data);
      updateRewardRiskHint();
      updateMinNetProfitPreview(true);
      document.getElementById('configStatus').textContent = '';
      openModal('configModal');
    }
    async function loadStrategyConfigSettings() {
      const response = await fetch('/api/config-json', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data;
      document.getElementById('cfgEntryMode').value = data.entry_mode || 'edge';
      document.getElementById('cfgStopMode').value = data.stop_loss_mode === 'atr' ? 'atr' : 'structure';
      document.getElementById('cfgStopPercent').value = data.stop_loss_percent ?? 0.25;
      document.getElementById('cfgStopBuffer').value = data.stop_loss_buffer_percent ?? 0;
      const strategyAtrPeriod = document.getElementById('cfgStrategyAtrPeriod');
      const strategyAtrMultiplier = document.getElementById('cfgStrategyAtrMultiplier');
      if (strategyAtrPeriod) strategyAtrPeriod.value = data.stop_loss_atr_period ?? 14;
      if (strategyAtrMultiplier) strategyAtrMultiplier.value = data.stop_loss_atr_multiplier ?? 1.5;
      updateStopLossVisibility();
      document.getElementById('cfgMinSweep').value = data.min_sweep_percent_of_prev_range ?? 0.05;
      document.getElementById('cfgStructureLookback').value = data.structure_lookback_candles ?? 80;
      document.getElementById('cfgPivotStrength').value = data.structure_pivot_strength ?? 2;
      document.getElementById('cfgRejectionMode').value = data.sweep_rejection_mode || 'close';
      document.getElementById('cfgEntrySearchCandles').value = data.swing_reaction_lookback_candles ?? data.entry_search_confirmation_candles ?? 5;
      document.getElementById('cfgSwingLookback').value = data.swing_lookback_candles ?? data.structure_lookback_candles ?? 80;
      document.getElementById('cfgSwingPivot').value = data.swing_pivot_strength ?? data.structure_pivot_strength ?? 2;
      document.getElementById('cfgSwingPadding').value = data.swing_zone_padding_fraction ?? 0.0005;
      document.getElementById('cfgDipWick').value = data.dip_rejection_wick_ratio ?? 0.25;
      updateEntrySearchHelp();
      document.getElementById('cfgMinBody').value = data.dip_rejection_body_ratio ?? 0.2;
      document.getElementById('cfgTrendFilter').checked = !!data.use_trend_filter;
      document.getElementById('cfgTrendMode').value = data.trend_filter_mode || 'day_candle';
      document.getElementById('cfgTrendEmaSource').value = data.trend_ema_source || 'trade_timeframe';
      document.getElementById('cfgTrendEma').value = data.trend_ema_period ?? 50;
      syncAllSwitchStates();
      updateEmaConfigVisibility();
      document.getElementById('strategyConfigStatus').textContent = '';
      openModal('strategyConfigModal');
    }
    function renderConfigSingleAsset(data) {
      const watchlist = data.watchlist_assets || [
        {label:'XRPUSDT', symbol:'XRPUSDT'}, {label:'KASUSDT', symbol:'KASUSDT'}, {label:'PTUSDT', symbol:'PTUSDT'}, {label:'BTCUSDT', symbol:'BTCUSDT'}, {label:'ETHUSDT', symbol:'ETHUSDT'}, {label:'SOLUSDT', symbol:'SOLUSDT'}, {label:'LINKUSDT', symbol:'LINKUSDT'}, {label:'BCHUSDT', symbol:'BCHUSDT'}, {label:'BNBUSDT', symbol:'BNBUSDT'}, {label:'PAXGUSDT', symbol:'PAXGUSDT'}
      ];
      const select = document.getElementById('cfgSingleAsset');
      select.innerHTML = watchlist.map(asset => `<option value="${asset.symbol}">${asset.label}</option>`).join('');
      select.value = (data.symbols || [watchlist[0]?.symbol])[0] || 'BTCUSDT';
    }
    function renderConfigWatchlist(data) {
      const active = new Set(data.symbols || []);
      const watchlist = (data.watchlist_assets || [
        {label:'XRPUSDT', symbol:'XRPUSDT'}, {label:'KASUSDT', symbol:'KASUSDT'}, {label:'PTUSDT', symbol:'PTUSDT'}, {label:'BTCUSDT', symbol:'BTCUSDT'}, {label:'ETHUSDT', symbol:'ETHUSDT'}, {label:'SOLUSDT', symbol:'SOLUSDT'}, {label:'LINKUSDT', symbol:'LINKUSDT'}, {label:'BCHUSDT', symbol:'BCHUSDT'}, {label:'BNBUSDT', symbol:'BNBUSDT'}, {label:'PAXGUSDT', symbol:'PAXGUSDT'}
      ]);
      document.getElementById('cfgWatchlistBox').innerHTML =
        '<label>Watchlist Assets</label><div class="watchlistChecks">' +
        watchlist.map(asset => `<label><input type="checkbox" data-cfg-symbol="${asset.symbol}" ${active.has(asset.symbol) ? 'checked' : ''}>${asset.label}</label>`).join('') +
        '</div>';
      document.querySelectorAll('[data-cfg-symbol]').forEach(input => {
        input.addEventListener('change', () => {
          persistCurrentMinProfitDraft();
          renderConfigProfitAssetSelector(latestConfig);
          loadMinProfitForSelectedAsset(latestConfig);
          updateMinNetProfitPreview(true);
        });
      });
    }
    function currentConfigSymbols() {
      const checkedSymbols = Array.from(document.querySelectorAll('[data-cfg-symbol]:checked')).map(input => input.dataset.cfgSymbol);
      const singleAsset = document.getElementById('cfgSingleAsset').value;
      return document.getElementById('cfgAssetMode').value === 'single'
        ? [singleAsset]
        : Array.from(new Set([...checkedSymbols, singleAsset]));
    }
    function renderConfigProfitAssetSelector(data) {
      const wrap = document.getElementById('cfgProfitAssetWrap');
      const select = document.getElementById('cfgProfitAsset');
      const isMulti = document.getElementById('cfgAssetMode').value === 'multi';
      wrap.style.display = isMulti ? 'block' : 'none';
      const symbols = currentConfigSymbols();
      const watchlist = data.watchlist_assets || [];
      const labelFor = symbol => (watchlist.find(asset => asset.symbol === symbol)?.label || symbol);
      const previous = select.value;
      select.innerHTML = symbols.map(symbol => `<option value="${symbol}">${labelFor(symbol)}</option>`).join('');
      select.value = symbols.includes(previous) ? previous : (symbols[0] || '');
    }
    function persistCurrentValueGateDraft() {
      const selector = document.getElementById('cfgProfitAsset');
      const symbol = selector.value || currentConfigSymbols()[0];
      if (!symbol) return;
      localMinProfitFractions[symbol] = Number(String(document.getElementById('cfgMinNetProfitFraction').value || '0').replace(',', '.'));
      localMaxSlDistanceFractions[symbol] = Number(String(document.getElementById('cfgMaxSlDistanceFraction').value || '0').replace(',', '.'));
    }
    function persistCurrentMinProfitDraft() {
      persistCurrentValueGateDraft();
    }
    function loadMinProfitForSelectedAsset(data = latestConfig) {
      const isMulti = document.getElementById('cfgAssetMode').value === 'multi';
      const symbol = document.getElementById('cfgProfitAsset').value || currentConfigSymbols()[0];
      const profitFallback = percentInputValue(data.min_net_profit_fraction ?? 0.001);
      const maxSlFallback = percentInputValue(data.max_sl_distance_fraction ?? 0);
      document.getElementById('cfgMinNetProfitFraction').value = isMulti
        ? (localMinProfitFractions[symbol] ?? profitFallback)
        : profitFallback;
      document.getElementById('cfgMaxSlDistanceFraction').value = isMulti
        ? (localMaxSlDistanceFractions[symbol] ?? maxSlFallback)
        : maxSlFallback;
      updateMinNetProfitPreview();
    }
    function selectedConfigProfitSymbol() {
      return document.getElementById('cfgProfitAsset')?.value || currentConfigSymbols()[0] || (latestConfig.symbols || [])[0] || 'BTCUSDT';
    }
    function valueGateNumber(value, decimals = 4) {
      const number = Number(value);
      if (!Number.isFinite(number)) return '-';
      return number.toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: decimals });
    }
    function valueGateTradeSize(symbol, price) {
      const sizes = latestConfig.trade_sizes_by_symbol || {};
      const item = sizes[symbol] || {};
      const mode = item.mode || latestConfig.trade_size_mode || 'usd';
      const usd = Number(item.usd ?? latestConfig.trade_size_usd ?? 0);
      const asset = Number(item.asset ?? latestConfig.trade_size_asset ?? 0);
      if (mode === 'asset') {
        const notional = Number.isFinite(price) && price > 0 && asset > 0 ? asset * price : null;
        return {
          label: `${valueGateNumber(asset, 8)} Asset${notional !== null ? ` ≈ ${valueGateNumber(notional, 2)} USDT` : ''}`,
          notional,
        };
      }
      return {
        label: `${valueGateNumber(usd, 2)} USDT`,
        notional: Number.isFinite(usd) && usd > 0 ? usd : null,
      };
    }
    function renderMinNetProfitPreview(symbol, price = null, loading = false, error = '') {
      const box = document.getElementById('cfgMinNetProfitPreview');
      const input = document.getElementById('cfgMinNetProfitFraction');
      if (!box || !input) return;
      box.style.display = 'block';
      const percent = Math.max(0, Number(String(input.value || '0').replace(',', '.')) || 0);
      const maxSlPercent = Math.max(0, Number(String(document.getElementById('cfgMaxSlDistanceFraction')?.value || '0').replace(',', '.')) || 0);
      const fraction = percent / 100;
      const maxSlFraction = maxSlPercent / 100;
      const hasPrice = Number.isFinite(price) && price > 0;
      const priceMove = hasPrice ? price * fraction : null;
      const maxSlMove = hasPrice ? price * maxSlFraction : null;
      const tradeSize = valueGateTradeSize(symbol, price);
      const minProfit = tradeSize.notional !== null ? tradeSize.notional * fraction : null;
      const priceText = hasPrice ? valueGateNumber(price, 8) : (loading ? 'lade...' : '-');
      const moveText = priceMove !== null ? valueGateNumber(priceMove, 8) : '-';
      const maxSlText = maxSlMove !== null ? valueGateNumber(maxSlMove, 8) : '-';
      const profitText = minProfit !== null ? valueGateNumber(minProfit, 4) : '-';
      const status = error ? `<br><span class="dangerText">${escapeHtml(error)}</span>` : (loading ? '<br>aktueller Preis wird geladen...' : '');
      box.innerHTML = `<strong>${escapeHtml(symbol || '-')}</strong> · aktueller Preis <strong>${priceText}</strong> · <strong>${valueGateNumber(percent, 2)} %</strong> = <strong>${moveText} USDT</strong> Mindestbewegung<br>` +
        `Position <strong>${escapeHtml(tradeSize.label)}</strong> · <strong>${valueGateNumber(percent, 2)} %</strong> = <strong>${profitText} USDT</strong> Mindest-Netto-Profit<br>` +
        `Max SL Abstand · aktueller Preis <strong>${priceText}</strong> · <strong>${valueGateNumber(maxSlPercent, 2)} %</strong> = <strong>${maxSlText} USDT</strong> maximaler SL-Abstand${status}`;
    }
    async function updateMinNetProfitPreview(forcePriceReload = false) {
      const symbol = selectedConfigProfitSymbol();
      const cached = valueGatePriceCache[symbol];
      const cachedFresh = cached && Date.now() - cached.at < 30000;
      renderMinNetProfitPreview(symbol, cached?.price ?? null, forcePriceReload && !cachedFresh);
      if (!symbol || (cachedFresh && !forcePriceReload)) return;
      const token = ++valueGatePreviewToken;
      const resolution = Number(document.getElementById('cfgSignalTf')?.value || latestConfig.signal_timeframe_seconds || 300);
      try {
        const response = await fetch(`/api/chart-data?symbol=${encodeURIComponent(symbol)}&resolution=${encodeURIComponent(resolution)}&limit=50`, { cache: 'no-store' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Preis nicht geladen');
        const responseSymbol = String(data.symbol || symbol).replace('.P', '').split(':', 1)[0].trim().toUpperCase();
        if (responseSymbol !== symbol) throw new Error(`Preisquelle ${responseSymbol || '-'}, erwartet ${symbol}`);
        const candles = data.candles || [];
        const last = candles[candles.length - 1] || null;
        const price = Number(last?.close);
        if (!Number.isFinite(price) || price <= 0) throw new Error('kein gueltiger letzter Close');
        valueGatePriceCache[symbol] = { price, at: Date.now() };
        if (token === valueGatePreviewToken && selectedConfigProfitSymbol() === symbol) {
          renderMinNetProfitPreview(symbol, price);
        }
      } catch (error) {
        if (token === valueGatePreviewToken && selectedConfigProfitSymbol() === symbol) {
          renderMinNetProfitPreview(symbol, cached?.price ?? null, false, error.message || 'Preis nicht geladen');
        }
      }
    }
    function updateMultiAssetVisibility() {
      const isMulti = document.getElementById('cfgAssetMode').value === 'multi';
      document.getElementById('cfgMultiAssetSection').style.display = isMulti ? 'grid' : 'none';
      document.getElementById('cfgMultiAssetSection').style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';
      document.getElementById('cfgMultiAssetSection').style.gap = '14px';
      document.getElementById('cfgProfitAssetWrap').style.display = isMulti ? 'block' : 'none';
    }
    async function saveConfigSettings() {
      persistCurrentMinProfitDraft();
      const checkedSymbols = Array.from(document.querySelectorAll('[data-cfg-symbol]:checked')).map(input => input.dataset.cfgSymbol);
      const singleAsset = document.getElementById('cfgSingleAsset').value;
      let symbols = document.getElementById('cfgAssetMode').value === 'single'
        ? [singleAsset]
        : Array.from(new Set([...checkedSymbols, singleAsset]));
      const profitBySymbol = {};
      const maxSlBySymbol = {};
      for (const symbol of symbols) {
        profitBySymbol[symbol] = percentOutputValue(localMinProfitFractions[symbol] ?? document.getElementById('cfgMinNetProfitFraction').value ?? 0);
        maxSlBySymbol[symbol] = percentOutputValue(localMaxSlDistanceFractions[symbol] ?? document.getElementById('cfgMaxSlDistanceFraction').value ?? 0);
      }
      const parsed = {
        symbols,
        ui_theme: document.getElementById('cfgUiTheme').value,
        observer_asset_mode: document.getElementById('cfgAssetMode').value,
        max_open_trades_total: Number(document.getElementById('cfgMaxOpenTotal').value),
        max_open_trades_per_asset: Number(document.getElementById('cfgMaxOpenAsset').value),
        block_same_direction_correlated_trades: document.getElementById('cfgCorrelationBlock').checked,
        signal_timeframe_seconds: Number(document.getElementById('cfgSignalTf').value),
        confirmation_timeframe_seconds: Number(document.getElementById('cfgConfirmTf').value),
        poll_seconds: Number(document.getElementById('cfgPhemexPoll').value),
        phemex_poll_seconds: Number(document.getElementById('cfgPhemexPoll').value),
        system_loop_seconds: Number(document.getElementById('cfgSystemLoop').value),
        kline_limit: Number(document.getElementById('cfgKlineLimit').value),
        reward_risk: Number(document.getElementById('cfgRewardRisk').value) / Number(document.getElementById('cfgRiskUnit').value || 1),
        risk_unit: Number(document.getElementById('cfgRiskUnit').value || 1),
        stop_loss_mode: document.getElementById('cfgEcoStopMode').value,
        stop_loss_buffer_percent: Number(document.getElementById('cfgEcoStopBuffer').value),
        stop_loss_atr_period: Number(document.getElementById('cfgAtrPeriod').value),
        stop_loss_atr_multiplier: Number(document.getElementById('cfgAtrMultiplier').value),
        take_profit_mode: 'reward_risk',
        allow_reward_risk_fallback_tp: true,
        min_rr: 1,
        min_tp_distance_fraction: 0,
        max_sl_distance_fraction: document.getElementById('cfgAssetMode').value === 'single'
          ? percentOutputValue(document.getElementById('cfgMaxSlDistanceFraction').value)
          : percentOutputValue(localMaxSlDistanceFractions[symbols[0]] ?? document.getElementById('cfgMaxSlDistanceFraction').value),
        max_sl_distance_fraction_by_symbol: document.getElementById('cfgAssetMode').value === 'multi' ? maxSlBySymbol : {},
        estimated_taker_fee_rate: 0.0006,
        min_net_profit_fraction: document.getElementById('cfgAssetMode').value === 'single'
          ? percentOutputValue(document.getElementById('cfgMinNetProfitFraction').value)
          : percentOutputValue(localMinProfitFractions[symbols[0]] ?? document.getElementById('cfgMinNetProfitFraction').value),
        min_net_profit_fraction_by_symbol: document.getElementById('cfgAssetMode').value === 'multi' ? profitBySymbol : {}
      };
      const response = await fetch('/api/config-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const result = await response.json();
      document.getElementById('configStatus').textContent = response.ok ? 'Gespeichert.' : (result.error || 'Fehler');
      if (response.ok) {
        await refresh();
        closeModal('configModal');
      }
    }
    async function saveStrategyConfigSettings() {
      const parsed = {
        entry_mode: document.getElementById('cfgEntryMode').value,
        stop_loss_mode: document.getElementById('cfgStopMode').value,
        stop_loss_percent: Number(document.getElementById('cfgStopPercent').value),
        stop_loss_buffer_percent: Number(document.getElementById('cfgStopBuffer').value),
        stop_loss_atr_period: Number(document.getElementById('cfgStrategyAtrPeriod')?.value || latestConfig.stop_loss_atr_period || 14),
        stop_loss_atr_multiplier: Number(document.getElementById('cfgStrategyAtrMultiplier')?.value || latestConfig.stop_loss_atr_multiplier || 1.5),
        min_sweep_percent_of_prev_range: Number(document.getElementById('cfgMinSweep').value),
        structure_lookback_candles: Number(document.getElementById('cfgStructureLookback').value),
        structure_pivot_strength: Number(document.getElementById('cfgPivotStrength').value),
        sweep_rejection_mode: document.getElementById('cfgRejectionMode').value,
        entry_search_confirmation_candles: Number(document.getElementById('cfgEntrySearchCandles').value),
        swing_reaction_lookback_candles: Number(document.getElementById('cfgEntrySearchCandles').value),
        swing_lookback_candles: Number(document.getElementById('cfgSwingLookback').value),
        swing_pivot_strength: Number(document.getElementById('cfgSwingPivot').value),
        swing_zone_padding_fraction: Number(document.getElementById('cfgSwingPadding').value),
        dip_rejection_wick_ratio: Number(document.getElementById('cfgDipWick').value),
        dip_rejection_body_ratio: Number(document.getElementById('cfgMinBody').value),
        min_displacement_body_percent_of_range: Number(document.getElementById('cfgMinBody').value),
        single_timeframe_mode: true,
        take_profit_mode: 'reward_risk',
        allow_reward_risk_fallback_tp: true,
        use_trend_filter: document.getElementById('cfgTrendFilter').checked && document.getElementById('cfgTrendMode').value !== 'none',
        trend_filter_mode: document.getElementById('cfgTrendMode').value,
        trend_ema_source: document.getElementById('cfgTrendEmaSource').value,
        daily_bias_blocks_against_direction: document.getElementById('cfgTrendFilter').checked,
        trend_ema_period: Number(document.getElementById('cfgTrendEma').value)
      };
      const response = await fetch('/api/config-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const result = await response.json();
      document.getElementById('strategyConfigStatus').textContent = response.ok ? 'Gespeichert.' : (result.error || 'Fehler');
      if (response.ok) {
        await refresh();
        closeModal('strategyConfigModal');
      }
    }
    function updateRewardRiskHint() {
      const tp = Number(document.getElementById('cfgRewardRisk').value || 0);
      const sl = Number(document.getElementById('cfgRiskUnit').value || 1);
      const ratio = sl ? tp / sl : 0;
      const shownTp = Number.isInteger(tp) ? String(tp) : tp.toFixed(2);
      const shownSl = Number.isInteger(sl) ? String(sl) : sl.toFixed(2);
      document.getElementById('cfgRewardRiskHint').textContent = `TP ${shownTp} : SL ${shownSl}  |  Bot rechnet ${ratio.toFixed(2)}R`;
    }
    function updateEntrySearchHelp() {
      const signalTf = timeframeLabel(document.getElementById('cfgSignalTf').value || 300);
      const entrySeconds = Number(document.getElementById('cfgConfirmTf').value || 60);
      const entryTf = timeframeLabel(entrySeconds);
      const candles = Number(document.getElementById('cfgEntrySearchCandles').value || 20);
      const minutes = Math.round(candles * entrySeconds / 60);
      const help = document.getElementById('entrySearchHelp');
      help.innerHTML = `Der Bot prueft die letzten ${candles} ${signalTf}-Kerzen auf Reaktion an einem Swing High / Swing Low.<br><br>Gueltig ist:<br>- Liquidity Sweep + Reclaim<br>- Dip / Abpraller<br><br>Kein Supply/Demand, kein FVG-Zwang, kein Volumenfilter.`;
    }
    function updateStopLossVisibility() {
      const ecoMode = document.getElementById('cfgEcoStopMode');
      const strategyMode = document.getElementById('cfgStopMode');
      const mode = ecoMode?.value || strategyMode?.value || 'structure';
      const stopPercent = document.getElementById('cfgStopPercent');
      const stopBuffer = document.getElementById('cfgStopBuffer');
      const ecoStopBuffer = document.getElementById('cfgEcoStopBuffer');
      const atrPeriod = document.getElementById('cfgAtrPeriod');
      const atrMultiplier = document.getElementById('cfgAtrMultiplier');
      const strategyAtrPeriod = document.getElementById('cfgStrategyAtrPeriod');
      const strategyAtrMultiplier = document.getElementById('cfgStrategyAtrMultiplier');
      if (stopPercent) stopPercent.parentElement.style.display = 'none';
      if (stopBuffer) stopBuffer.parentElement.style.display = mode === 'structure' ? 'block' : 'none';
      if (ecoStopBuffer) ecoStopBuffer.parentElement.style.display = mode === 'structure' ? 'block' : 'none';
      if (atrPeriod) atrPeriod.parentElement.style.display = mode === 'atr' ? 'block' : 'none';
      if (atrMultiplier) atrMultiplier.parentElement.style.display = mode === 'atr' ? 'block' : 'none';
      if (strategyAtrPeriod) strategyAtrPeriod.parentElement.style.display = mode === 'atr' ? 'block' : 'none';
      if (strategyAtrMultiplier) strategyAtrMultiplier.parentElement.style.display = mode === 'atr' ? 'block' : 'none';
    }
    function toggleSettingsMenu() {
      const panel = document.getElementById('settingsMenuPanel');
      const button = document.getElementById('settingsMenuButton');
      const open = !panel.classList.contains('open');
      panel.classList.toggle('open', open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    document.getElementById('saveSettings').addEventListener('click', saveSettings);
    document.getElementById('startBot').addEventListener('click', () => botControl('start'));
    document.getElementById('stopBot').addEventListener('click', () => botControl('stop'));
    document.getElementById('reloadBot').addEventListener('click', reloadDashboardData);
    document.getElementById('resetBot').addEventListener('click', () => botControl('reset'));
    document.getElementById('assetFilter').addEventListener('change', event => {
      setSelectedAssetFromDropdown(event.target.value);
      refresh();
    });
    document.getElementById('tradeStatusFilter')?.addEventListener('change', event => {
      selectedTradeStatus = event.target.value;
      refresh();
    });
    document.getElementById('tradePatternFilter')?.addEventListener('change', event => {
      selectedTradePattern = event.target.value;
      refresh();
    });
    document.getElementById('tradeResultFilter')?.addEventListener('change', event => {
      selectedTradeResult = event.target.value;
      refresh();
    });
    document.getElementById('exportTradesJson')?.addEventListener('click', () => exportTradeHistory('json'));
    document.getElementById('exportTradesCsv')?.addEventListener('click', () => exportTradeHistory('csv'));
    document.getElementById('agentExportTradesJson')?.addEventListener('click', () => exportTradeHistory('json'));
    document.getElementById('agentExportTradesCsv')?.addEventListener('click', () => exportTradeHistory('csv'));
    document.getElementById('tradeSizeAssetSelector').addEventListener('change', () => {
      persistCurrentTradeSizeDraft(activeTradeSizeSymbol);
      loadTradeSizeForSelectedAsset();
    });
    document.getElementById('sizeMode').addEventListener('change', () => {
      updateSizeVisibility();
      persistCurrentTradeSizeDraft();
    });
    document.getElementById('sizeUsd').addEventListener('input', () => persistCurrentTradeSizeDraft());
    document.getElementById('sizeAsset').addEventListener('input', () => persistCurrentTradeSizeDraft());
    document.getElementById('paperToggle').addEventListener('change', () => syncSwitchState('paperToggle', 'paperToggleState', 'Aktiv', 'Aus', 'paperToggleBox'));
    document.getElementById('cfgCorrelationBlock').addEventListener('change', () => syncSwitchState('cfgCorrelationBlock', 'cfgCorrelationState'));
    document.getElementById('cfgTrendFilter').addEventListener('change', () => syncSwitchState('cfgTrendFilter', 'cfgTrendState'));
    document.getElementById('cfgIndicatorEnabled').addEventListener('change', () => syncSwitchState('cfgIndicatorEnabled', 'cfgIndicatorEnabledState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowBosChoch').addEventListener('change', () => syncSwitchState('cfgIndicatorShowBosChoch', 'cfgIndicatorShowBosChochState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowBoxes').addEventListener('change', () => syncSwitchState('cfgIndicatorShowBoxes', 'cfgIndicatorShowBoxesState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowSwingLabels').addEventListener('change', () => syncSwitchState('cfgIndicatorShowSwingLabels', 'cfgIndicatorShowSwingLabelsState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowHma').addEventListener('change', () => syncSwitchState('cfgIndicatorShowHma', 'cfgIndicatorShowHmaState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowSma').addEventListener('change', () => syncSwitchState('cfgIndicatorShowSma', 'cfgIndicatorShowSmaState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowTripleEma').addEventListener('change', () => syncSwitchState('cfgIndicatorShowTripleEma', 'cfgIndicatorShowTripleEmaState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowMfi').addEventListener('change', () => syncSwitchState('cfgIndicatorShowMfi', 'cfgIndicatorShowMfiState', 'Aktiv', 'Aus'));
    document.getElementById('cfgIndicatorShowSupportResistance').addEventListener('change', () => syncSwitchState('cfgIndicatorShowSupportResistance', 'cfgIndicatorShowSupportResistanceState', 'Aktiv', 'Aus'));
    ['cfgBrainEnabled', 'cfgBrainRequireBox', 'cfgBrainLlmLayer', 'cfgOllamaEnabled', 'cfgOllamaBlockHint', 'cfgAgentShowOffline'].forEach(id => {
      const input = document.getElementById(id);
      if (input) input.addEventListener('change', () => { syncAllSwitchStates(); syncUtilityAgentGroupStates(); });
    });
    document.getElementById('cfgTrendMode').addEventListener('change', updateEmaConfigVisibility);
    document.getElementById('cfgTrendEmaSource').addEventListener('change', updateEmaConfigVisibility);
    document.getElementById('cfgRewardRisk').addEventListener('input', updateRewardRiskHint);
    document.getElementById('cfgRiskUnit').addEventListener('input', updateRewardRiskHint);
    document.getElementById('cfgStopMode').addEventListener('change', updateStopLossVisibility);
    document.getElementById('cfgEcoStopMode').addEventListener('change', updateStopLossVisibility);
    document.getElementById('cfgSignalTf').addEventListener('change', () => {
      updateEntrySearchHelp();
      updateMinNetProfitPreview(true);
    });
    document.getElementById('cfgConfirmTf').addEventListener('change', updateEntrySearchHelp);
    document.getElementById('cfgEntrySearchCandles').addEventListener('input', updateEntrySearchHelp);
    document.getElementById('cfgUiTheme').addEventListener('change', event => applyUiTheme(event.target.value));
    document.getElementById('cfgAssetMode').addEventListener('change', () => {
      persistCurrentMinProfitDraft();
      updateMultiAssetVisibility();
      renderConfigProfitAssetSelector(latestConfig);
      loadMinProfitForSelectedAsset(latestConfig);
      updateMinNetProfitPreview(true);
    });
    document.getElementById('cfgSingleAsset').addEventListener('change', () => {
      persistCurrentMinProfitDraft();
      renderConfigProfitAssetSelector(latestConfig);
      loadMinProfitForSelectedAsset(latestConfig);
      updateMinNetProfitPreview(true);
    });
    document.getElementById('cfgProfitAsset').addEventListener('change', () => {
      loadMinProfitForSelectedAsset(latestConfig);
      updateMinNetProfitPreview(true);
    });
    document.getElementById('cfgMinNetProfitFraction').addEventListener('input', () => {
      persistCurrentValueGateDraft();
      updateMinNetProfitPreview(false);
    });
    document.getElementById('cfgMaxSlDistanceFraction').addEventListener('input', () => {
      persistCurrentValueGateDraft();
      updateMinNetProfitPreview(false);
    });
    function bindHelpButtons(root = document) {
      root.querySelectorAll('[data-help-target]').forEach(button => {
        if (button.dataset.helpBound === 'true') return;
        button.dataset.helpBound = 'true';
        button.addEventListener('click', event => {
          event.preventDefault();
          event.stopPropagation();
          const target = document.getElementById(button.dataset.helpTarget);
          if (target) target.classList.toggle('open');
        });
      });
    }
    bindHelpButtons();
    document.getElementById('chartViewButton').addEventListener('click', () => setView(currentView === 'chart' ? 'dashboard' : 'chart'));
    document.getElementById('agentViewButton').addEventListener('click', () => setView(currentView === 'agents' ? 'dashboard' : 'agents'));
    document.getElementById('agentSetupViewButton')?.addEventListener('click', () => setView(currentView === 'agent_setup' ? 'dashboard' : 'agent_setup'));
    document.getElementById('replayViewButton')?.addEventListener('click', openReplayView);
    document.querySelectorAll('[data-replay-tab]').forEach(button => {
      button.addEventListener('click', () => switchReplayTab(button.dataset.replayTab || 'overview'));
    });
    document.getElementById('reloadAgents').addEventListener('click', refresh);
    document.getElementById('agentAsset').addEventListener('change', event => {
      selectedAgentAsset = event.target.value;
      renderAgentViewer(latestStatusData || {}, latestConfig || {});
    });
    document.getElementById('agentSortMode')?.addEventListener('change', event => {
      agentSortMode = event.target.value;
      renderAgentViewer(latestStatusData || {}, latestConfig || {});
    });
    document.getElementById('agentRoleFilter')?.addEventListener('change', event => {
      agentRoleFilter = event.target.value;
      renderAgentViewer(latestStatusData || {}, latestConfig || {});
    });
    document.getElementById('replayAsset')?.addEventListener('change', () => {
      lastReplayPreviewData = null;
      loadReplayHistory();
    });
    document.getElementById('runReplayPreview')?.addEventListener('click', runReplayPreview);
    document.getElementById('exportReplayJson')?.addEventListener('click', () => exportReplayPreview('json'));
    document.getElementById('exportReplayCsv')?.addEventListener('click', () => exportReplayPreview('csv'));
    document.getElementById('clearReplayAssetHistory')?.addEventListener('click', async () => {
      try { await clearReplayHistory('asset'); } catch (error) { alert(String(error.message || error)); }
    });
    document.getElementById('clearReplayAllHistory')?.addEventListener('click', async () => {
      try { await clearReplayHistory(null); } catch (error) { alert(String(error.message || error)); }
    });
    document.getElementById('applyReplayRuleWeights')?.addEventListener('click', async () => {
      try { await saveReplayRuleWeights(true); } catch (error) { renderReplayRuleWeightStatus(String(error.message || error), 'warn'); }
    });
    document.getElementById('disableReplayRuleWeights')?.addEventListener('click', async () => {
      try { await saveReplayRuleWeights(false); } catch (error) { renderReplayRuleWeightStatus(String(error.message || error), 'warn'); }
    });
    document.getElementById('replayFilterDecision')?.addEventListener('change', refreshReplayFilters);
    document.getElementById('replayFilterGate')?.addEventListener('change', refreshReplayFilters);
    document.getElementById('replayFilterResult')?.addEventListener('change', refreshReplayFilters);
    document.getElementById('reloadChart').addEventListener('click', () => loadChartData(true));
    document.getElementById('chartSetupButton').addEventListener('click', loadChartSetupSettings);

    document.getElementById('chartAsset').addEventListener('change', () => loadChartData(true));
    document.getElementById('chartTimeframe').addEventListener('change', () => loadChartData(true));
    document.getElementById('chartCandleLimit').addEventListener('change', () => loadChartData(true));
    document.getElementById('settingsMenuButton').addEventListener('click', toggleSettingsMenu);
    document.getElementById('apiSettingsButton').addEventListener('click', async () => {
      document.getElementById('settingsMenuPanel').classList.remove('open');
      await loadApiSettings();
    });
    document.getElementById('tradingSettingsButton').addEventListener('click', async () => {
      document.getElementById('settingsMenuPanel').classList.remove('open');
      await loadTradingSettings();
    });
    document.getElementById('configSettingsButton').addEventListener('click', async () => {
      document.getElementById('settingsMenuPanel').classList.remove('open');
      await loadConfigSettings();
    });
    document.getElementById('saveApiSettings').addEventListener('click', saveApiSettings);
    document.getElementById('saveConfigSettings').addEventListener('click', saveConfigSettings);
    document.getElementById('saveStrategyConfigSettings').addEventListener('click', saveStrategyConfigSettings);
    document.getElementById('saveAgentSettings').addEventListener('click', saveAgentSettings);
    document.getElementById('saveChartSetupSettings').addEventListener('click', saveChartSetupSettings);

    document.querySelectorAll('[data-close-modal]').forEach(button => {
      button.addEventListener('click', () => closeModal(button.dataset.closeModal));
    });
    document.querySelectorAll('[data-open-target]').forEach(button => {
      button.addEventListener('click', async () => {
        document.getElementById('settingsMenuPanel').classList.remove('open');
        document.getElementById('settingsMenuButton').setAttribute('aria-expanded', 'false');
        await openSetupFile(button.dataset.openTarget);
      });
    });
    document.addEventListener('click', event => {
      const menu = document.querySelector('.menu');
      if (!menu.contains(event.target)) {
        document.getElementById('settingsMenuPanel').classList.remove('open');
        document.getElementById('settingsMenuButton').setAttribute('aria-expanded', 'false');
      }
    });
    refresh();
    loadReplayHistory();
    setInterval(refresh, 5000);
