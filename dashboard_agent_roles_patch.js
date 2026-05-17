// ==================================================
// dashboard_agent_roles_patch.js
// ==================================================
// DASHBOARD AGENT ROLE CONTRACT PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-role-ui-v2';

  function normalizedText(value) {
    return String(value || '').toLowerCase();
  }

  function patchedAgentRole(report, ceo = false) {
    if (ceo) return 'decision';
    const role = normalizedText(report?.role);
    if (['structure', 'momentum', 'context', 'risk', 'decision', 'other'].includes(role)) return role;
    const name = normalizedText(report?.agent_name);
    const fn = normalizedText(report?.function);
    const text = `${name} ${fn}`;
    if (text.includes('ceo') || text.includes('brain') || text.includes('audit') || text.includes('llm')) return 'decision';
    if (text.includes('risk') || text.includes('volatility') || text.includes('vola')) return 'risk';
    if (text.includes('volume')) return 'context';
    if (text.includes('bos') || text.includes('choch') || text.includes('box') || text.includes('support') || text.includes('resistance') || text.includes('swing') || text.includes('hh') || text.includes('breakout') || text.includes('fakeout')) return 'structure';
    if (text.includes('hma') || text.includes('sma') || text.includes('triple') || text.includes('macd') || text.includes('mfi') || text.includes('rsi') || text.includes('vwap')) return 'momentum';
    return 'other';
  }

  function patchedAgentRoleLabel(role) {
    const map = {
      structure: 'Struktur',
      momentum: 'Momentum',
      context: 'Kontext',
      risk: 'Risiko',
      decision: 'Entscheidung',
      other: 'Weitere',
      signal: 'Signal'
    };
    return map[String(role || '').toLowerCase()] || 'Weitere';
  }

  function patchedIsRiskPipelineReport(report) {
    const role = patchedAgentRole(report);
    return role === 'risk' || role === 'decision';
  }

  function patchedFilterAgentReportsByRole(reports, role) {
    const selected = String(role || 'all').toLowerCase();
    if (selected === 'all') return reports || [];
    if (selected === 'signal') {
      return (reports || []).filter(report => ['structure', 'momentum', 'context'].includes(patchedAgentRole(report)));
    }
    return (reports || []).filter(report => patchedAgentRole(report) === selected);
  }

  function ensureAgentRoleFilterOptions() {
    const select = document.getElementById('agentRoleFilter');
    if (!select) return;
    const current = select.value || 'all';
    const expected = ['all', 'structure', 'momentum', 'context', 'risk', 'decision'];
    select.innerHTML = [
      ['all', 'Alle Rollen'],
      ['structure', 'Struktur'],
      ['momentum', 'Momentum'],
      ['context', 'Kontext'],
      ['risk', 'Risiko'],
      ['decision', 'Entscheidung']
    ].map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    select.value = expected.includes(current) ? current : 'all';
    select.dataset.roleContractPatched = PATCH_VERSION;
  }

  function injectRoleUiStyles() {
    const styleId = 'agent-role-contract-style';
    const oldStyle = document.getElementById(styleId);
    if (oldStyle) oldStyle.remove();
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .agentRoleGroup { margin-top:12px; border:1px solid var(--line); border-radius:8px; overflow:hidden; background:var(--panel-soft); }
      .agentRoleGroupTitle { min-height:34px; padding:8px 11px; font-size:12px; letter-spacing:.05em; text-transform:uppercase; display:flex; justify-content:space-between; align-items:center; background:rgba(15,23,42,.18); border-bottom:1px solid var(--line); }
      .agentRoleGroupTitle span { color:var(--muted); font-size:11px; text-transform:none; letter-spacing:0; }
      .agentRoleGroup .agentGrid { padding:10px; display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:10px; }
      .agentCube, .agentCeoCard { border-radius:8px; padding:11px 12px; min-height:0; }
      .agentCube .agentHead, .agentCeoCard .agentHead { gap:8px; align-items:flex-start; }
      .agentName { font-size:13px; line-height:1.25; }
      .agentFunction { font-size:11px; line-height:1.35; }
      .agentHeadBadges { gap:5px; justify-content:flex-end; }
      .agentSignal, .agentQualityPill { padding:3px 7px; font-size:11px; border-radius:999px; }
      .agentScore { height:5px; margin:8px 0; }
      .agentTextBox { font-size:11px; line-height:1.35; padding:8px; border-radius:6px; }
      .agentCompactBoard { border-radius:10px; }
      .agentCompactTop { display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:9px; }
      .agentCompactKpi { min-height:80px; padding:11px; }
      .agentCompactKpi span { font-size:11px; }
      .agentCompactKpi strong { font-size:16px; }
      .agentCompactKpi small { font-size:11px; line-height:1.35; }
      .priorityDecisionCenter { border:1px solid var(--line); border-radius:10px; padding:12px; margin-top:12px; background:linear-gradient(180deg, rgba(15,23,42,.24), rgba(15,23,42,.12)); }
      .priorityHeader { margin-bottom:10px; }
      .priorityTitle { font-size:13px; letter-spacing:.06em; text-transform:uppercase; }
      .prioritySummaryCard { display:grid; gap:6px; }
      .prioritySummaryRow { min-height:34px; padding:7px 9px; border-radius:7px; }
      .priorityAgentRow, .priorityAgentHead { grid-template-columns:minmax(130px,1.4fr) 82px 86px 48px minmax(120px,1fr); gap:7px; font-size:11px; }
      .priorityChip { padding:3px 7px; border-radius:999px; font-size:11px; }
      .ceoExplainPanel { border-radius:9px; padding:11px; margin-top:10px; }
      .ceoExplainTitle { font-size:12px; letter-spacing:.06em; text-transform:uppercase; margin-bottom:8px; }
      .ceoExplainRows { display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:7px; }
      .ceoExplainRow { min-height:32px; padding:7px 8px; border-radius:7px; }
      .ceoExplainRow span { font-size:11px; }
      .ceoExplainRow strong { font-size:12px; line-height:1.35; }
      .agentConflictPanel { border-radius:9px; padding:11px; }
      .agentConflictMatrix { display:grid; gap:6px; }
      .agentMatrixRow { grid-template-columns:92px 86px 76px 76px 70px minmax(120px,1fr); gap:7px; padding:7px 8px; border-radius:7px; font-size:11px; }
      .agentMatrixRow span:first-child { font-weight:800; }
      .agentMatrixRow.context { border-left:3px solid #64748b; }
      @media (max-width: 780px) {
        .priorityAgentRow, .priorityAgentHead { grid-template-columns:1fr 72px 76px; }
        .priorityAgentRow > div:nth-child(4), .priorityAgentHead > span:nth-child(4), .priorityAgentRow > div:nth-child(5), .priorityAgentHead > span:nth-child(5) { display:none; }
        .agentMatrixRow { grid-template-columns:1fr 80px 70px; }
        .agentMatrixRow span:nth-child(4), .agentMatrixRow span:nth-child(5), .agentMatrixRow small { display:none; }
      }
    `;
    document.head.appendChild(style);
  }

  function countByRole(reports) {
    const counts = { structure: 0, momentum: 0, context: 0, risk: 0, decision: 0, other: 0 };
    (reports || []).forEach(report => {
      const role = patchedAgentRole(report);
      counts[role] = (counts[role] || 0) + 1;
    });
    return counts;
  }

  function installPatch() {
    window.agentRole = patchedAgentRole;
    window.agentRoleLabel = patchedAgentRoleLabel;
    window.isRiskPipelineReport = patchedIsRiskPipelineReport;
    window.filterAgentReportsByRole = patchedFilterAgentReportsByRole;
    window.agentRoleContractCounts = countByRole;
    ensureAgentRoleFilterOptions();
    injectRoleUiStyles();
    document.body.dataset.agentRolePatch = PATCH_VERSION;
  }

  installPatch();
  document.addEventListener('DOMContentLoaded', installPatch);
  window.addEventListener('load', installPatch);
})();
