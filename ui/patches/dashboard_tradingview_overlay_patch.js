// ==================================================
// dashboard_tradingview_overlay_patch.js
// ==================================================
// TRADINGVIEW STYLE CHART OVERLAY PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-06-02-tradingview-overlay-v3-top-controls-hud';
  const OVERLAY_GROUP = 'tv_strategy_overlay';
  let overlayIds = [];
  let overlaysRegistered = false;
  let latestOverlay = null;

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

  function fmt(value, digits = 4) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '-';
    if (Math.abs(number) >= 1000) return number.toLocaleString('de-DE', { maximumFractionDigits: 2 });
    return number.toFixed(digits).replace(/0+$/, '').replace(/\.$/, '');
  }

  function textStyle(color, size = 11, weight = 'bold') {
    return {
      color,
      size,
      family: 'Arial',
      weight,
      style: 'fill',
      backgroundColor: 'transparent',
      borderColor: 'transparent',
      borderSize: 0,
      paddingLeft: 0,
      paddingRight: 0,
      paddingTop: 0,
      paddingBottom: 0
    };
  }

  function clearOverlayIds() {
    const chart = chartInstance();
    if (!chart || typeof chart.removeOverlay !== 'function') {
      overlayIds = [];
      return;
    }
    overlayIds.forEach(id => {
      try { chart.removeOverlay({ id }); } catch (_) {
        try { chart.removeOverlay(id); } catch (_) {}
      }
    });
    overlayIds = [];
  }

  function remember(result) {
    if (Array.isArray(result)) overlayIds.push(...result.filter(Boolean));
    else if (result) overlayIds.push(result);
  }

  function directionFromOverlay(overlay) {
    const side = String(overlay?.setup?.side || overlay?.scan?.side || '').toLowerCase();
    if (side.includes('short')) return 'short';
    if (side.includes('long')) return 'long';
    const entry = Number(overlay?.setup?.entry ?? overlay?.scan?.entry);
    const tp = Number(overlay?.setup?.take_profit);
    if (Number.isFinite(entry) && Number.isFinite(tp)) return tp >= entry ? 'long' : 'short';
    return 'neutral';
  }

  function setupPrices(overlay) {
    const setup = overlay?.setup || {};
    const scan = overlay?.scan || {};
    return {
      entry: Number(setup.entry ?? scan.entry),
      stop: Number(setup.stop_loss ?? scan.stop_loss),
      tp: Number(setup.take_profit ?? scan.take_profit),
      side: directionFromOverlay(overlay)
    };
  }

  function point(timestamp, price) {
    return { timestamp: Number(timestamp), value: Number(price) };
  }

  function registerOverlays() {
    const api = apiInstance();
    if (overlaysRegistered || !api?.registerOverlay) return;

    api.registerOverlay({
      name: 'tvPriceLine',
      totalStep: 2,
      lock: true,
      createPointFigures: ({ overlay, coordinates }) => {
        if (coordinates.length < 2) return [];
        const data = overlay.extendData || {};
        const color = data.color || '#38bdf8';
        const y = coordinates[0].y;
        const leftX = Math.min(coordinates[0].x, coordinates[1].x);
        const rightX = Math.max(coordinates[0].x, coordinates[1].x);
        const label = `${data.label || 'Level'} ${fmt(data.price)}`;
        const labelWidth = Math.max(70, label.length * 7 + 18);
        const labelX = Math.max(leftX + labelWidth / 2 + 4, rightX - labelWidth / 2 - 4);
        return [
          { type: 'line', attrs: { coordinates: [{ x: leftX, y }, { x: rightX, y }] }, styles: { color, size: data.strong ? 2 : 1, style: data.style || 'dashed' }, ignoreEvent: true },
          { type: 'rect', attrs: { x: labelX - labelWidth / 2, y: y - 11, width: labelWidth, height: 22 }, styles: { style: 'stroke_fill', color: data.fill || 'rgba(2,6,23,.88)', borderColor: color }, ignoreEvent: true },
          { type: 'text', attrs: { x: labelX, y, text: label, align: 'center', baseline: 'middle' }, styles: textStyle('#f8fafc', 11), ignoreEvent: true }
        ];
      }
    });

    api.registerOverlay({
      name: 'tvPriceZone',
      totalStep: 2,
      lock: true,
      createPointFigures: ({ overlay, coordinates }) => {
        if (coordinates.length < 2) return [];
        const data = overlay.extendData || {};
        const color = data.color || '#38bdf8';
        const x = Math.min(coordinates[0].x, coordinates[1].x);
        const y = Math.min(coordinates[0].y, coordinates[1].y);
        const width = Math.max(2, Math.abs(coordinates[1].x - coordinates[0].x));
        const height = Math.max(2, Math.abs(coordinates[1].y - coordinates[0].y));
        return [
          { type: 'rect', attrs: { x, y, width, height }, styles: { style: 'stroke_fill', color: data.fill || 'rgba(56,189,248,.10)', borderColor: color }, ignoreEvent: true },
          { type: 'text', attrs: { x: x + 12, y: y + 14, text: String(data.label || ''), align: 'left', baseline: 'middle' }, styles: textStyle(color, 11), ignoreEvent: true }
        ];
      }
    });

    api.registerOverlay({
      name: 'tvRiskRewardBox',
      totalStep: 2,
      lock: true,
      createPointFigures: ({ overlay, coordinates }) => {
        if (coordinates.length < 2) return [];
        const data = overlay.extendData || {};
        const x = Math.min(coordinates[0].x, coordinates[1].x);
        const width = Math.max(4, Math.abs(coordinates[1].x - coordinates[0].x));
        const y = Math.min(coordinates[0].y, coordinates[1].y);
        const height = Math.max(3, Math.abs(coordinates[1].y - coordinates[0].y));
        const color = data.kind === 'reward' ? '#22c55e' : '#ef4444';
        const fill = data.kind === 'reward' ? 'rgba(34,197,94,.13)' : 'rgba(239,68,68,.13)';
        const label = data.kind === 'reward' ? `Target ${fmt(data.price)}` : `Stop ${fmt(data.price)}`;
        return [
          { type: 'rect', attrs: { x, y, width, height }, styles: { style: 'stroke_fill', color: fill, borderColor: color }, ignoreEvent: true },
          { type: 'text', attrs: { x: x + 12, y: y + 15, text: label, align: 'left', baseline: 'middle' }, styles: textStyle(color, 11), ignoreEvent: true }
        ];
      }
    });

    overlaysRegistered = true;
  }

  function visibleRange(rows) {
    const first = rows[0]?.timestamp;
    const last = rows[rows.length - 1]?.timestamp;
    if (!Number.isFinite(first) || !Number.isFinite(last)) return null;
    const step = rows.length > 1 ? Math.max(60_000, last - rows[rows.length - 2].timestamp) : 60_000;
    return { start: Math.max(first, last - step * 54), end: last + step * 16, last, step };
  }

  function drawTradingViewOverlay(rows, overlay) {
    const chart = chartInstance();
    if (!chart || !rows?.length || !overlay || typeof chart.createOverlay !== 'function') return;
    registerOverlays();
    clearOverlayIds();
    latestOverlay = overlay;

    const range = visibleRange(rows);
    if (!range) return;
    const prices = setupPrices(overlay);
    const levels = (overlay.levels || []).filter(level => Number.isFinite(Number(level.price)));

    if (overlay.fvg && Number.isFinite(Number(overlay.fvg.low)) && Number.isFinite(Number(overlay.fvg.high))) {
      remember(chart.createOverlay({
        name: 'tvPriceZone',
        groupId: OVERLAY_GROUP,
        lock: true,
        zLevel: 35,
        points: [point(range.start, overlay.fvg.high), point(range.end, overlay.fvg.low)],
        extendData: { label: overlay.fvg.label || 'Entry Zone', color: '#38bdf8', fill: 'rgba(56,189,248,.09)' }
      }));
    }

    if (Number.isFinite(prices.entry) && Number.isFinite(prices.tp) && Number.isFinite(prices.stop)) {
      const rewardTop = Math.max(prices.entry, prices.tp);
      const rewardBottom = Math.min(prices.entry, prices.tp);
      const riskTop = Math.max(prices.entry, prices.stop);
      const riskBottom = Math.min(prices.entry, prices.stop);
      remember(chart.createOverlay({
        name: 'tvRiskRewardBox',
        groupId: OVERLAY_GROUP,
        lock: true,
        zLevel: 38,
        points: [point(range.last - range.step * 18, rewardTop), point(range.end, rewardBottom)],
        extendData: { kind: 'reward', price: prices.tp }
      }));
      remember(chart.createOverlay({
        name: 'tvRiskRewardBox',
        groupId: OVERLAY_GROUP,
        lock: true,
        zLevel: 38,
        points: [point(range.last - range.step * 18, riskTop), point(range.end, riskBottom)],
        extendData: { kind: 'risk', price: prices.stop }
      }));
    }

    levels.forEach(level => {
      const label = String(level.label || '').toUpperCase();
      const color = label.includes('SL') ? '#ef4444' : label.includes('TP') ? '#22c55e' : label.includes('ENTRY') ? '#38bdf8' : (level.color || '#94a3b8');
      remember(chart.createOverlay({
        name: 'tvPriceLine',
        groupId: OVERLAY_GROUP,
        lock: true,
        zLevel: level.strong ? 48 : 42,
        points: [point(range.start, Number(level.price)), point(range.end, Number(level.price))],
        extendData: {
          label: level.label || 'Level',
          price: Number(level.price),
          color,
          strong: !!level.strong,
          style: level.strong ? 'solid' : 'dashed'
        }
      }));
    });
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char]));
  }

  function ensureHud() {
    const chart = document.getElementById('klineChart');
    const wrap = chart?.closest('.chartCanvasWrap');
    const topControls = document.getElementById('chartViewTopControls');
    if (!wrap && !topControls) return null;
    if (wrap) wrap.classList.add('tvOverlayCanvasWrap');
    let hud = document.getElementById('tvStrategyHud');
    if (!hud) {
      hud = document.createElement('div');
      hud.id = 'tvStrategyHud';
      hud.className = 'tvStrategyHud';
    }
    if (topControls && hud.parentElement !== topControls) topControls.appendChild(hud);
    else if (!topControls && wrap && hud.parentElement !== wrap) wrap.appendChild(hud);
    return hud;
  }

  function updateHud(overlay) {
    const hud = ensureHud();
    if (!hud) return;
    latestOverlay = overlay || latestOverlay;
    const data = latestOverlay || {};
    const prices = setupPrices(data);
    const rr = Number.isFinite(prices.entry) && Number.isFinite(prices.stop) && Number.isFinite(prices.tp)
      ? Math.abs(prices.tp - prices.entry) / Math.max(Math.abs(prices.entry - prices.stop), 1e-12)
      : null;
    const direction = prices.side === 'short' ? 'short' : prices.side === 'long' ? 'long' : 'neutral';
    const diagnostics = (data.diagnostics || []).slice(0, 2).map(item => `
      <span class="tvHudCheck ${escapeHtml(item.state || 'neutral')}">
        <b>${escapeHtml(item.label || '-')}</b>
        <em>${escapeHtml(item.detail || '')}</em>
      </span>
    `).join('');

    hud.innerHTML = `
      <div class="tvHudTop">
        <span class="tvHudSymbol">${escapeHtml(data.asset || document.getElementById('chartAsset')?.value || '-')}</span>
        <span class="tvHudPill ${direction}">${direction === 'long' ? 'LONG' : direction === 'short' ? 'SHORT' : 'WATCH'}</span>
        <span class="tvHudMuted">${escapeHtml(document.getElementById('chartTimeframe')?.selectedOptions?.[0]?.textContent || '')}</span>
      </div>
      <div class="tvHudPrices">
        <span><b>Entry</b>${fmt(prices.entry)}</span>
        <span><b>SL</b>${fmt(prices.stop)}</span>
        <span><b>TP</b>${fmt(prices.tp)}</span>
        <span><b>RR</b>${rr === null ? '-' : rr.toFixed(2)}</span>
      </div>
      <div class="tvHudStatus">${escapeHtml(data.status || 'Kein aktives Setup')}</div>
      <div class="tvHudChecks">${diagnostics}</div>
    `;
  }

  function installStyles() {
    const oldStyle = document.getElementById('tradingview-overlay-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'tradingview-overlay-style';
    style.textContent = `
      #chartView .tvOverlayCanvasWrap { position:relative !important; }
      #chartView .tvStrategyHud {
        position:relative !important;
        top:auto !important;
        left:auto !important;
        z-index:3 !important;
        width:100% !important;
        min-width:0 !important;
        align-self:stretch !important;
        padding:8px 9px !important;
        border:1px solid rgba(148,163,184,.26) !important;
        border-radius:6px !important;
        background:rgba(15,23,42,.22) !important;
        box-shadow:none !important;
        backdrop-filter:none !important;
        pointer-events:auto !important;
        overflow:hidden !important;
      }
      body[data-theme="light"] #chartView .tvStrategyHud { background:rgba(255,255,255,.82) !important; box-shadow:0 10px 24px rgba(15,23,42,.14) !important; }
      #chartView .tvHudTop { display:flex !important; align-items:center !important; gap:8px !important; min-width:0 !important; }
      #chartView .tvHudSymbol { color:var(--ink) !important; font:900 13px Arial,sans-serif !important; letter-spacing:0 !important; }
      #chartView .tvHudPill { padding:3px 7px !important; border-radius:4px !important; color:#f8fafc !important; font:900 11px Arial,sans-serif !important; }
      #chartView .tvHudPill.long { background:#047857 !important; }
      #chartView .tvHudPill.short { background:#b42318 !important; }
      #chartView .tvHudPill.neutral { background:#475569 !important; }
      #chartView .tvHudMuted { margin-left:auto !important; color:var(--muted) !important; font:700 11px Arial,sans-serif !important; }
      #chartView .tvHudPrices { display:grid !important; grid-template-columns:repeat(4, minmax(0, 1fr)) !important; gap:4px !important; margin-top:7px !important; }
      #chartView .tvHudPrices span { min-height:30px !important; padding:4px 5px !important; border:1px solid rgba(148,163,184,.18) !important; border-radius:4px !important; background:rgba(15,23,42,.32) !important; color:var(--ink) !important; font:800 11px Arial,sans-serif !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      body[data-theme="light"] #chartView .tvHudPrices span { background:rgba(241,245,249,.78) !important; }
      #chartView .tvHudPrices b { display:block !important; margin-bottom:3px !important; color:var(--muted) !important; font-size:9px !important; font-weight:900 !important; text-transform:uppercase !important; }
      #chartView .tvHudStatus { margin-top:6px !important; color:var(--ink) !important; font:800 11px/1.3 Arial,sans-serif !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      #chartView .tvHudChecks { display:grid !important; grid-template-columns:repeat(2, minmax(0, 1fr)) !important; gap:4px !important; margin-top:6px !important; }
      #chartView .tvHudCheck { min-height:32px !important; padding:4px 5px !important; border-left:3px solid #64748b !important; border-radius:4px !important; background:rgba(15,23,42,.26) !important; overflow:hidden !important; }
      body[data-theme="light"] #chartView .tvHudCheck { background:rgba(241,245,249,.70) !important; }
      #chartView .tvHudCheck.ok { border-left-color:#22c55e !important; }
      #chartView .tvHudCheck.fail { border-left-color:#ef4444 !important; }
      #chartView .tvHudCheck.neutral { border-left-color:#38bdf8 !important; }
      #chartView .tvHudCheck b { display:block !important; color:var(--ink) !important; font:900 10px Arial,sans-serif !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      #chartView .tvHudCheck em { display:block !important; margin-top:2px !important; color:var(--muted) !important; font:700 10px/1.25 Arial,sans-serif !important; font-style:normal !important; overflow:hidden !important; text-overflow:ellipsis !important; white-space:nowrap !important; }
      @media (max-width:760px) {
        #chartView .tvStrategyHud { width:100% !important; }
        #chartView .tvHudPrices { grid-template-columns:repeat(2, minmax(0, 1fr)) !important; }
        #chartView .tvHudChecks { grid-template-columns:1fr !important; }
      }
    `;
    document.head.appendChild(style);
  }

  function patchRenderOverlay() {
    if (window.renderKlineStrategyOverlay?.__tradingViewOverlayPatched) return;
    const original = window.renderKlineStrategyOverlay;
    if (typeof original !== 'function') return;
    window.renderKlineStrategyOverlay = function patchedRenderKlineStrategyOverlay(rows, overlay) {
      const result = original.apply(this, arguments);
      drawTradingViewOverlay(rows, overlay);
      updateHud(overlay);
      return result;
    };
    window.renderKlineStrategyOverlay.__tradingViewOverlayPatched = true;
  }

  function patchClearChart() {
    if (window.clearKlineChart?.__tradingViewOverlayPatched) return;
    const original = window.clearKlineChart;
    if (typeof original !== 'function') return;
    window.clearKlineChart = function patchedClearKlineChart() {
      clearOverlayIds();
      const hud = document.getElementById('tvStrategyHud');
      if (hud) hud.innerHTML = '';
      return original.apply(this, arguments);
    };
    window.clearKlineChart.__tradingViewOverlayPatched = true;
  }

  function refreshHudFromDom() {
    if (document.getElementById('chartView')?.classList.contains('hidden')) return;
    updateHud(latestOverlay);
  }

  function installHooks() {
    ['click', 'change'].forEach(type => {
      document.addEventListener(type, event => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (target.closest('#chartViewButton, #reloadChart, #chartAsset, #chartTimeframe, #chartCandleLimit')) {
          window.setTimeout(refreshHudFromDom, 120);
          window.setTimeout(refreshHudFromDom, 700);
        }
      }, true);
    });
  }

  function install() {
    installStyles();
    installHooks();
    patchRenderOverlay();
    patchClearChart();
    ensureHud();
    window.setTimeout(() => { patchRenderOverlay(); patchClearChart(); ensureHud(); }, 500);
    window.setTimeout(() => { patchRenderOverlay(); patchClearChart(); ensureHud(); }, 1500);
    document.body.dataset.tradingViewOverlayPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
  window.addEventListener('resize', refreshHudFromDom);
})();
