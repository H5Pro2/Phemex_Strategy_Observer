// ==================================================
// dashboard_agent_roles_patch.js
// ==================================================
// DASHBOARD AGENT ROLE CONTRACT PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-17-role-ui-v3-tech';

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
      body { font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif; font-size: 13px; letter-spacing: .005em; }
      code, .agentSignal, .agentQualityPill, .priorityChip, .replayRuleBadge, .tradeStatus,
      .agentCompactKpi strong, .prioritySummaryRow strong, .ceoExplainRow strong, .agentMatrixRow strong {
        font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace; font-variant-numeric: tabular-nums;
      }
      .card, .modal, .settingsGroup, .agentCompactBoard, .priorityDecisionCenter, .ceoExplainPanel,
      .agentConflictPanel, .agentRoleGroup, .agentCube, .agentCeoCard { box-shadow: none !important; }
      .agentRoleGroup { margin-top:10px; border:1px solid rgba(148,163,184,.28); border-radius:4px; overflow:hidden; background:rgba(15,23,42,.10); }
      .agentRoleGroup.structure { border-left:3px solid #38bdf8; }
      .agentRoleGroup.momentum { border-left:3px solid #22c55e; }
      .agentRoleGroup.context { border-left:3px solid #64748b; }
      .agentRoleGroup.risk { border-left:3px solid #f97316; }
      .agentRoleGroup.decision { border-left:3px solid #a855f7; }
      .agentRoleGroupTitle { min-height:30px; padding:7px 10px; font-size:11px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; display:flex; justify-content:space-between; align-items:center; background:rgba(15,23,42,.28); border-bottom:1px solid rgba(148,163,184,.22); }
      .agentRoleGroupTitle span { color:var(--muted); font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
      .agentRoleGroup .agentGrid { padding:9px; display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px; }
      .agentCube, .agentCeoCard { border-radius:4px !important; padding:10px 11px !important; min-height:0 !important; border-color:rgba(148,163,184,.24) !important; background:rgba(15,23,42,.10) !important; }
      .agentCube.long, .agentCeoCard.long { border-left:3px solid #22c55e !important; }
      .agentCube.short, .agentCeoCard.short { border-left:3px solid #ef4444 !important; }
      .agentCube.neutral, .agentCeoCard.neutral { border-left:3px solid #64748b !important; }
      .agentCube.conflict, .agentCeoCard.conflict { border-left:3px solid #f59e0b !important; }
      .agentName { font-size:12px !important; font-weight:800; line-height:1.22; letter-spacing:.01em; }
      .agentFunction { font-size:10.5px !important; line-height:1.35; color:var(--muted); }
      .agentSignal, .agentQualityPill { padding:2px 6px !important; font-size:10px !important; border-radius:3px !important; letter-spacing:.03em; text-transform:uppercase; }
      .agentScore { height:4px !important; margin:7px 0 !important; border-radius:0 !important; background:rgba(148,163,184,.18) !important; }
      .agentScore span { border-radius:0 !important; }
      .agentTextBox { font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; font-size:10.5px !important; line-height:1.4 !important; padding:7px 8px !important; border-radius:3px !important; background:rgba(15,23,42,.20) !important; border:1px solid rgba(148,163,184,.18) !important; }
      .agentCompactBoard { border-radius:4px !important; border:1px solid rgba(148,163,184,.28) !important; background:rgba(15,23,42,.12) !important; }
      .priorityDecisionCenter, .ceoExplainPanel, .agentConflictPanel { border-radius:4px !important; padding:10px !important; border:1px solid rgba(148,163,184,.24) !important; background:rgba(15,23,42,.12) !important; }
      .priorityTitle, .ceoExplainTitle, .agentConflictTitle { font-size:11px !important; font-weight:900; letter-spacing:.10em; text-transform:uppercase; }
      select#agentRoleFilter, select#agentSortMode, select#agentAsset { border-radius:3px !important; font-size:12px; }
      @media (max-width: 780px) { body { font-size:12px; } }
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
