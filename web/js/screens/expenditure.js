// =========================================================================
// EXPENDITURE — what each recruiting team COSTS per admission they deliver.
//
// New data: each exec's `total_amount` (salary + general expenditure + incentive
// + gift) and admission `target` (TOT TARGET) from the PRO+STAFF target-vs-
// achievement sheet, stored on the exec and served by api().exec_expenditure().
// A team's cost/target are the sum of its execs'. Admissions come from the same
// student payload the rest of the app uses (api().students()), joined client-side.
//
// The headline metric is CUT PER ADMISSION = team cost / (reported + settled),
// read against the team's AVG BOOKED FEE — i.e. how much of each fee is eaten by
// acquisition cost. A team (or exec) that took money but produced nothing shows
// its cost with a "—" ratio: dead weight.
//
// Two tabs, both grouped by AGM name (the role labels in the sheet are just tags):
//   • All teams      — every AGM + their execs (the whole org)
//   • Admission AGMs  — only AGMs with a real area, whose job is just admissions
// Mirrors the Averages screen's look (seg-tabs, frozen first column, heat tints).
// =========================================================================
const EX = {
  teams: null, students: null,
  tab: 'field', level: 'overview', selectedTeam: null,
  // Active sort for each table — default to most expensive overall (cost desc),
  // matching the original fixed ordering.
  teamSort: { key: 'cost', dir: -1 },
  execSort: { key: 'cost', dir: -1 },
  // Independent sort for the cost-breakdown tables (overview = AGM, drill = exec).
  bdTeamSort: { key: 'total', dir: -1 },
  bdExecSort: { key: 'total', dir: -1 },
};
// Admissions that count: actually arrived (reported) or part-paid then left
// (settled) — both are real admissions the team delivered.
const EX_DONE = new Set(['REPORTED', 'SETTLED']);

async function buildExpenditure() {
  $('#main').innerHTML = skelPage();
  const [students, exp] = await Promise.all([api().students(), api().exec_expenditure()]);
  EX.allStudents = (students && students.students) || [];
  EX.meta = (students && students.meta) || {};
  EX.allTeams = (exp && exp.agms) || [];
  EX.level = 'overview';
  EX.selectedTeam = null;
  renderExpenditure();
}

// Apply the active city slice (org-wide admins) to the working students + teams.
// AGMs are city-bound, so each team carries one `city`; cost stays exact per city.
function exApplyCity() {
  EX.students = studentsInCity(EX.allStudents, (EX.meta || {}).campus_city);
  EX.teams = state.cityFilter
    ? EX.allTeams.filter((t) => t.city === state.cityFilter) : EX.allTeams;
}

// ---- helpers ------------------------------------------------------------
function exNum(v) { const n = Number(v); return Number.isFinite(n) ? n : null; }
// `adm` = reported+settled (the "Reported" column); `ach` = ALL admissions any
// status (the "Achieved" column, matching the AGMs/Execs tab headcount).
function exAcc() { return { cost: 0, hasCost: false, target: 0, hasTarget: false, adm: 0, ach: 0, feeSum: 0, feeN: 0,
  salary: 0, hasSalary: false, gen_exp: 0, incentive: 0, gift: 0 }; }
function exCutAdm(a) { return a.adm ? Math.round(a.cost / a.adm) : null; }
function exCutAch(a) { return a.ach ? Math.round(a.cost / a.ach) : null; }
function exAvgFee(a) { return a.feeN ? Math.round(a.feeSum / a.feeN) : null; }
function exCutPct(a) {
  const c = exCutAdm(a), f = exAvgFee(a);
  return (c != null && f) ? Math.round(c / f * 100) : null;
}
// Compact rupees for the big totals: ₹2.72 cr / ₹16.86 L; small ones fall back
// to the app-wide ₹-grouped form so the column stays scannable.
function fmtLk(n) {
  if (n == null) return '—';
  if (n >= 1e7) return '₹' + (n / 1e7).toFixed(2) + ' cr';
  if (n >= 1e5) return '₹' + (n / 1e5).toFixed(2) + ' L';
  return fmtFee(n);
}
// A student's exec key — a solo AGM (blank exec) recruits as their own exec.
function exExecKey(s) { return (s.marketing_exec || '').trim() || (s.agm || '').trim(); }
// Diverging heat vs a benchmark: above (more expensive per admission) gets an ink
// wash, below (cheaper) a cool slate wash. Saturates at ±50%. Same visual
// language as the Averages heatmap.
function exHeat(v, bench) {
  if (v == null || bench == null || !bench) return '';
  const d = (v - bench) / bench;
  if (Math.abs(d) < 0.02) return '';
  const a = (Math.min(1, Math.abs(d) / 0.5) * 0.16).toFixed(3);
  return d > 0 ? `background:rgba(20,20,26,${a})` : `background:rgba(96,110,170,${a})`;
}
function exArrow(v, bench) {
  if (v == null || bench == null || v === bench) return '';
  return v > bench
    ? '<span class="av-up" title="costs more per admission than average">▲</span>'
    : '<span class="av-dn" title="costs less per admission than average">▼</span>';
}

// Sortable columns — same six metrics in both tables (only the first label
// differs). Keys match the enriched-row fields built before each table renders.
const EX_TEAM_COLS = [
  { key: 'name', label: 'Team (AGM)' }, { key: 'cost', label: 'Total Cost' },
  { key: 'target', label: 'Target' },
  { key: 'adm', label: 'Reported' }, { key: 'cut', label: 'Exp / Reported' },
  { key: 'ach', label: 'Achieved' }, { key: 'cutAch', label: 'Exp / Achieved' },
  { key: 'fee', label: 'Avg Fee' }, { key: 'pct', label: '% of Fee' },
];
const EX_EXEC_COLS = [{ key: 'name', label: 'Marketing Exec' }].concat(EX_TEAM_COLS.slice(1));

// Sort enriched rows by the active column. Blank metrics (—) always sink to the
// bottom regardless of direction; ties fall back to the name. The pinned total
// row is added after sorting, so it is unaffected.
function exSortRows(rows, sort) {
  return rows.slice().sort((a, b) => {
    if (sort.key === 'name') return sort.dir * cmpv(a.name, b.name);
    const av = a[sort.key], bv = b[sort.key];
    if (av == null && bv == null) return cmpv(a.name, b.name);
    if (av == null) return 1;
    if (bv == null) return -1;
    return sort.dir * (av - bv) || cmpv(a.name, b.name);
  });
}
// Toggle direction when re-clicking the active column, else start descending for
// numbers / ascending for the name column.
function exNextSort(cur, k) {
  return { key: k, dir: cur.key === k ? -cur.dir : (k === 'name' ? 1 : -1) };
}

// Index reported+settled admissions by team (agm) and by exec-within-team.
function exIndex() {
  const byTeam = new Map(), byExec = new Map();
  EX.students.forEach((s) => {
    const team = (s.agm || '').trim();
    if (!team) return;
    const done = EX_DONE.has(s.status_category);   // reported+settled → "Reported"
    const fee = exNum(s.final_fee);
    const bump = (m, k) => {
      let a = m.get(k); if (!a) { a = exAcc(); m.set(k, a); }
      a.ach++;                                       // every admission, any status
      if (done) { a.adm++; if (fee != null) { a.feeSum += fee; a.feeN++; } }
    };
    bump(byTeam, team);
    bump(byExec, team + '||' + exExecKey(s));
  });
  return { byTeam, byExec };
}

// Roll each AGM team up: cost from the exec roster, admissions from the index.
function exAggregate() {
  const { byTeam, byExec } = exIndex();
  const teams = EX.teams
    .map((t) => {
      const acc = exAcc();
      const ti = byTeam.get(t.name);
      if (ti) { acc.adm = ti.adm; acc.ach = ti.ach; acc.feeSum = ti.feeSum; acc.feeN = ti.feeN; }
      const execs = t.execs.map((e) => {
        const cost = exNum(e.total_amount);
        if (cost != null) { acc.cost += cost; acc.hasCost = true; }
        const target = exNum(e.target);
        if (target != null) { acc.target += target; acc.hasTarget = true; }
        // Cost components (SCHEMA_VERSION 10). `salary` is null for non-admission
        // staff (their salary is not an admission cost); gen/inc/gift for everyone.
        const salary = exNum(e.salary);
        if (salary != null) { acc.salary += salary; acc.hasSalary = true; }
        const gen_exp = exNum(e.gen_exp) || 0, incentive = exNum(e.incentive) || 0, gift = exNum(e.gift) || 0;
        acc.gen_exp += gen_exp; acc.incentive += incentive; acc.gift += gift;
        const ei = byExec.get(t.name + '||' + e.name) || exAcc();
        return { id: e.id, name: e.name, cost, target, salary, gen_exp, incentive, gift,
          adm: ei.adm, ach: ei.ach, feeSum: ei.feeSum, feeN: ei.feeN };
      });
      // Team rent (SCHEMA_VERSION 12): a whole-team cost on the AGM, admission
      // (field) teams only. Folded into Total Cost so it flows into the per-adm
      // costs, and itemised as a Rent column in the cost-breakdown table.
      const rent = t.is_field ? (exNum(t.rent) || 0) : 0;
      if (rent) { acc.cost += rent; acc.hasCost = true; }
      return { name: t.name, is_field: t.is_field, execs, ...acc, rent };
    });
  return teams;
}

// ---- top-level render ---------------------------------------------------
function renderExpenditure() {
  exApplyCity();
  if (EX.level === 'team') { renderTeamDrill(); return; }
  const head = pageHead('Expenditure',
    'What each team costs per admission — total spend ÷ (reported + settled), against the booked fee.',
    'Analytics');
  const cityCtl = cityFilterHtml((EX.meta || {}).cities);
  if (!EX.teams || !EX.teams.length) {
    $('#main').innerHTML = head + `<div class="controlbar">${cityCtl}</div>`
      + emptyHtml('wallet', 'No expenditure yet',
        'Recruiter cost data will appear here once it is loaded.');
    wireCityFilter(renderExpenditure);
    return;
  }
  const tabs = `<div class="seg-tabs" id="exTabs">
      <button class="seg-tab ${EX.tab === 'field' ? 'active' : ''}" data-tab="field">Admission AGMs</button>
      <button class="seg-tab ${EX.tab === 'staff' ? 'active' : ''}" data-tab="staff">Staff</button>
      <button class="seg-tab ${EX.tab === 'all' ? 'active' : ''}" data-tab="all">All Teams</button>
    </div>`;
  $('#main').innerHTML = head + `<div class="controlbar">${tabs}${cityCtl}</div><div id="exBody"></div>`;

  const { teams, scope, benchCut, benchCutAch } = exScopeTeams();
  $('#phStats').innerHTML =
    statChip(fmtLk(scope.cost), 'Total Cost')
    + statChip(scope.target || '—', 'Target')
    + statChip(scope.ach, 'Achieved')
    + statChip(benchCutAch != null ? fmtFee(benchCutAch) : '—', 'Expenditure / Achieved')
    + statChip(scope.adm, 'Reported')
    + statChip(benchCut != null ? fmtFee(benchCut) : '—', 'Expenditure / Reported', true);

  $('#exBody').innerHTML = exTeamTable(teams, benchCut, benchCutAch)
    + exBreakdownTable(exBreakdownTeamRows(teams), 'AGM', EX.bdTeamSort, 'exBdTeamHead', 'bdtkey', EX.tab !== 'staff', 0);
  wireExpenditure();
  wireCityFilter(renderExpenditure);
}

// The teams in the active tab + scope totals + the benchmark every row is read
// against (also recomputed on a header re-sort).
function exScopeTeams() {
  const all = exAggregate();
  const teams = EX.tab === 'field' ? all.filter((t) => t.is_field)
    : EX.tab === 'staff' ? all.filter((t) => !t.is_field)
    : all;
  const scope = teams.reduce((a, t) => {
    a.cost += t.cost; a.target += t.target; a.adm += t.adm; a.ach += t.ach; return a;
  }, { cost: 0, target: 0, adm: 0, ach: 0 });
  const benchCut = scope.adm ? Math.round(scope.cost / scope.adm) : null;
  const benchCutAch = scope.ach ? Math.round(scope.cost / scope.ach) : null;
  return { teams, scope, benchCut, benchCutAch };
}

function exTeamTable(teams, benchCut, benchCutAch) {
  const fieldTab = EX.tab === 'field';
  const note = (!fieldTab && teams.some((t) => !t.hasCost))
    ? '<span class="av-leg-sep"></span>some non-field teams have no cost loaded yet'
    : '';

  // Enrich each team with its computed metrics, then sort by the active column.
  // A team with no cost loaded sorts as a blank cost (sinks to the bottom).
  const recs = teams.map((t) => ({
    name: t.name, is_field: t.is_field, hasCost: t.hasCost,
    cost: t.hasCost ? t.cost : null, target: t.hasTarget ? t.target : null,
    ach: t.ach || null, cutAch: exCutAch(t),
    adm: t.adm || null,
    cut: exCutAdm(t), fee: exAvgFee(t), pct: exCutPct(t),
  }));
  const sorted = exSortRows(recs, EX.teamSort);

  const grand = teams.reduce((a, t) => {
    a.cost += t.cost; a.target += t.target; a.adm += t.adm; a.ach += t.ach;
    a.feeSum += t.feeSum; a.feeN += t.feeN; return a;
  }, exAcc());

  const rows = sorted.map((t) => {
    const heat = exHeat(t.cut, benchCut), heatA = exHeat(t.cutAch, benchCutAch);
    const tags = (t.is_field ? '' : '<span class="ex-tag">staff</span>')
      + (t.hasCost ? '' : '<span class="ex-tag">no cost</span>');
    return `<tr data-team="${esc(t.name)}">
      <td class="nm-cell">${esc(t.name)}${tags}</td>
      <td class="mono">${t.hasCost ? fmtLk(t.cost) : '—'}</td>
      <td class="mono">${t.target != null ? t.target : '—'}</td>
      <td class="mono">${t.adm != null ? t.adm : '—'}</td>
      <td class="mono ex-heat"${heat ? ` style="${heat}"` : ''}>${t.cut != null ? fmtFee(t.cut) : '—'}${exArrow(t.cut, benchCut)}</td>
      <td class="mono">${t.ach != null ? t.ach : '—'}</td>
      <td class="mono ex-heat"${heatA ? ` style="${heatA}"` : ''}>${t.cutAch != null ? fmtFee(t.cutAch) : '—'}${exArrow(t.cutAch, benchCutAch)}</td>
      <td class="mono">${t.fee != null ? fmtFee(t.fee) : '—'}</td>
      <td class="mono">${t.pct != null ? t.pct + '%' : '—'}</td>
    </tr>`;
  }).join('');

  const gcut = exCutAdm(grand), gcutA = exCutAch(grand), gfee = exAvgFee(grand), gpct = exCutPct(grand);
  const grandRow = `<tr class="ex-total">
      <td class="nm-cell">All teams</td>
      <td class="mono">${fmtLk(grand.cost)}</td>
      <td class="mono">${grand.target || '—'}</td>
      <td class="mono">${grand.adm}</td>
      <td class="mono">${gcut != null ? fmtFee(gcut) : '—'}</td>
      <td class="mono">${grand.ach}</td>
      <td class="mono">${gcutA != null ? fmtFee(gcutA) : '—'}</td>
      <td class="mono">${gfee != null ? fmtFee(gfee) : '—'}</td>
      <td class="mono">${gpct != null ? gpct + '%' : '—'}</td></tr>`;

  return `<div class="eyebrow av-tablehead">Expenditure per admission by team
      <span class="av-hint">
        <span class="av-leg up"><i>▲</i>above</span>
        <span class="av-leg dn"><i>▼</i>below the avg (Reported ${benchCut != null ? fmtFee(benchCut) : '—'} · Achieved ${benchCutAch != null ? fmtFee(benchCutAch) : '—'})</span>
        <span class="av-leg-sep"></span>click a team to drill in${note}</span></div>
    <div class="table-wrap"><table class="ledger exp">
      <thead><tr id="exTeamHead">${sortHead(EX_TEAM_COLS, EX.teamSort.key, EX.teamSort.dir, 'tkey')}</tr></thead>
      <tbody>${grandRow}${rows}</tbody>
    </table></div>`;
}

// ---- per-person cost breakdown (Salary / Gen Exp / Incentive / Gift) ----
// A second table under the per-admission one: how each team's (overview) or each
// exec's (drill) total_amount splits across the four PRO+STAFF components. Salary
// is blank for non-admission STAFF rows (their salary is not an admission cost),
// so every row's four columns foot to Total (= total_amount). Sorted by Total desc,
// non-interactive (the per-admission table above carries the sortable metrics).
function exBdCols(firstLabel, showRent) {
  const cols = [{ key: 'name', label: firstLabel }, { key: 'salary', label: 'Salary' },
    { key: 'gen_exp', label: 'General Expenditure' }, { key: 'incentive', label: 'Incentives' },
    { key: 'gift', label: 'Gift' }];
  if (showRent) cols.push({ key: 'rent', label: 'Building rent' });
  cols.push({ key: 'total', label: 'Total' });
  return cols;
}
// Sort breakdown rows by the active column; a row with no salary/total (staff
// salary, no-cost team) sorts as blank and sinks, matching the other tables.
function exBdSort(rows, sort) {
  const val = (r) => sort.key === 'salary' ? (r.hasSalary ? r.salary : null)
    : sort.key === 'total' ? (r.hasTotal ? r.total : null) : r[sort.key];
  return rows.slice().sort((a, b) => {
    if (sort.key === 'name') return sort.dir * cmpv(a.name, b.name);
    const av = val(a), bv = val(b);
    if (av == null && bv == null) return cmpv(a.name, b.name);
    if (av == null) return 1;
    if (bv == null) return -1;
    return sort.dir * (av - bv) || cmpv(a.name, b.name);
  });
}
// `showRent` adds the team Rent column (admission AGMs only — hidden on the Staff
// tab / staff drill). `extraRent` is the team's rent at the per-exec drill: rent is
// team-level, so individual exec rows carry none (—) and it lands on the totals row
// so the breakdown still foots to the team's Total Cost.
function exBreakdownTable(rows, firstLabel, sort, headId, attr, showRent, extraRent) {
  extraRent = extraRent || 0;
  const sorted = exBdSort(rows, sort);
  const g = rows.reduce((a, r) => {
    if (r.hasSalary) { a.salary += r.salary; a.hasSalary = true; }
    a.gen_exp += r.gen_exp; a.incentive += r.incentive; a.gift += r.gift;
    if (r.rent) a.rent += r.rent;
    if (r.hasTotal) a.total += r.total;
    return a;
  }, { salary: 0, hasSalary: false, gen_exp: 0, incentive: 0, gift: 0, rent: 0, total: 0, hasTotal: true });
  g.rent += extraRent; g.total += extraRent;
  const c = (v) => (v ? fmtLk(v) : '—');
  const bodyRow = (r, cls) => `<tr${cls ? ` class="${cls}"` : ''}>
      <td class="nm-cell">${esc(r.name)}</td>
      <td class="mono">${r.hasSalary ? c(r.salary) : '—'}</td>
      <td class="mono">${c(r.gen_exp)}</td>
      <td class="mono">${c(r.incentive)}</td>
      <td class="mono">${c(r.gift)}</td>
      ${showRent ? `<td class="mono">${c(r.rent)}</td>` : ''}
      <td class="mono">${r.hasTotal ? fmtLk(r.total) : '—'}</td>
    </tr>`;
  const grandRow = bodyRow({ name: firstLabel === 'Exec' ? 'All execs' : 'All teams',
    ...g, hasTotal: true }, 'ex-total');
  return `<div class="eyebrow av-tablehead" style="margin-top:22px">Cost breakdown · ${firstLabel === 'Exec' ? 'per recruiter' : 'per team'}</div>
    <div class="table-wrap"><table class="ledger exp">
      <thead><tr id="${headId}">${sortHead(exBdCols(firstLabel, showRent), sort.key, sort.dir, attr)}</tr></thead>
      <tbody>${grandRow}${sorted.map((r) => bodyRow(r)).join('')}</tbody>
    </table></div>`;
}
function exBreakdownTeamRows(teams) {
  return teams.map((t) => ({ name: t.name, salary: t.salary, hasSalary: t.hasSalary,
    gen_exp: t.gen_exp, incentive: t.incentive, gift: t.gift, rent: t.rent || 0,
    total: t.cost, hasTotal: t.hasCost }));
}
function exBreakdownExecRows(execs) {
  // Execs carry no rent — it is a team-level cost (passed as extraRent to the table).
  return execs.map((e) => ({ name: e.name, salary: e.salary, hasSalary: e.salary != null,
    gen_exp: e.gen_exp || 0, incentive: e.incentive || 0, gift: e.gift || 0,
    rent: 0, total: e.cost, hasTotal: e.cost != null }));
}

// ---- one team's per-exec breakdown (drill-down) -------------------------
function renderTeamDrill() {
  const team = exAggregate().find((t) => t.name === EX.selectedTeam);
  if (!team) { EX.level = 'overview'; renderExpenditure(); return; }
  const benchCut = exCutAdm(team);      // read each exec against their own team
  const benchCutAch = exCutAch(team);

  const top = `<tr class="ex-total">
      <td class="nm-cell">Team total</td>
      <td class="mono">${fmtLk(team.cost)}</td>
      <td class="mono">${team.target || '—'}</td>
      <td class="mono">${team.adm}</td>
      <td class="mono">${benchCut != null ? fmtFee(benchCut) : '—'}</td>
      <td class="mono">${team.ach}</td>
      <td class="mono">${benchCutAch != null ? fmtFee(benchCutAch) : '—'}</td>
      <td class="mono">${exAvgFee(team) != null ? fmtFee(exAvgFee(team)) : '—'}</td>
      <td class="mono">${exCutPct(team) != null ? exCutPct(team) + '%' : '—'}</td></tr>`;

  $('#main').innerHTML =
    `<div class="detail-top">
       <button class="back-link" id="exBack">${icon('back', 16)}<span>Expenditure</span></button>
     </div>` +
    pageHead(team.name, 'Expenditure per admission by individual recruiter',
      team.is_field ? 'Admission AGM' : 'Staff team') +
    `<div class="eyebrow av-tablehead">Expenditure per admission · exec
       <span class="av-hint">▲ / ▼ vs the team's avg (Reported ${benchCut != null ? fmtFee(benchCut) : '—'} · Achieved ${benchCutAch != null ? fmtFee(benchCutAch) : '—'})</span></div>
     <div class="table-wrap"><table class="ledger exp">
       <thead><tr id="exExecHead"></tr></thead>
       <tbody id="exExecBody"></tbody>
     </table></div>
     <div id="exBdWrap"></div>`;
  const fillBd = () => {
    $('#exBdWrap').innerHTML = exBreakdownTable(exBreakdownExecRows(team.execs), 'Exec',
      EX.bdExecSort, 'exBdExecHead', 'bdxkey', team.is_field, team.is_field ? (team.rent || 0) : 0);
    $('#exBdExecHead').onclick = (e) => {
      const th = e.target.closest('th'); if (!th) return;
      EX.bdExecSort = exNextSort(EX.bdExecSort, th.dataset.bdxkey); fillBd();
    };
  };
  fillBd();
  $('#phStats').innerHTML =
    statChip(fmtLk(team.cost), 'Total Cost')
    + statChip(team.target || '—', 'Target')
    + statChip(team.ach, 'Achieved')
    + statChip(benchCutAch != null ? fmtFee(benchCutAch) : '—', 'Expenditure / Achieved')
    + statChip(team.adm, 'Reported')
    + statChip(benchCut != null ? fmtFee(benchCut) : '—', 'Expenditure / Reported', true);
  $('#exBack').onclick = () => { EX.level = 'overview'; EX.selectedTeam = null; renderExpenditure(); };

  const fill = () => {
    $('#exExecHead').innerHTML = sortHead(EX_EXEC_COLS, EX.execSort.key, EX.execSort.dir, 'xkey');
    const recs = team.execs.map((e) => {
      const acc = { cost: exNum(e.cost) || 0, adm: e.adm, ach: e.ach, feeSum: e.feeSum, feeN: e.feeN };
      return { id: e.id, name: e.name, isAgm: e.name === team.name, cost: exNum(e.cost),
        target: exNum(e.target), ach: e.ach || null, cutAch: exCutAch(acc), adm: e.adm || null,
        cut: exCutAdm(acc), fee: exAvgFee(acc), pct: exCutPct(acc) };
    });
    const rows = exSortRows(recs, EX.execSort).map((e) => {
      const heat = exHeat(e.cut, benchCut), heatA = exHeat(e.cutAch, benchCutAch);
      const tags = (e.isAgm ? '<span class="ex-tag">AGM</span>' : '')
        + (e.adm == null && e.cost != null ? '<span class="ex-tag">no adm</span>' : '');
      return `<tr data-exec="${esc(e.name)}" title="See this exec's admissions">
        <td class="nm-cell">${esc(e.name)}${tags}</td>
        <td class="mono">${e.cost != null ? fmtFee(e.cost) : '—'}</td>
        <td class="mono">${e.target != null ? e.target : '—'}</td>
        <td class="mono">${e.adm != null ? e.adm : '—'}</td>
        <td class="mono ex-heat"${heat ? ` style="${heat}"` : ''}>${e.cut != null ? fmtFee(e.cut) : '—'}${exArrow(e.cut, benchCut)}</td>
        <td class="mono">${e.ach != null ? e.ach : '—'}</td>
        <td class="mono ex-heat"${heatA ? ` style="${heatA}"` : ''}>${e.cutAch != null ? fmtFee(e.cutAch) : '—'}${exArrow(e.cutAch, benchCutAch)}</td>
        <td class="mono">${e.fee != null ? fmtFee(e.fee) : '—'}</td>
        <td class="mono">${e.pct != null ? e.pct + '%' : '—'}</td>
      </tr>`;
    }).join('');
    $('#exExecBody').innerHTML = top + rows;
    // Click an exec → their profile on the Marketing Execs screen (one-shot deep
    // link via ST.preset, the same mechanism the Home leaderboard uses).
    $('#exExecBody').querySelectorAll('tr[data-exec]').forEach((tr) =>
      tr.onclick = () => { ST.preset = { field: 'exec', value: tr.dataset.exec }; openModule('execs'); });
  };
  $('#exExecHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    EX.execSort = exNextSort(EX.execSort, th.dataset.xkey); fill();
  };
  fill();
}

// Rebuild the overview body (per-admission + breakdown tables) in place after a
// header re-sort on either table, then re-wire.
function rerenderExOverview() {
  const { teams, benchCut, benchCutAch } = exScopeTeams();
  $('#exBody').innerHTML = exTeamTable(teams, benchCut, benchCutAch)
    + exBreakdownTable(exBreakdownTeamRows(teams), 'AGM', EX.bdTeamSort, 'exBdTeamHead', 'bdtkey', EX.tab !== 'staff', 0);
  wireExpenditure();
}

// ---- interactions -------------------------------------------------------
function wireExpenditure() {
  const tabs = $('#exTabs');
  if (tabs) tabs.querySelectorAll('.seg-tab').forEach((b) =>
    b.onclick = () => { EX.tab = b.dataset.tab; renderExpenditure(); });
  const head = $('#exTeamHead');
  if (head) head.onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    EX.teamSort = exNextSort(EX.teamSort, th.dataset.tkey);
    rerenderExOverview();
  };
  const bdHead = $('#exBdTeamHead');
  if (bdHead) bdHead.onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    EX.bdTeamSort = exNextSort(EX.bdTeamSort, th.dataset.bdtkey);
    rerenderExOverview();
  };
  $('#main').querySelectorAll('tr[data-team]').forEach((tr) =>
    tr.onclick = () => { EX.selectedTeam = tr.dataset.team; EX.level = 'team'; renderExpenditure(); });
}
