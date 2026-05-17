// ==================================================
// dashboard_settings_layout_patch.js
// ==================================================
// SETTINGS MODAL SAFE WIDTH PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-settings-layout-v2-safe';

  function injectStyles() {
    const oldStyle = document.getElementById('settings-layout-wide-style');
    if (oldStyle && oldStyle.parentNode) oldStyle.parentNode.removeChild(oldStyle);
    const style = document.createElement('style');
    style.id = 'settings-layout-wide-style';
    style.textContent = `
      .modalBackdrop.open {
        padding:18px !important;
        align-items:center !important;
      }
      .modalBackdrop.open .modal {
        width:min(1180px, calc(100vw - 36px)) !important;
        max-height:calc(100vh - 36px) !important;
        border-radius:6px !important;
        box-shadow:none !important;
      }
      .modalBackdrop.open .chartSetupModalBox {
        width:min(1320px, calc(100vw - 36px)) !important;
      }
      .modalBackdrop.open .modalHeader {
        min-height:58px !important;
        padding:14px 18px !important;
      }
      .modalBackdrop.open .modalHeader h2 {
        font-size:15px !important;
        font-weight:900 !important;
        letter-spacing:.065em !important;
        text-transform:uppercase !important;
      }
      .modalBackdrop.open .modalBody {
        max-height:calc(100vh - 160px) !important;
        overflow:auto !important;
        padding:16px 18px !important;
      }
      .modalBackdrop.open .modalActions {
        min-height:58px !important;
        padding:12px 18px !important;
      }
      .modalBackdrop.open .settingsGroup {
        border-radius:6px !important;
        padding:14px !important;
        box-shadow:none !important;
      }
      .modalBackdrop.open .settingsGroupGrid {
        gap:14px !important;
      }
      .modalBackdrop.open .settingsGroup input,
      .modalBackdrop.open .settingsGroup select {
        min-height:40px !important;
        border-radius:5px !important;
      }
      .modalBackdrop.open .settingsGroup textarea {
        min-height:260px !important;
      }
      .modalBackdrop.open input[type="color"] {
        height:42px !important;
      }
      @media (min-width: 1500px) {
        .modalBackdrop.open .modal,
        .modalBackdrop.open .chartSetupModalBox {
          width:min(1440px, calc(100vw - 48px)) !important;
        }
      }
      @media (max-width: 760px) {
        .modalBackdrop.open { padding:8px !important; }
        .modalBackdrop.open .modal {
          width:calc(100vw - 16px) !important;
          max-height:calc(100vh - 16px) !important;
        }
        .modalBackdrop.open .modalBody {
          max-height:calc(100vh - 140px) !important;
          padding:12px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function install() {
    injectStyles();
    document.body.dataset.settingsLayoutPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
