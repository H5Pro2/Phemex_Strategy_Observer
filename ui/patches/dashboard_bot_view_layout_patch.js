// ==================================================
// dashboard_bot_view_layout_patch.js
// ==================================================
// BOT VIEW LAYOUT PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-18-bot-view-layout-v1-clean-groups';

  function botView() {
    return document.getElementById('dashboardView') || null;
  }

  function createHeader(id, title, detail, mode) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const header = document.createElement('div');
    header.id = id;
    header.className = `botViewSectionHeader ${mode || ''}`.trim();
    header.innerHTML = `<div><strong>${title}</strong><span>${detail}</span></div>`;
    return header;
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
    tagElements();

    const kpiGrid = view.querySelector(':scope > .botViewKpiGrid');
    const controlCard = view.querySelector(':scope > .botViewControlCard');
    const auditCard = view.querySelector(':scope > .botViewAuditCard');
    const tradeGroup = view.querySelector(':scope > .botViewTradeDataGroup');
    const debugCard = view.querySelector(':scope > .botViewDebugCard');
    const cycleCard = view.querySelector(':scope > .botViewCycleCard');

    if (kpiGrid) view.insertBefore(createHeader('botViewOverviewHeader', 'Bot Übersicht', 'Kontostand, Paper-Ergebnis, Winrate und aktuelle Steuerung.', 'overview'), kpiGrid);
    if (controlCard && auditCard) view.insertBefore(createHeader('botViewControlHeader', 'Bot Steuerung / Audit', 'Start, Stop, Reload, Asset-Ansicht und Ollama Audit.', 'control'), controlCard);
    if (tradeGroup) view.insertBefore(createHeader('botViewTradeHeader', 'Trades / Bot Daten', 'Trade-History und kompakte Runtime-Werte nebeneinander.', 'trades'), tradeGroup);
    if (debugCard) view.insertBefore(createHeader('botViewDebugHeader', 'Debug / Lernspeicher', 'Scan-Debug und gelernte Formation-Buckets.', 'debug'), debugCard);
    if (cycleCard) view.insertBefore(createHeader('botViewCycleHeader', 'Letzter Zyklus', 'Rohdaten des letzten Bot-Zyklus separat unten.', 'cycle'), cycleCard);
  }

  function installStyles() {
    const oldStyle = document.getElementById('bot-view-layout-style');
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = 'bot-view-layout-style';
    style.textContent = `
      #dashboardView {
        width:100% !important;
        max-width:none !important;
        display:grid !important;
        grid-template-columns:1fr !important;
        gap:16px !important;
      }
      #dashboardView.hidden {
        display:none !important;
      }
      #dashboardView .botViewSectionHeader {
        display:flex !important;
        align-items:center !important;
        justify-content:space-between !important;
        min-height:62px !important;
        padding:13px 16px !important;
        border:1px solid var(--line) !important;
        border-radius:9px !important;
        background:rgba(15,23,42,.28) !important;
        box-shadow:0 8px 22px rgba(0,0,0,.16) !important;
      }
      #dashboardView .botViewSectionHeader.overview { border-left:6px solid #2dd4bf !important; }
      #dashboardView .botViewSectionHeader.control { border-left:6px solid #60a5fa !important; }
      #dashboardView .botViewSectionHeader.trades { border-left:6px solid #22d3ee !important; }
      #dashboardView .botViewSectionHeader.debug { border-left:6px solid #f59e0b !important; }
      #dashboardView .botViewSectionHeader.cycle { border-left:6px solid #a78bfa !important; }
      #dashboardView .botViewSectionHeader strong {
        display:block !important;
        color:var(--ink) !important;
        font-size:15px !important;
        font-weight:900 !important;
        letter-spacing:.07em !important;
        text-transform:uppercase !important;
      }
      #dashboardView .botViewSectionHeader span {
        display:block !important;
        margin-top:5px !important;
        color:var(--muted) !important;
        font-size:12px !important;
        line-height:1.35 !important;
      }
      #dashboardView .botViewKpiGrid {
        display:grid !important;
        grid-template-columns:repeat(4, minmax(0, 1fr)) !important;
        gap:14px !important;
      }
      #dashboardView .botViewKpiGrid > .card {
        min-height:116px !important;
        display:flex !important;
        flex-direction:column !important;
        justify-content:center !important;
        border-left:4px solid #2dd4bf !important;
      }
      #dashboardView .botViewControlCard,
      #dashboardView .botViewAuditCard,
      #dashboardView .botViewDebugCard,
      #dashboardView .botViewMemoryCard,
      #dashboardView .botViewCycleCard {
        width:100% !important;
        max-width:none !important;
        overflow:visible !important;
      }
      #dashboardView .botViewControlCard .controls {
        display:grid !important;
        grid-template-columns:repeat(6, minmax(130px, 1fr)) !important;
        gap:12px !important;
        align-items:end !important;
      }
      #dashboardView .botViewControlCard .controlButton {
        width:100% !important;
        min-height:44px !important;
      }
      #dashboardView .botViewControlCard #controlStatus {
        min-height:44px !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        text-align:center !important;
      }
      #dashboardView .botViewTradeDataGroup {
        display:grid !important;
        grid-template-columns:minmax(0, 2fr) minmax(320px, .85fr) !important;
        gap:16px !important;
        align-items:stretch !important;
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
        #dashboardView .botViewControlCard .controls,
        #dashboardView .botViewTradeDataGroup {
          grid-template-columns:1fr !important;
        }
      }
      @media (max-width:760px) {
        #dashboardView .botViewKpiGrid {
          grid-template-columns:1fr !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function install() {
    installStyles();
    insertHeaders();
    window.setTimeout(insertHeaders, 250);
    window.setTimeout(insertHeaders, 1000);
    document.body.dataset.botViewLayoutPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
