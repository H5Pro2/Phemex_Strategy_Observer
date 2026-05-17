// ==================================================
// dashboard_agent_setup_cleanup_patch.js
// ==================================================
// AGENT SETUP STABILITY PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-agent-setup-stable-v4-chart-capable-direct';

  function installStyles() {
    const oldStyle = document.getElementById('agent-setup-cleanup-style');
    if (oldStyle && oldStyle.parentNode) oldStyle.parentNode.removeChild(oldStyle);
    const style = document.createElement('style');
    style.id = 'agent-setup-cleanup-style';
    style.textContent = `
      #agentSetupView .configModalBody {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)) !important;
        gap:16px !important;
        align-items:start !important;
      }
      #agentSetupView .settingsGroup,
      #agentSetupView .agentIndicatorGroup,
      #agentSetupView .agentDirectGroup,
      #agentSetupView .agentUtilityGroup {
        min-height:0 !important;
        height:auto !important;
        overflow:visible !important;
      }
      #agentSetupView .settingsGroupGrid {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)) !important;
        gap:12px 14px !important;
      }
      #agentSetupView .settingsGroup h3 {
        font-size:13px !important;
        font-weight:900 !important;
        letter-spacing:.055em !important;
        text-transform:uppercase !important;
      }
      #agentSetupView .agentDirectGroup[data-agent-section="rsi"],
      #agentSetupView .agentDirectGroup[data-agent-section="vwap"],
      #agentSetupView .agentDirectGroup[data-agent-section="volume"] {
        border-left:3px solid #38bdf8 !important;
      }
      #agentSetupView .agentDirectGroup[data-agent-section="breakout_fakeout"] {
        border-left:3px solid #f472b6 !important;
      }
      #agentSetupView .agentDirectGroup[data-agent-section="volatility_regime"],
      #agentSetupView .agentDirectGroup[data-agent-section="risk"] {
        border-left:3px solid #f97316 !important;
      }
      #agentSetupView .agentDirectGroup[data-agent-section="rsi"] .label.fullWidth::after,
      #agentSetupView .agentDirectGroup[data-agent-section="vwap"] .label.fullWidth::after,
      #agentSetupView .agentDirectGroup[data-agent-section="volume"] .label.fullWidth::after {
        content:' · wird im Chart View angezeigt';
        color:#67e8f9;
      }
      #agentSetupView .agentDirectGroup[data-agent-section="breakout_fakeout"] .label.fullWidth::after {
        content:' · Struktur-/Signalbewertung';
        color:#f9a8d4;
      }
      #agentSetupView .agentDirectGroup[data-agent-section="volatility_regime"] .label.fullWidth::after,
      #agentSetupView .agentDirectGroup[data-agent-section="risk"] .label.fullWidth::after {
        content:' · Bewertungslogik ohne Chart-Pane';
        color:#fdba74;
      }
    `;
    document.head.appendChild(style);
  }

  function renameDirectHeading() {
    const view = document.getElementById('agentSetupView');
    if (!view) return;
    view.querySelectorAll('.settingsGroup').forEach(block => {
      const title = block.querySelector(':scope > h3');
      const label = block.querySelector(':scope > .label');
      if (!title) return;
      const text = String(title.textContent || '').trim();
      if (text !== 'Direkte Agenten ohne Chart-Indikator' && text !== 'Agenten ohne eigene Hauptchart-Linie') return;
      title.textContent = 'Direkte Agenten / Chart View';
      if (label) {
        label.textContent = 'RSI, VWAP und Volume werden im Chart View angezeigt. Breakout/Fakeout, Volatility und Risk bleiben reine Bewertungsagenten.';
      }
    });
  }

  function install() {
    installStyles();
    renameDirectHeading();
    window.setTimeout(renameDirectHeading, 250);
    window.setTimeout(renameDirectHeading, 1000);
    document.body.dataset.agentSetupCleanupPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
