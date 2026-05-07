
    const fmt = (value, fallback='-') => value === null || value === undefined ? fallback : value;
    const pct = value => value === null || value === undefined ? '-' : (value * 100).toFixed(2) + '%';
    const money = (value, currency='USDT') => value === null || value === undefined ? '-' : Number(value).toFixed(2) + ' ' + currency;
    const ALL_ASSETS_VALUE = '__ALL__';
    let selectedAsset = null;
    let selectedAgentAsset = null;
    let latestStatusData = null;
    let currentView = 'dashboard';
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
    let lastActionMessage = null;
    let lastIndicatorData = null;
    let lastChartRows = [];
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
    function cleanLlmText(value, fallback='-') {
      let text = String(value ?? '').replace(/[\r\n]+/g, ' ').trim();
      text = text.replace(/\s+/g, ' ').replace(/^[`"',;\s]+|[`"',;\s]+$/g, '').trim();
      if (!text || /^[-–—.,;:'"`\s]+$/.test(text) || ['null', 'none', 'None'].includes(text)) return fallback;
      return /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]/.test(text) ? fallback : text;
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
        start.classList.toggle('active', running);
        start.disabled = running;
        start.textContent = running ? 'Aktiv' : 'Start';
      }
      if (stop) {
        stop.classList.toggle('active', !running);
        stop.disabled = !running;
        stop.textContent = running ? 'Stop' : 'Gestoppt';
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
      syncSwitchState('cfgIndicatorShowSupportResistance', 'cfgIndicatorShowSupportResistanceState', 'Aktiv', 'Aus');
      syncSwitchState('cfgBrainEnabled', 'cfgBrainEnabledState', 'Aktiv', 'Aus');
      syncSwitchState('cfgBrainRequireBox', 'cfgBrainRequireBoxState', 'Aktiv', 'Aus');
      syncSwitchState('cfgBrainLlmLayer', 'cfgBrainLlmLayerState', 'Aktiv', 'Aus');
      syncSwitchState('cfgOllamaEnabled', 'cfgOllamaEnabledState', 'Aktiv', 'Aus');
      syncSwitchState('cfgOllamaBlockHint', 'cfgOllamaBlockHintState', 'Aktiv', 'Aus');
      syncSwitchState('cfgAgentShowOffline', 'cfgAgentShowOfflineState', 'Aktiv', 'Aus');
      document.querySelectorAll('[data-agent-enabled]').forEach(input => syncSwitchState(input.id, `${input.id}State`, 'Aktiv', 'Aus'));
      document.querySelectorAll('[data-agent-blocking]').forEach(input => syncSwitchState(input.id, `${input.id}State`, 'Block', 'Info'));
    }
    async function refresh() {
      const response = await fetch('/api/status', { cache: 'no-store' });
      const data = await response.json();
      latestStatusData = data;
      const perf = data.paper?.performance || {};
      const cfg = data.config || {};
      latestConfig = cfg;
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
      renderLlmAuditSummary(data, cfg);
      renderAgentViewer(data, cfg);
      const viewLabel = assetViewLabel(selectedAsset);
      document.getElementById('tradesTitle').textContent = `Aktive & letzte Trades (${viewLabel})`;
      const assetStats = selectedAsset ? data.paper?.per_symbol?.[selectedAsset] : null;
      if (assetStats && !lastActionMessage) {
        renderControlMessage(`Ansicht ${selectedAsset}: ${assetStats.closed} geschlossen, Winrate ${pct(assetStats.win_rate)}, Sum R ${assetStats.sum_r}`);
      } else if (!selectedAsset && !lastActionMessage) {
        renderControlMessage(`Gesamtansicht: ${fmt(perf.closed, 0)} geschlossen, ${fmt(data.paper?.open_trades, 0)} offen, ${fmt(data.paper?.pending_trades, 0)} pending`);
      }

      const trades = tradesAll.filter(t => !selectedAsset || t.setup?.symbol === selectedAsset).slice().reverse().slice(0, 25);
      document.getElementById('tradeRows').innerHTML = trades.map(t => {
        const s = t.setup || {};
        const size = s.trade_size_mode === 'asset'
          ? `${fmt(s.planned_quantity_asset)} asset`
          : `${fmt(s.planned_notional_usd)} USD`;
        return '<tr>' + [
          td(fmt(t.status)), td(fmt(s.symbol)), td(fmt(s.side)), td(size), td(fmt(s.entry)), td(fmt(s.stop_loss)),
          td(fmt(s.take_profit)), td(fmt(t.result_r)), td(fmt(s.confidence))
        ].join('') + '</tr>';
      }).join('') || '<tr><td colspan="9">Noch keine Paper-Trades.</td></tr>';

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
          ? `<span class="dangerText">${fmt(event.value_result?.reason)}</span>`
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
        ['Stop-Loss', cfg.stop_loss_mode === 'fixed_percent' ? `${cfg.stop_loss_percent}% vom Entry` : `Zone/Struktur + ${cfg.stop_loss_buffer_percent}% Puffer`],
        ['Phemex Balance', account.status === 'ok' ? money(account.account_balance, currency) : fmt(account.error)],
        ['Positionsgroesse', cfg.trade_size_mode === 'asset' ? `${cfg.trade_size_asset} Asset` : `${cfg.trade_size_usd} USD/USDT`],
        ['Timeframes', `${timeframeLabel(data.config?.signal_timeframe_seconds)} / ${timeframeLabel(data.config?.confirmation_timeframe_seconds)}`],
        ['Trend', cfg.trend_filter_mode === 'ema' ? `${emaSourceLabel(cfg.trend_ema_source, cfg.signal_timeframe_seconds)} ${cfg.trend_ema_period}${cfg.use_trend_filter ? ' blockierend' : ' optional'}` : (cfg.trend_filter_mode === 'day_candle' ? `Day-Candle${cfg.use_trend_filter ? ' blockierend' : ' Status'}` : 'aus')],
        ['Loops', `Phemex ${fmt(cfg.phemex_poll_seconds ?? cfg.poll_seconds)}s / System ${fmt(cfg.system_loop_seconds)}s`],
        ['TP/SL', `${data.config?.reward_risk}:1`],
        ['Value Gate', `min Netto ${fmt(cfg.min_net_profit_fraction)} vom Positionswert`],
        ['Ollama Audit', `${cfg.brain_llm_layer_enabled && cfg.ollama_enabled ? 'aktiv' : 'aus'} | ${fmt(cfg.ollama_model || 'qwen2.5:3b')}`],
        ['Paper-Trades', `${fmt(perf.closed, 0)} geschlossen / ${fmt(data.paper?.open_trades, 0)} offen / ${fmt(data.paper?.pending_trades, 0)} pending`],
      ];
      document.getElementById('botRows').innerHTML = botRows.map(([k,v]) => `<tr><th>${k}</th><td>${fmt(v)}</td></tr>`).join('');

      const buckets = data.memory?.top_buckets || [];
      document.getElementById('bucketRows').innerHTML = buckets.map(b => '<tr>' + [
        td(`<code>${b.key}</code>`), td(b.count), td(pct(b.win_rate)), td(b.avg_r)
      ].join('') + '</tr>').join('') || '<tr><td colspan="4">Noch keine abgeschlossenen Trades im Lernspeicher.</td></tr>';
      document.getElementById('cycle').textContent = JSON.stringify(data.cycle || {}, null, 2);
    }
    function setView(view) {
      currentView = view;
      document.getElementById('dashboardView').classList.toggle('hidden', view !== 'dashboard');
      document.getElementById('chartView').classList.toggle('hidden', view !== 'chart');
      document.getElementById('agentView').classList.toggle('hidden', view !== 'agents');
      document.getElementById('chartViewButton').classList.toggle('active', view === 'chart');
      document.getElementById('agentViewButton').classList.toggle('active', view === 'agents');
      document.getElementById('chartViewButton').textContent = view === 'chart' ? 'Bot View' : 'Chart View';
      document.getElementById('agentViewButton').textContent = view === 'agents' ? 'Bot View' : 'Agent Viewer';
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
      const riskNote = cleanLlmText(layer?.risk_note && layer.risk_note !== '-' ? layer.risk_note : (layer?.message || '-'));
      const conflictNote = cleanLlmText(layer?.conflict_note && layer.conflict_note !== '-' ? layer.conflict_note : '-');
      const auditNote = cleanLlmText(layer?.advice && layer.advice !== '-' ? layer.advice : (layer?.message || '-'));
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
    function renderLlmAuditSummary(data, cfg) {
      const panel = document.getElementById('llmAuditSummary');
      if (!panel) return;
      const activeSymbols = cfg?.symbols || [];
      const symbol = selectedAgentAsset || selectedAsset || activeSymbols[0] || 'BTCUSDT';
      panel.innerHTML = renderLlmAuditContent(llmLayerForSymbol(data, cfg, symbol), cfg);
    }
    function signalClass(signal) {
      const value = String(signal || 'NEUTRAL').toLowerCase();
      return value === 'long' ? 'long' : value === 'short' ? 'short' : 'neutral';
    }
    function renderAgentCard(report, ceo=false) {
      const cls = signalClass(report?.signal);
      const conflict = report?.conflict ? ' conflict' : '';
      const score = Math.max(0, Math.min(100, Number(report?.score || 0)));
      const reads = escapeHtml(report?.reads || '-');
      const message = escapeHtml(report?.message || '-');
      const name = escapeHtml(report?.agent_name || '-');
      const fn = escapeHtml(report?.function || '-');
      return `<div class="${ceo ? 'agentCeoCard' : 'agentCube'} ${cls}${conflict}">
        <div class="agentHead"><div class="agentName">${name}</div><span class="agentSignal ${cls}">${escapeHtml(report?.signal || 'NEUTRAL')} · ${score}</span></div>
        <div class="agentFunction">${fn}</div>
        <div class="agentScore"><span style="width:${score}%"></span></div>
        <div class="agentTextBox">Liest: ${reads}
Rueckmeldung: ${message}</div>
      </div>`;
    }
    function renderAgentViewer(data, cfg) {
      const agentStatus = document.getElementById('agentStatus');
      const agentGrid = document.getElementById('agentGrid');
      const agentRiskGrid = document.getElementById('agentRiskGrid');
      const agentCeo = document.getElementById('agentCeoCard');
      const agentLlmAudit = document.getElementById('agentLlmAuditCard');
      if (!agentStatus || !agentGrid || !agentRiskGrid || !agentCeo) return;
      const symbol = activeAgentSymbol();
      const board = data?.cycle?.agents?.[symbol] || data?.cycle?.symbols?.[symbol]?.agents || null;
      if (!board) {
        agentStatus.textContent = `${symbol} | noch keine Agenten-Daten`;
        agentCeo.innerHTML = renderAgentCard({agent_name:'CEO Agent', function:'Wartet auf Agentenberichte', signal:'NEUTRAL', score:0, reads:'keine Daten', message:'Scanner starten oder Reload abwarten.'}, true);
        if (agentLlmAudit) agentLlmAudit.innerHTML = `<h3>Ollama Audit</h3>${renderLlmAuditContent(llmLayerForSymbol(data, cfg, symbol), cfg)}`;
        agentGrid.innerHTML = '<div class="agentTextBox">Keine Indikator-Agenten geladen.</div>';
        agentRiskGrid.innerHTML = '<div class="agentTextBox">Keine Risk-/Pipeline-Agenten geladen.</div>';
        return;
      }
      const reports = board.reports || [];
      const visibleReports = cfg?.agent_show_offline_agents === false ? reports.filter(report => !isOfflineAgentReport(report)) : reports;
      const hiddenOfflineCount = reports.length - visibleReports.length;
      const indicatorReports = visibleReports.filter(report => !isRiskPipelineReport(report));
      const riskReports = visibleReports.filter(report => isRiskPipelineReport(report));
      const brain = board.brain || data?.cycle?.brains?.[symbol]?.brain || null;
      const tradePlan = board.trade_plan || data?.cycle?.brains?.[symbol]?.candidate || null;
      const gate = board.economic_gate || data?.cycle?.brains?.[symbol]?.economic_gate || null;
      const llmLayer = board.llm_layer || data?.cycle?.brains?.[symbol]?.llm_layer || null;
      const flowInfo = tradePlan
        ? `<div class="agentTextBox">Trade Plan: ${escapeHtml(tradePlan.decision)} | Entry ${escapeHtml(fmt(tradePlan.entry_price))} | SL ${escapeHtml(fmt(tradePlan.sl_price))} | TP ${escapeHtml(fmt(tradePlan.tp_price))}<br>Economic Gate: ${escapeHtml(gate ? (gate.trade_allowed ? 'OK' : 'BLOCKED ' + (gate.reason || '')) : 'wartet')}</div>`
        : `<div class="agentTextBox">Trade Plan: kein freigegebener Brain-Kandidat<br>Economic Gate: wartet</div>`;
      const offlineInfo = hiddenOfflineCount > 0 ? ` | ${hiddenOfflineCount} Offline ausgeblendet` : '';
      agentStatus.textContent = `${board.symbol || symbol} | ${timeframeLabel(board.timeframe_seconds || cfg?.signal_timeframe_seconds || 0)} | ${indicatorReports.length} Indikator / ${riskReports.length} Risk${offlineInfo} | ${board.ceo?.message || '-'}`;
      agentCeo.innerHTML = `${brain ? renderAgentCard(brain, true) : ''}${renderAgentCard(board.ceo || {}, true)}${flowInfo}`;
      if (agentLlmAudit) agentLlmAudit.innerHTML = `<h3>Ollama Audit</h3>${renderLlmAuditContent(llmLayer || llmLayerForSymbol(data, cfg, symbol), cfg)}`;
      agentGrid.innerHTML = indicatorReports.map(report => renderAgentCard(report)).join('') || '<div class="agentTextBox">Keine sichtbaren Indikator-Agenten.</div>';
      agentRiskGrid.innerHTML = riskReports.map(report => renderAgentCard(report)).join('') || '<div class="agentTextBox">Keine sichtbaren Risk-/Pipeline-Agenten.</div>';
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
          detail: valueGateBlocked ? fmt(setupEvent?.value_result?.reason) : setup ? 'wirtschaftlich akzeptiert' : 'erst nach Setup',
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
      return {
        candleUp: safeHexColor(cfg.chart_candle_up_color, '#047857'),
        candleDown: safeHexColor(cfg.chart_candle_down_color, '#b42318'),
        candleNoChange: safeHexColor(cfg.chart_candle_no_change_color, '#667085'),
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
          bar: { upColor: colors.candleUp, downColor: colors.candleDown, noChangeColor: colors.candleNoChange }
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
        showSupportResistance: cfg.indicator_show_support_resistance !== false,
        swingSize: Number(cfg.indicator_swing_size ?? 5),
        hhllRange: Number(cfg.indicator_hhll_range ?? 50),
        hmaPeriod: Number(cfg.indicator_hma_period ?? 20),
        smaPeriod: Number(cfg.indicator_sma_period ?? 50),
        tripleEmaPeriod: Number(cfg.indicator_triple_ema_period ?? 20),
        tripleEmaSlowPeriod: Number(cfg.indicator_triple_ema_slow_period ?? 50),
        mfiPeriod: Number(cfg.indicator_mfi_period ?? 14),
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
        bosConfirmation: String(cfg.indicator_bos_confirmation || 'Wicks'),
        hmaColor: colors.hma,
        smaColor: colors.sma,
        tripleEmaColor: colors.tripleEma,
        tripleEmaSlowColor: colors.tripleEmaSlow,
        mfiColor: colors.mfi,
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
          bos_confirmation: cfg.bosConfirmation,
          hma_color: cfg.hmaColor,
          sma_color: cfg.smaColor,
          triple_ema_color: cfg.tripleEmaColor,
          triple_ema_slow_color: cfg.tripleEmaSlowColor,
          mfi_color: cfg.mfiColor,
          sr_support_color: cfg.srSupportColor,
          sr_resistance_color: cfg.srResistanceColor,
          show_bos_choch: String(cfg.showBosChoch),
          show_boxes: String(cfg.showBoxes),
          show_swing_labels: String(cfg.showSwingLabels),
          show_hma: String(cfg.showHma),
          show_sma: String(cfg.showSma),
          show_triple_ema: String(cfg.showTripleEma),
          show_mfi: String(cfg.showMfi),
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
    async function loadIndicatorSettings() {
      const response = await fetch('/api/config-json', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data;
      document.getElementById('cfgIndicatorEnabled').checked = data.indicator_enabled !== false;
      document.getElementById('cfgIndicatorShowBosChoch').checked = data.indicator_show_bos_choch !== false;
      document.getElementById('cfgIndicatorShowBoxes').checked = data.indicator_show_boxes !== false;
      document.getElementById('cfgIndicatorShowSwingLabels').checked = data.indicator_show_swing_labels !== false;
      document.getElementById('cfgIndicatorShowHma').checked = data.indicator_show_hma === true;
      document.getElementById('cfgIndicatorShowSma').checked = data.indicator_show_sma !== false;
      document.getElementById('cfgIndicatorShowTripleEma').checked = data.indicator_show_triple_ema === true;
      document.getElementById('cfgIndicatorShowMfi').checked = data.indicator_show_mfi !== false;
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
      document.getElementById('cfgIndicatorBosConfirmation').value = data.indicator_bos_confirmation || 'Wicks';
      document.getElementById('cfgIndicatorHmaPeriod').value = data.indicator_hma_period ?? 20;
      document.getElementById('cfgIndicatorSmaPeriod').value = data.indicator_sma_period ?? 50;
      document.getElementById('cfgIndicatorTripleEmaPeriod').value = data.indicator_triple_ema_period ?? 20;
      document.getElementById('cfgIndicatorTripleEmaSlowPeriod').value = data.indicator_triple_ema_slow_period ?? 50;
      document.getElementById('cfgIndicatorMfiPeriod').value = data.indicator_mfi_period ?? 14;
      document.getElementById('cfgIndicatorSrPivotPeriod').value = data.indicator_sr_pivot_period ?? 10;
      document.getElementById('cfgIndicatorSrSource').value = data.indicator_sr_source || 'High/Low';
      document.getElementById('cfgIndicatorSrMaxPivots').value = data.indicator_sr_max_pivots ?? 20;
      document.getElementById('cfgIndicatorSrChannelWidthPercent').value = data.indicator_sr_channel_width_percent ?? 10;
      document.getElementById('cfgIndicatorSrMaxLevels').value = data.indicator_sr_max_levels ?? 5;
      document.getElementById('cfgIndicatorSrMinStrength').value = data.indicator_sr_min_strength ?? 2;
      document.getElementById('cfgChartCandleUpColor').value = safeHexColor(data.chart_candle_up_color, '#047857');
      document.getElementById('cfgChartCandleDownColor').value = safeHexColor(data.chart_candle_down_color, '#b42318');
      document.getElementById('cfgChartCandleNoChangeColor').value = safeHexColor(data.chart_candle_no_change_color, '#667085');
      document.getElementById('cfgChartGridColor').value = safeHexColor(data.chart_grid_color, '#d9e0ea');
      document.getElementById('cfgChartBackgroundColor').value = safeHexColor(data.chart_background_color, '#ffffff');
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
      document.getElementById('cfgIndicatorSrSupportColor').value = safeHexColor(data.indicator_sr_support_color, '#22c55e');
      document.getElementById('cfgIndicatorSrResistanceColor').value = safeHexColor(data.indicator_sr_resistance_color, '#ef4444');
      syncAllSwitchStates();
      document.getElementById('indicatorSettingsStatus').textContent = '';
      openModal('indicatorModal');
    }
    async function saveIndicatorSettings() {
      const parsed = {
        indicator_enabled: document.getElementById('cfgIndicatorEnabled').checked,
        indicator_show_bos_choch: document.getElementById('cfgIndicatorShowBosChoch').checked,
        indicator_show_boxes: document.getElementById('cfgIndicatorShowBoxes').checked,
        indicator_show_swing_labels: document.getElementById('cfgIndicatorShowSwingLabels').checked,
        indicator_show_hma: document.getElementById('cfgIndicatorShowHma').checked,
        indicator_show_sma: document.getElementById('cfgIndicatorShowSma').checked,
        indicator_show_triple_ema: document.getElementById('cfgIndicatorShowTripleEma').checked,
        indicator_show_mfi: document.getElementById('cfgIndicatorShowMfi').checked,
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
        indicator_bos_confirmation: document.getElementById('cfgIndicatorBosConfirmation').value,
        indicator_hma_period: Number(document.getElementById('cfgIndicatorHmaPeriod').value),
        indicator_sma_period: Number(document.getElementById('cfgIndicatorSmaPeriod').value),
        indicator_triple_ema_period: Number(document.getElementById('cfgIndicatorTripleEmaPeriod').value),
        indicator_triple_ema_slow_period: Number(document.getElementById('cfgIndicatorTripleEmaSlowPeriod').value),
        indicator_mfi_period: Number(document.getElementById('cfgIndicatorMfiPeriod').value),
        indicator_sr_pivot_period: Number(document.getElementById('cfgIndicatorSrPivotPeriod').value),
        indicator_sr_source: document.getElementById('cfgIndicatorSrSource').value,
        indicator_sr_max_pivots: Number(document.getElementById('cfgIndicatorSrMaxPivots').value),
        indicator_sr_channel_width_percent: Number(document.getElementById('cfgIndicatorSrChannelWidthPercent').value),
        indicator_sr_max_levels: Number(document.getElementById('cfgIndicatorSrMaxLevels').value),
        indicator_sr_min_strength: Number(document.getElementById('cfgIndicatorSrMinStrength').value),
        chart_candle_up_color: document.getElementById('cfgChartCandleUpColor').value,
        chart_candle_down_color: document.getElementById('cfgChartCandleDownColor').value,
        chart_candle_no_change_color: document.getElementById('cfgChartCandleNoChangeColor').value,
        chart_grid_color: document.getElementById('cfgChartGridColor').value,
        chart_background_color: document.getElementById('cfgChartBackgroundColor').value,
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
        indicator_sr_support_color: document.getElementById('cfgIndicatorSrSupportColor').value,
        indicator_sr_resistance_color: document.getElementById('cfgIndicatorSrResistanceColor').value,
      };
      const response = await fetch('/api/config-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const result = await response.json();
      document.getElementById('indicatorSettingsStatus').textContent = response.ok ? 'Gespeichert.' : (result.error || 'Fehler');
      if (response.ok) {
        latestConfig = { ...latestConfig, ...parsed };
        updateKlineChartStyles();
        lastChartKey = '';
        closeModal('indicatorModal');
        await loadChartData(true);
      }
    }
    const AGENT_SETTING_DEFS = [
      ['bos_choch', 'BOS / CHoCH Agent', 'liest BOS / CHoCH aus den Break-Lines', 'indicator_show_bos_choch', null],
      ['box', 'LL / HH Box Agent', 'liest aktive Strukturboxen', 'indicator_show_boxes', null],
      ['support_resistance', 'Support / Resistance Agent', 'liest dynamische Support-/Resistance-Level', 'indicator_show_support_resistance', null],
      ['swing_labels', 'HH / LH / HL / LL Agent', 'liest Swing Labels', 'indicator_show_swing_labels', null],
      ['hma', 'HMA Agent', 'liest HMA Trend / Momentum', 'indicator_show_hma', null],
      ['sma', 'SMA Agent', 'liest Preisposition und SMA-Neigung', 'indicator_show_sma', { id:'cfgAgentSmaPeriod', key:'agent_sma_period', label:'SMA Period', fallback:50, help:'Anzahl Kerzen fuer den SMA-Trendfilter des SMA Agents.' }],
      ['triple_ema', 'Triple EMA Agent', 'liest Fast / Slow Triple EMA', 'indicator_show_triple_ema', null],
      ['mfi', 'MFI Agent', 'liest Money Flow Index und Kapitalfluss', 'indicator_show_mfi', { id:'cfgAgentMfiPeriod', key:'agent_mfi_period', label:'MFI Period', fallback:14, help:'Anzahl Kerzen fuer den Money Flow Index des MFI Agents.' }],
      ['volume', 'Volume Agent', 'liest Kerzenvolumen', null, { id:'cfgAgentVolumePeriod', key:'agent_volume_period', label:'Volume Period', fallback:20, help:'Anzahl Kerzen fuer den Volumen-Durchschnitt des Volume Agents.' }],
      ['risk', 'Risk Agent', 'liest Pipeline- und Gate-Kontext', null, null],
    ];
    function renderAgentSettingsGroups(data) {
      const wrap = document.getElementById('agentSettingsGroups');
      wrap.innerHTML = AGENT_SETTING_DEFS.map(([key, title, info, linked, period]) => {
        const prefix = `agent_${key}`;
        const linkedText = linked ? `Gekoppelt mit ${linked}` : 'Direkter Agent ohne Chart-Indikator-Pflicht';
        const safeKey = key.replace(/[^a-zA-Z0-9]/g, '_');
        const periodField = period
          ? `<div><label class="fieldLabel" for="${period.id}">${escapeHtml(period.label)} <button class="helpButton" type="button" data-help-target="agent_${safeKey}_period_help">?</button></label><input id="${period.id}" type="number" min="2" max="500" step="1" value="${Number(data[period.key] ?? period.fallback)}"><div id="agent_${safeKey}_period_help" class="helpText">${escapeHtml(period.help)}</div></div>`
          : '';
        return `<div class="settingsGroup">
          <h3>${escapeHtml(title)}</h3>
          <div class="settingsGroupGrid">
            <div class="fullWidth"><div class="switchLine"><input id="cfgAgent${key}Enabled" data-agent-enabled="${prefix}" class="switchInput" type="checkbox"><label class="fieldLabel" for="cfgAgent${key}Enabled">Agent aktiv <button class="helpButton" type="button" data-help-target="agent_${safeKey}_enabled_help">?</button></label><span id="cfgAgent${key}EnabledState" class="switchState">Aus</span></div><div id="agent_${safeKey}_enabled_help" class="helpText">Schaltet diesen Agenten ein oder aus. Bei Aus liefert er keine aktive Bewertung.</div></div>
            <div><label class="fieldLabel" for="cfgAgent${key}Weight">Gewichtung <button class="helpButton" type="button" data-help-target="agent_${safeKey}_weight_help">?</button></label><input id="cfgAgent${key}Weight" type="number" min="0" max="5" step="0.1"><div id="agent_${safeKey}_weight_help" class="helpText">Multiplikator fuer den Agenten-Score. 1 = normal, 0 = keine Wirkung, ueber 1 = staerkerer Einfluss.</div></div>
            <div><label class="fieldLabel" for="cfgAgent${key}MinScore">Mindestscore <button class="helpButton" type="button" data-help-target="agent_${safeKey}_min_help">?</button></label><input id="cfgAgent${key}MinScore" type="number" min="0" max="100" step="1"><div id="agent_${safeKey}_min_help" class="helpText">Unter diesem Score wird das Agentensignal auf neutral gesetzt.</div></div>
            ${periodField}
            <div class="fullWidth"><div class="switchLine"><input id="cfgAgent${key}Blocking" data-agent-blocking="${prefix}" class="switchInput" type="checkbox"><label class="fieldLabel" for="cfgAgent${key}Blocking">blockierend wenn keine Freigabe <button class="helpButton" type="button" data-help-target="agent_${safeKey}_blocking_help">?</button></label><span id="cfgAgent${key}BlockingState" class="switchState">Info</span></div><div id="agent_${safeKey}_blocking_help" class="helpText">Wenn aktiv, kann dieser Agent einen Trade blockieren, sobald seine Mindestanforderung nicht erfuellt ist.</div></div>
            <div class="label fullWidth">${escapeHtml(info)} · ${escapeHtml(linkedText)}</div>
          </div>
        </div>`;
      }).join('');
      for (const [key] of AGENT_SETTING_DEFS) {
        document.getElementById(`cfgAgent${key}Enabled`).checked = data[`agent_${key}_enabled`] !== false;
        document.getElementById(`cfgAgent${key}Weight`).value = data[`agent_${key}_weight`] ?? 1;
        document.getElementById(`cfgAgent${key}MinScore`).value = data[`agent_${key}_min_score`] ?? 0;
        document.getElementById(`cfgAgent${key}Blocking`).checked = data[`agent_${key}_blocking`] === true;
      }
      document.querySelectorAll('[data-agent-enabled],[data-agent-blocking]').forEach(input => {
        input.addEventListener('change', syncAllSwitchStates);
      });
      bindHelpButtons(wrap);
    }
    async function loadAgentSettings() {
      const response = await fetch('/api/settings', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data;
      document.getElementById('cfgBrainEnabled').checked = data.brain_enabled !== false;
      document.getElementById('cfgBrainMinScore').value = data.brain_min_score ?? 58;
      document.getElementById('cfgBrainMinScoreGap').value = data.brain_min_score_gap ?? 18;
      document.getElementById('cfgBrainMinAlignment').value = data.brain_min_agent_alignment ?? 2;
      document.getElementById('cfgBrainMemoryMinCount').value = data.brain_memory_min_count ?? 3;
      document.getElementById('cfgBrainEntryBoxOffset').value = data.brain_entry_box_offset ?? 0.35;
      document.getElementById('cfgBrainRequireBox').checked = data.brain_require_box_for_trade !== false;
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
      syncAllSwitchStates();
      document.getElementById('agentSettingsStatus').textContent = '';
      openModal('agentSettingsModal');
    }
    async function saveAgentSettings() {
      const parsed = {
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
      for (const [key, _title, _info, _linked, period] of AGENT_SETTING_DEFS) {
        parsed[`agent_${key}_enabled`] = document.getElementById(`cfgAgent${key}Enabled`).checked;
        parsed[`agent_${key}_weight`] = Number(document.getElementById(`cfgAgent${key}Weight`).value);
        parsed[`agent_${key}_min_score`] = Number(document.getElementById(`cfgAgent${key}MinScore`).value);
        parsed[`agent_${key}_blocking`] = document.getElementById(`cfgAgent${key}Blocking`).checked;
        if (period) {
          parsed[period.key] = Number(document.getElementById(period.id)?.value || latestConfig[period.key] || period.fallback);
        }
      }
      const response = await fetch('/api/config-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      const result = await response.json();
      document.getElementById('agentSettingsStatus').textContent = response.ok ? 'Gespeichert.' : (result.error || 'Fehler');
      if (response.ok) {
        latestConfig = { ...latestConfig, ...parsed };
        await refresh();
        closeModal('agentSettingsModal');
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
      localMinProfitFractions = JSON.parse(JSON.stringify(data.min_net_profit_fraction_by_symbol || {}));
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
      renderConfigProfitAssetSelector(data);
      loadMinProfitForSelectedAsset(data);
      updateRewardRiskHint();
      document.getElementById('configStatus').textContent = '';
      openModal('configModal');
    }
    async function loadStrategyConfigSettings() {
      const response = await fetch('/api/config-json', { cache: 'no-store' });
      const data = await response.json();
      latestConfig = data;
      document.getElementById('cfgEntryMode').value = data.entry_mode || 'edge';
      document.getElementById('cfgStopMode').value = data.stop_loss_mode || 'structure';
      document.getElementById('cfgStopPercent').value = data.stop_loss_percent ?? 0.25;
      document.getElementById('cfgStopBuffer').value = data.stop_loss_buffer_percent ?? 0;
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
    function persistCurrentMinProfitDraft() {
      const selector = document.getElementById('cfgProfitAsset');
      const symbol = selector.value || currentConfigSymbols()[0];
      if (!symbol) return;
      localMinProfitFractions[symbol] = Number(document.getElementById('cfgMinNetProfitFraction').value || 0);
    }
    function loadMinProfitForSelectedAsset(data = latestConfig) {
      const isMulti = document.getElementById('cfgAssetMode').value === 'multi';
      const symbol = document.getElementById('cfgProfitAsset').value || currentConfigSymbols()[0];
      const fallback = data.min_net_profit_fraction ?? 0.001;
      document.getElementById('cfgMinNetProfitFraction').value = isMulti
        ? (localMinProfitFractions[symbol] ?? fallback)
        : fallback;
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
      for (const symbol of symbols) {
        profitBySymbol[symbol] = Number(localMinProfitFractions[symbol] ?? document.getElementById('cfgMinNetProfitFraction').value ?? 0);
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
        min_rr: 1,
        min_tp_distance_fraction: 0,
        max_sl_distance_fraction: 0,
        estimated_taker_fee_rate: 0.0006,
        min_net_profit_fraction: document.getElementById('cfgAssetMode').value === 'single'
          ? Number(document.getElementById('cfgMinNetProfitFraction').value)
          : Number(localMinProfitFractions[symbols[0]] ?? document.getElementById('cfgMinNetProfitFraction').value),
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
        take_profit_mode: 'target_swing',
        allow_reward_risk_fallback_tp: false,
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
      const mode = document.getElementById('cfgStopMode').value;
      document.getElementById('cfgStopPercent').parentElement.style.display = mode === 'fixed_percent' ? 'block' : 'none';
      document.getElementById('cfgStopBuffer').parentElement.style.display = mode === 'structure' ? 'block' : 'none';
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
      if (input) input.addEventListener('change', syncAllSwitchStates);
    });
    document.getElementById('cfgTrendMode').addEventListener('change', updateEmaConfigVisibility);
    document.getElementById('cfgTrendEmaSource').addEventListener('change', updateEmaConfigVisibility);
    document.getElementById('cfgRewardRisk').addEventListener('input', updateRewardRiskHint);
    document.getElementById('cfgRiskUnit').addEventListener('input', updateRewardRiskHint);
    document.getElementById('cfgStopMode').addEventListener('change', updateStopLossVisibility);
    document.getElementById('cfgSignalTf').addEventListener('change', updateEntrySearchHelp);
    document.getElementById('cfgConfirmTf').addEventListener('change', updateEntrySearchHelp);
    document.getElementById('cfgEntrySearchCandles').addEventListener('input', updateEntrySearchHelp);
    document.getElementById('cfgUiTheme').addEventListener('change', event => applyUiTheme(event.target.value));
    document.getElementById('cfgAssetMode').addEventListener('change', () => {
      persistCurrentMinProfitDraft();
      updateMultiAssetVisibility();
      renderConfigProfitAssetSelector(latestConfig);
      loadMinProfitForSelectedAsset(latestConfig);
    });
    document.getElementById('cfgSingleAsset').addEventListener('change', () => {
      persistCurrentMinProfitDraft();
      renderConfigProfitAssetSelector(latestConfig);
      loadMinProfitForSelectedAsset(latestConfig);
    });
    document.getElementById('cfgProfitAsset').addEventListener('change', () => {
      loadMinProfitForSelectedAsset(latestConfig);
    });
    document.getElementById('cfgMinNetProfitFraction').addEventListener('input', persistCurrentMinProfitDraft);
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
    document.getElementById('reloadAgents').addEventListener('click', refresh);
    document.getElementById('agentAsset').addEventListener('change', event => {
      selectedAgentAsset = event.target.value;
      renderAgentViewer(latestStatusData || {}, latestConfig || {});
    });
    document.getElementById('reloadChart').addEventListener('click', () => loadChartData(true));
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
    document.getElementById('indicatorSettingsButton').addEventListener('click', async () => {
      document.getElementById('settingsMenuPanel').classList.remove('open');
      await loadIndicatorSettings();
    });
    document.getElementById('agentSettingsButton').addEventListener('click', async () => {
      document.getElementById('settingsMenuPanel').classList.remove('open');
      await loadAgentSettings();
    });
    document.getElementById('saveApiSettings').addEventListener('click', saveApiSettings);
    document.getElementById('saveConfigSettings').addEventListener('click', saveConfigSettings);
    document.getElementById('saveStrategyConfigSettings').addEventListener('click', saveStrategyConfigSettings);
    document.getElementById('saveIndicatorSettings').addEventListener('click', saveIndicatorSettings);
    document.getElementById('saveAgentSettings').addEventListener('click', saveAgentSettings);
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
    setInterval(refresh, 5000);
  