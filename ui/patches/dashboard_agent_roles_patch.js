// ==================================================
// dashboard_agent_roles_patch.js
// ==================================================
// DASHBOARD AGENT ROLE CONTRACT PATCH
// ==================================================

(function () {
  const PATCH_VERSION = '2026-05-31-role-ui-v7-toolbar-breakpoint';

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
      #agentView > .card {
        padding:14px 16px !important;
      }
      #agentView .agentToolbar {
        display:grid !important;
        grid-template-columns:minmax(180px, 1.2fr) minmax(145px, .7fr) minmax(145px, .7fr) minmax(130px, .48fr) minmax(160px, .65fr) !important;
        gap:8px !important;
        margin-bottom:8px !important;
        padding:9px 10px !important;
        border-radius:5px !important;
        align-items:end !important;
      }
      #agentView .agentToolbar label {
        margin-bottom:4px !important;
        font-size:10.5px !important;
        line-height:1.2 !important;
      }
      #agentView .agentToolbar select,
      #agentView .agentToolbar button {
        min-height:34px !important;
        padding:6px 9px !important;
        font-size:11.5px !important;
      }
      #agentView #agentStatus {
        min-height:34px !important;
        display:flex !important;
        align-items:center !important;
        padding:6px 8px !important;
        border:1px solid rgba(148,163,184,.20) !important;
        border-radius:4px !important;
        background:rgba(15,23,42,.16) !important;
        font-size:11px !important;
        line-height:1.25 !important;
      }
      #agentView .agentActionPanel {
        display:grid !important;
        grid-template-columns:minmax(0, 1fr) auto !important;
        align-items:center !important;
        margin:0 0 8px !important;
        padding:8px 10px !important;
        gap:10px !important;
        border-radius:5px !important;
      }
      #agentView .agentActionText {
        font-size:11px !important;
        line-height:1.3 !important;
      }
      #agentView .agentActionButtons {
        gap:8px !important;
        justify-content:flex-end !important;
      }
      #agentView .agentActionButtons .controlButton {
        min-height:32px !important;
        padding:6px 10px !important;
        font-size:11.5px !important;
      }
      #agentView .agentFrame {
        min-height:0 !important;
        padding:10px !important;
        display:grid !important;
        gap:8px !important;
        border-radius:5px !important;
      }
      #agentView .agentLlmTeamDetails,
      #agentView .agentDiagnosticsDetails {
        border-radius:5px !important;
        margin:0 !important;
      }
      #agentView .agentLlmTeamSummary {
        min-height:46px !important;
        padding:9px 12px !important;
        gap:10px !important;
      }
      #agentView .agentLlmTeamSummary strong {
        font-size:13px !important;
        letter-spacing:.02em !important;
      }
      #agentView .agentLlmTeamSummary small {
        margin-top:2px !important;
        font-size:11px !important;
        line-height:1.25 !important;
      }
      #agentView .agentLlmTeamDetails .llmAuditCard,
      #agentView #agentCeoCard {
        padding:10px !important;
      }
      #agentView .llmAuditCompact {
        gap:8px !important;
      }
      #agentView .llmAuditStrip {
        gap:6px !important;
      }
      #agentView .llmAuditStrip div,
      #agentView .llmAuditItem {
        min-height:0 !important;
        padding:7px 8px !important;
        border-radius:4px !important;
      }
      #agentView .llmTalkPanel {
        gap:7px !important;
      }
      #agentView .llmTalkTitle span {
        margin-left:8px !important;
        color:#93c5fd !important;
        font-size:9.5px !important;
        letter-spacing:.04em !important;
      }
      #agentView .llmTalkGrid {
        grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)) !important;
        gap:7px !important;
      }
      #agentView .llmTalkJudge,
      #agentView .llmTalkCard {
        padding:8px 9px !important;
        border-radius:4px !important;
      }
      #agentView .llmTalkMeta {
        margin-top:6px !important;
        padding-top:6px !important;
        border-top:1px solid rgba(148,163,184,.14) !important;
      }
      #agentView .llmTalkMeta span {
        display:block !important;
        color:var(--muted) !important;
        font-size:9.5px !important;
        font-weight:900 !important;
        text-transform:uppercase !important;
        letter-spacing:.06em !important;
      }
      #agentView .llmTalkMeta p {
        margin:3px 0 0 !important;
        color:#cbd5e1 !important;
        font-size:11.5px !important;
        line-height:1.35 !important;
        overflow-wrap:anywhere !important;
      }
      #agentView .llmTalkMeta.answer p {
        color:var(--ink) !important;
      }
      #agentView .llmAnalysisHistory {
        border:1px solid var(--line) !important;
        border-radius:5px !important;
        background:var(--panel-soft) !important;
        padding:8px 10px !important;
      }
      #agentView .llmAnalysisHistory > summary {
        cursor:pointer !important;
        list-style:none !important;
        display:inline-flex !important;
        align-items:center !important;
        gap:6px !important;
        width:max-content !important;
        max-width:100% !important;
        box-sizing:border-box !important;
        border:0 !important;
        background:transparent !important;
        padding:0 !important;
        color:#93c5fd !important;
        font-size:10.5px !important;
        font-weight:900 !important;
        text-transform:uppercase !important;
        letter-spacing:.06em !important;
      }
      #agentView .llmAnalysisHistory > summary::-webkit-details-marker {
        display:none !important;
      }
      #agentView .llmAnalysisHistory > summary::before {
        content:">" !important;
        color:#93c5fd !important;
        font-size:15px !important;
        line-height:1 !important;
        transform:translateY(-1px) !important;
      }
      #agentView .llmAnalysisHistory[open] > summary::before {
        content:"" !important;
        display:none !important;
      }
      #agentView .llmAnalysisHistory[open] > summary {
        color:var(--muted) !important;
      }
      #agentView .llmHistoryGrid {
        display:grid !important;
        grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)) !important;
        gap:7px !important;
        padding-top:8px !important;
      }
      #agentView .llmHistoryItem {
        border:1px solid rgba(148,163,184,.18) !important;
        border-radius:4px !important;
        background:rgba(15,23,42,.58) !important;
        padding:8px 9px !important;
        min-width:0 !important;
      }
      #agentView .llmHistoryTop {
        display:flex !important;
        align-items:center !important;
        justify-content:space-between !important;
        gap:8px !important;
      }
      #agentView .llmHistoryItem p,
      #agentView .llmHistoryItem small {
        overflow-wrap:anywhere !important;
      }
      #agentView .agentDiagnosticsDetails {
        padding:8px !important;
      }
      #agentView .agentDiagnosticsBody {
        gap:8px !important;
        margin-top:8px !important;
      }
      #agentView .agentDecisionGrid {
        gap:8px !important;
      }
      #agentView .agentSection {
        padding:9px !important;
        border-radius:5px !important;
      }
      #agentView .agentSection h3 {
        margin:0 0 7px !important;
        font-size:11px !important;
        letter-spacing:.06em !important;
      }
      .agentGrid { align-items:start !important; }
      .agentRoleGroup { align-self:start !important; align-content:start !important; grid-template-rows:auto auto !important; margin-top:6px; border:1px solid rgba(148,163,184,.28); border-radius:4px; overflow:hidden; background:rgba(15,23,42,.10); }
      .agentRoleGroup.structure { border-left:3px solid #38bdf8; }
      .agentRoleGroup.momentum { border-left:3px solid #22c55e; }
      .agentRoleGroup.context { border-left:3px solid #64748b; }
      .agentRoleGroup.risk { border-left:3px solid #f97316; }
      .agentRoleGroup.decision { border-left:3px solid #a855f7; }
      .agentRoleGroupTitle { min-height:30px; padding:7px 10px; font-size:11px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; display:flex; justify-content:space-between; align-items:center; background:rgba(15,23,42,.28); border-bottom:1px solid rgba(148,163,184,.22); }
      .agentRoleGroupTitle span { color:var(--muted); font-family:"JetBrains Mono", "Cascadia Code", Consolas, monospace; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
      .agentRoleGroup .agentGrid { padding:7px; display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); align-items:start; gap:6px; }
      .sourceReportTable { align-self:start !important; }
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
      .priorityDecisionCenter, .ceoExplainPanel, .agentConflictPanel, .agentDecisionDetails { border-radius:4px !important; padding:8px !important; border:1px solid rgba(148,163,184,.24) !important; background:rgba(15,23,42,.12) !important; }
      .agentDecisionDetails summary { cursor:pointer; color:var(--muted); font-size:11px !important; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }
      #agentView .agentLlmTeamSummary,
      #agentView .agentDiagnosticsDetails > summary,
      #agentView .agentSourceDetails > summary,
      #agentView .agentConflictPanel > summary,
      #agentView .agentDecisionDetails > summary,
      #agentView .llmAuditNotes > summary,
      #agentView .llmTraceBox details > summary {
        cursor:pointer !important;
        list-style:none !important;
        display:flex !important;
        align-items:center !important;
        justify-content:flex-start !important;
        gap:6px !important;
        width:100% !important;
        min-height:40px !important;
        box-sizing:border-box !important;
        border:1px solid var(--line) !important;
        border-left:4px solid #60a5fa !important;
        border-radius:6px !important;
        background:linear-gradient(90deg, rgba(96,165,250,.10), rgba(15,23,42,.18) 42%) !important;
        color:#93c5fd !important;
        padding:8px 11px !important;
        user-select:none !important;
      }
      #agentView .agentLlmTeamSummary { border-left-color:#22d3ee !important; background:linear-gradient(90deg, rgba(34,211,238,.10), rgba(15,23,42,.18) 42%) !important; }
      #agentView .agentDiagnosticsDetails > summary,
      #agentView .agentSourceDetails > summary { border-left-color:#14b8a6 !important; background:linear-gradient(90deg, rgba(20,184,166,.09), rgba(15,23,42,.18) 42%) !important; }
      #agentView .agentConflictPanel > summary,
      #agentView .agentDecisionDetails > summary { border-left-color:#f59e0b !important; background:linear-gradient(90deg, rgba(245,158,11,.10), rgba(15,23,42,.18) 42%) !important; }
      #agentView .llmAuditNotes > summary,
      #agentView .llmTraceBox details > summary { border-left-color:#38bdf8 !important; background:linear-gradient(90deg, rgba(56,189,248,.09), rgba(15,23,42,.18) 42%) !important; }
      #agentView .agentLlmTeamSummary::-webkit-details-marker,
      #agentView .agentDiagnosticsDetails > summary::-webkit-details-marker,
      #agentView .agentSourceDetails > summary::-webkit-details-marker,
      #agentView .agentConflictPanel > summary::-webkit-details-marker,
      #agentView .agentDecisionDetails > summary::-webkit-details-marker,
      #agentView .llmAuditNotes > summary::-webkit-details-marker,
      #agentView .llmTraceBox details > summary::-webkit-details-marker {
        display:none !important;
      }
      #agentView .agentLlmTeamSummary::after,
      #agentView .agentDiagnosticsDetails > summary::after,
      #agentView .agentSourceDetails > summary::after,
      #agentView .agentConflictPanel > summary::after,
      #agentView .agentDecisionDetails > summary::after,
      #agentView .llmAuditNotes > summary::after,
      #agentView .llmTraceBox details > summary::after {
        content:"" !important;
        display:none !important;
        justify-content:center !important;
        min-height:28px !important;
        padding:4px 9px !important;
        border:1px solid var(--line) !important;
        border-radius:4px !important;
        background:var(--panel-soft) !important;
        color:#93c5fd !important;
        font-size:11px !important;
        font-weight:900 !important;
        line-height:1.1 !important;
        white-space:nowrap !important;
        text-transform:none !important;
        letter-spacing:0 !important;
      }
      #agentView details[open] > .agentLlmTeamSummary::after,
      #agentView .agentDiagnosticsDetails[open] > summary::after,
      #agentView .agentSourceDetails[open] > summary::after,
      #agentView .agentConflictPanel[open] > summary::after,
      #agentView .agentDecisionDetails[open] > summary::after,
      #agentView .llmAuditNotes[open] > summary::after,
      #agentView .llmTraceBox details[open] > summary::after {
        content:"" !important;
        display:none !important;
      }
      #agentView .agentDiagnosticsDetails > summary::before,
      #agentView .agentSourceDetails > summary::before,
      #agentView .agentConflictPanel > summary::before,
      #agentView .agentDecisionDetails > summary::before,
      #agentView .llmAuditNotes > summary::before,
      #agentView .llmTraceBox details > summary::before {
        content:">" !important;
        color:#93c5fd !important;
        font-size:15px !important;
        line-height:1 !important;
        transform:translateY(-1px) !important;
      }
      #agentView .agentDiagnosticsDetails[open] > summary::before,
      #agentView .agentSourceDetails[open] > summary::before,
      #agentView .agentConflictPanel[open] > summary::before,
      #agentView .agentDecisionDetails[open] > summary::before,
      #agentView .llmAuditNotes[open] > summary::before,
      #agentView .llmTraceBox details[open] > summary::before {
        content:"" !important;
        display:none !important;
      }
      #agentView .agentDiagnosticsDetails[open] > summary,
      #agentView .agentSourceDetails[open] > summary,
      #agentView .agentConflictPanel[open] > summary,
      #agentView .agentDecisionDetails[open] > summary,
      #agentView .llmAuditNotes[open] > summary,
      #agentView .llmTraceBox details[open] > summary {
        color:var(--muted) !important;
        border-left-color:rgba(96,165,250,.48) !important;
        background:linear-gradient(90deg, rgba(96,165,250,.035), rgba(15,23,42,.12) 42%) !important;
      }
      #agentView details[open] > .agentLlmTeamSummary { border-left-color:rgba(34,211,238,.52) !important; background:linear-gradient(90deg, rgba(34,211,238,.035), rgba(15,23,42,.12) 42%) !important; color:var(--muted) !important; }
      #agentView .agentDiagnosticsDetails[open] > summary,
      #agentView .agentSourceDetails[open] > summary { border-left-color:rgba(20,184,166,.48) !important; background:linear-gradient(90deg, rgba(20,184,166,.03), rgba(15,23,42,.12) 42%) !important; }
      #agentView .agentConflictPanel[open] > summary,
      #agentView .agentDecisionDetails[open] > summary { border-left-color:rgba(245,158,11,.52) !important; background:linear-gradient(90deg, rgba(245,158,11,.035), rgba(15,23,42,.12) 42%) !important; }
      #agentView .llmAuditNotes[open] > summary,
      #agentView .llmTraceBox details[open] > summary { border-left-color:rgba(56,189,248,.48) !important; background:linear-gradient(90deg, rgba(56,189,248,.03), rgba(15,23,42,.12) 42%) !important; }
      .agentDecisionDetailsGrid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px; margin-top:10px; }
      .priorityTitle, .ceoExplainTitle, .agentConflictTitle { font-size:11px !important; font-weight:900; letter-spacing:.10em; text-transform:uppercase; }
      select#agentRoleFilter, select#agentSortMode, select#agentAsset { border-radius:3px !important; font-size:12px; }
      @media (max-width: 980px) {
        #agentView .agentToolbar {
          grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
        }
        #agentView #agentStatus {
          grid-column:1 / -1 !important;
        }
      }
      @media (max-width: 560px) {
        body { font-size:12px; }
        #agentView .agentToolbar,
        #agentView .agentActionPanel {
          grid-template-columns:1fr !important;
        }
        #agentView .agentActionButtons {
          justify-content:flex-start !important;
        }
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
