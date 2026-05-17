// ==================================================
// dashboard_settings_layout_patch.js
// ==================================================
// SETTINGS MODAL LAYOUT PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-settings-layout-v1-wide';

  function injectStyles() {
    const oldStyle = document.getElementById('settings-layout-wide-style');
    if (oldStyle && oldStyle.parentNode) oldStyle.parentNode.removeChild(oldStyle);
    const style = document.createElement('style');
    style.id = 'settings-layout-wide-style';
    style.textContent = `
      .modalBackdrop {
        padding:18px !important;
        align-items:center !important;
      }
      .modal {
        width:min(1180px, calc(100vw - 36px)) !important;
        max-height:calc(100vh - 36px) !important;
        border-radius:6px !important;
        box-shadow:none !important;
        display:flex !important;
        flex-direction:column !important;
        overflow:hidden !important;
      }
      .chartSetupModalBox,
      #configModal .modal,
      #agentSetupView .modal,
      #chartSetupView .modal {
        width:min(1320px, calc(100vw - 36px)) !important;
      }
      .modalHeader {
        position:sticky !important;
        top:0 !important;
        z-index:5 !important;
        min-height:58px !important;
        padding:14px 18px !important;
        background:var(--panel) !important;
        border-bottom:1px solid rgba(148,163,184,.28) !important;
      }
      .modalHeader h2 {
        font-size:15px !important;
        font-weight:900 !important;
        letter-spacing:.08em !important;
        text-transform:uppercase !important;
      }
      .modalBody {
        flex:1 1 auto !important;
        overflow:auto !important;
        padding:16px 18px !important;
        gap:14px !important;
        background:rgba(15,23,42,.04) !important;
      }
      .modalActions {
        position:sticky !important;
        bottom:0 !important;
        z-index:5 !important;
        min-height:58px !important;
        padding:12px 18px !important;
        background:var(--panel) !important;
        border-top:1px solid rgba(148,163,184,.28) !important;
      }
      .configModalBody,
      #agentSetupView .configModalBody {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)) !important;
        gap:14px !important;
        align-items:start !important;
      }
      .settingsGroup {
        border-radius:5px !important;
        padding:14px !important;
        gap:12px !important;
        background:rgba(15,23,42,.08) !important;
        box-shadow:none !important;
      }
      .settingsGroup h3 {
        font-size:12px !important;
        font-weight:900 !important;
        letter-spacing:.08em !important;
        text-transform:uppercase !important;
        padding-bottom:8px !important;
        border-bottom:1px solid rgba(148,163,184,.18) !important;
      }
      .settingsGroupGrid {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)) !important;
        gap:12px !important;
      }
      .settingsGroupGrid .fullWidth,
      .settingsGroup .fullWidth {
        grid-column:1 / -1 !important;
      }
      .settingsGroup label,
      .fieldLabel {
        font-size:11px !important;
        font-weight:800 !important;
        letter-spacing:.055em !important;
        text-transform:uppercase !important;
      }
      .settingsGroup input,
      .settingsGroup select,
      .settingsGroup textarea {
        min-height:42px !important;
        border-radius:4px !important;
        font-size:13px !important;
      }
      .settingsGroup textarea {
        min-height:260px !important;
      }
      .settingsGroup input[type="checkbox"] {
        min-height:0 !important;
      }
      .switchInput {
        width:58px !important;
        height:30px !important;
        flex-basis:58px !important;
      }
      .switchInput::after {
        width:22px !important;
        height:22px !important;
      }
      .switchInput:checked::after {
        left:31px !important;
      }
      .paperToggleLarge {
        min-height:58px !important;
        border-radius:5px !important;
      }
      .helpText {
        border-radius:4px !important;
        font-size:12px !important;
      }
      .watchlistChecks {
        grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)) !important;
        max-height:320px !important;
        overflow:auto !important;
        border-radius:4px !important;
      }
      .colorFieldRow {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(135px, 1fr)) !important;
        gap:12px !important;
      }
      .colorField {
        min-width:0 !important;
        max-width:none !important;
      }
      .colorField input[type="color"],
      input[type="color"] {
        width:100% !important;
        max-width:none !important;
        min-width:0 !important;
        height:44px !important;
      }
      #agentSetupView .agentIndicatorGroup,
      #agentSetupView .agentDirectGroup,
      #agentSetupView .agentSetupReclassifiedGroup .agentDirectGroup {
        min-height:0 !important;
      }
      #agentSetupView .agentSetupReclassifiedGroup {
        grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)) !important;
        gap:14px !important;
      }
      .agentSetupInfoBlock {
        grid-column:1 / -1 !important;
      }
      .replayCompactToolbar,
      .replayFilterToolbar,
      .tradeFilters {
        grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)) !important;
      }
      .modalActions button,
      .modalHeader button {
        min-height:38px !important;
      }
      @media (min-width: 1500px) {
        .modal,
        .chartSetupModalBox,
        #configModal .modal,
        #agentSetupView .modal,
        #chartSetupView .modal {
          width:min(1460px, calc(100vw - 48px)) !important;
        }
        .configModalBody,
        #agentSetupView .configModalBody {
          grid-template-columns:repeat(auto-fit, minmax(390px, 1fr)) !important;
        }
      }
      @media (max-width: 760px) {
        .modalBackdrop { padding:8px !important; }
        .modal {
          width:calc(100vw - 16px) !important;
          max-height:calc(100vh - 16px) !important;
        }
        .configModalBody,
        #agentSetupView .configModalBody,
        .settingsGroupGrid,
        #agentSetupView .agentSetupReclassifiedGroup {
          grid-template-columns:1fr !important;
        }
        .modalHeader,
        .modalActions {
          padding:10px 12px !important;
        }
        .modalBody {
          padding:12px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function markSettingsModals() {
    document.querySelectorAll('.modal').forEach(modal => {
      if (modal.querySelector('.settingsGroup') || modal.querySelector('.configModalBody')) {
        modal.classList.add('settingsWideModal');
      }
    });
    document.body.dataset.settingsLayoutPatch = PATCH_VERSION;
  }

  function install() {
    injectStyles();
    markSettingsModals();
    if (!window.__settingsLayoutObserver) {
      window.__settingsLayoutObserver = new MutationObserver(() => markSettingsModals());
      window.__settingsLayoutObserver.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
