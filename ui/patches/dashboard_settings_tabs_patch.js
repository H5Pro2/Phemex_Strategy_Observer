// ==================================================
// dashboard_settings_tabs_patch.js
// ==================================================
// SAFE SETTINGS TAB FILTER PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-settings-tabs-v1-safe';

  const AGENT_TABS = [
    { key: 'all', label: 'Alle' },
    { key: 'structure', label: 'Struktur' },
    { key: 'trend', label: 'Trend' },
    { key: 'oscillator', label: 'Oszillatoren' },
    { key: 'context', label: 'Kontext / Risiko' }
  ];

  const CONFIG_TABS = [
    { key: 'all', label: 'Alle' },
    { key: 'general', label: 'Allgemein' },
    { key: 'system', label: 'System' },
    { key: 'economy', label: 'Ökonomie' }
  ];

  const AGENT_GROUPS = {
    bos_choch: 'structure',
    box: 'structure',
    swing_labels: 'structure',
    support_resistance: 'structure',
    breakout_fakeout: 'structure',
    hma: 'trend',
    sma: 'trend',
    triple_ema: 'trend',
    macd: 'oscillator',
    mfi: 'oscillator',
    rsi: 'oscillator',
    vwap: 'trend',
    volume: 'context',
    volatility_regime: 'context',
    risk: 'context'
  };

  function injectStyles() {
    if (document.getElementById('settings-tabs-style')) return;
    const style = document.createElement('style');
    style.id = 'settings-tabs-style';
    style.textContent = `
      .settingsTabsBar {
        display:flex;
        flex-wrap:wrap;
        gap:6px;
        margin:0 0 14px;
        padding:10px 0 12px;
        border-bottom:1px solid var(--line);
      }
      .settingsTabButton {
        min-height:34px;
        padding:7px 12px;
        border-radius:4px;
        border:1px solid var(--line);
        background:var(--panel-soft);
        color:var(--muted);
        font-size:12px;
        font-weight:800;
        letter-spacing:.045em;
        text-transform:uppercase;
      }
      .settingsTabButton:hover {
        border-color:var(--accent);
        color:var(--ink);
      }
      .settingsTabButton.active {
        background:rgba(45,212,191,.10);
        border-color:var(--accent);
        color:var(--accent);
      }
      #configModal[data-settings-tab="general"] .configModalBody > .settingsGroup:not([data-config-tab="general"]),
      #configModal[data-settings-tab="system"] .configModalBody > .settingsGroup:not([data-config-tab="system"]),
      #configModal[data-settings-tab="economy"] .configModalBody > .settingsGroup:not([data-config-tab="economy"]) {
        display:none !important;
      }
      #agentSetupView[data-agent-tab="structure"] .settingsGroup[data-agent-category]:not([data-agent-category="structure"]),
      #agentSetupView[data-agent-tab="trend"] .settingsGroup[data-agent-category]:not([data-agent-category="trend"]),
      #agentSetupView[data-agent-tab="oscillator"] .settingsGroup[data-agent-category]:not([data-agent-category="oscillator"]),
      #agentSetupView[data-agent-tab="context"] .settingsGroup[data-agent-category]:not([data-agent-category="context"]) {
        display:none !important;
      }
      #agentSetupView[data-agent-tab]:not([data-agent-tab="all"]) .settingsGroup:not([data-agent-category]):not(:first-child) {
        display:none !important;
      }
      #agentSetupView .settingsTabsBar {
        margin:0 0 16px;
        padding:0 0 12px;
      }
      #agentSetupView[data-agent-tab="oscillator"] .settingsGroup[data-agent-category="oscillator"] {
        border-left-color:#38bdf8 !important;
      }
      #agentSetupView[data-agent-tab="context"] .settingsGroup[data-agent-category="context"] {
        border-left-color:#f97316 !important;
      }
      @media (max-width:760px) {
        .settingsTabsBar { gap:5px; }
        .settingsTabButton { flex:1 1 auto; min-width:110px; }
      }
    `;
    document.head.appendChild(style);
  }

  function makeButton(tab, activeKey, onClick) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'settingsTabButton';
    button.textContent = tab.label;
    button.dataset.tabKey = tab.key;
    button.classList.toggle('active', tab.key === activeKey);
    button.addEventListener('click', function () { onClick(tab.key); });
    return button;
  }

  function installConfigTabs() {
    const modal = document.getElementById('configModal');
    const body = modal?.querySelector('.configModalBody');
    if (!modal || !body || body.dataset.settingsTabsReady === '1') return;
    const groups = Array.from(body.querySelectorAll(':scope > .settingsGroup'));
    if (groups[0]) groups[0].dataset.configTab = 'general';
    if (groups[1]) groups[1].dataset.configTab = 'system';
    if (groups[2]) groups[2].dataset.configTab = 'economy';
    let active = 'all';
    modal.dataset.settingsTab = active;
    const bar = document.createElement('div');
    bar.className = 'settingsTabsBar';
    function setActive(key) {
      active = key;
      modal.dataset.settingsTab = key;
      bar.querySelectorAll('.settingsTabButton').forEach(button => {
        button.classList.toggle('active', button.dataset.tabKey === key);
      });
    }
    CONFIG_TABS.forEach(tab => bar.appendChild(makeButton(tab, active, setActive)));
    body.insertBefore(bar, body.firstChild);
    body.dataset.settingsTabsReady = '1';
  }

  function installAgentTabs() {
    const view = document.getElementById('agentSetupView');
    const body = view?.querySelector('.configModalBody');
    if (!view || !body || body.dataset.agentTabsReady === '1') return;
    Array.from(body.querySelectorAll('.settingsGroup[data-agent-section]')).forEach(group => {
      const section = group.dataset.agentSection || '';
      const category = AGENT_GROUPS[section] || 'context';
      group.dataset.agentCategory = category;
    });
    let active = 'all';
    view.dataset.agentTab = active;
    const bar = document.createElement('div');
    bar.className = 'settingsTabsBar';
    function setActive(key) {
      active = key;
      view.dataset.agentTab = key;
      bar.querySelectorAll('.settingsTabButton').forEach(button => {
        button.classList.toggle('active', button.dataset.tabKey === key);
      });
    }
    AGENT_TABS.forEach(tab => bar.appendChild(makeButton(tab, active, setActive)));
    body.insertBefore(bar, body.firstChild);
    body.dataset.agentTabsReady = '1';
  }

  function install() {
    injectStyles();
    installConfigTabs();
    installAgentTabs();
    window.setTimeout(installConfigTabs, 250);
    window.setTimeout(installAgentTabs, 250);
    document.body.dataset.settingsTabsPatch = PATCH_VERSION;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();
