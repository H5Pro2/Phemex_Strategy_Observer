// ==================================================
// dashboard_agent_roles_patch.js
// ==================================================
// DASHBOARD AGENT ROLE CONTRACT PATCH
// ==================================================

(function () {
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
      other: 'Weitere'
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
    if (!select || select.dataset.roleContractPatched === 'true') return;
    const current = select.value || 'all';
    select.innerHTML = [
      ['all', 'Alle Rollen'],
      ['structure', 'Struktur'],
      ['momentum', 'Momentum'],
      ['context', 'Kontext'],
      ['risk', 'Risiko'],
      ['decision', 'Entscheidung']
    ].map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    select.value = ['all', 'structure', 'momentum', 'context', 'risk', 'decision'].includes(current) ? current : 'all';
    select.dataset.roleContractPatched = 'true';
  }

  function installPatch() {
    window.agentRole = patchedAgentRole;
    window.agentRoleLabel = patchedAgentRoleLabel;
    window.isRiskPipelineReport = patchedIsRiskPipelineReport;
    window.filterAgentReportsByRole = patchedFilterAgentReportsByRole;
    ensureAgentRoleFilterOptions();
  }

  installPatch();
  document.addEventListener('DOMContentLoaded', installPatch);
  window.addEventListener('load', installPatch);
})();
