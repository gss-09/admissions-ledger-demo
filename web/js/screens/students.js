// =========================================================================
// ADMISSIONS — two screens sharing the students payload:
//   • "students" module → the flat All-Students directory (buildStudents)
//   • "agms" module     → AGM overview → that AGM's execs → that exec's
//                         students (buildAgms). AGMs with no real sub-exec
//                         skip the exec level and go straight to students.
// =========================================================================
const ST = {
  data: null,                                  // {students, meta}
  studSort: { key: 'student_name', dir: 1 },
  agmSort: { key: 'Admissions', dir: -1 },
  execSort: { key: 'Admissions', dir: -1 },
  detSort: { key: 'student_name', dir: 1 },
  agmLevel: 'overview',                         // 'overview' | 'execs' | 'students'
  selectedAgm: null,
  selectedExec: null,                           // null = whole AGM; '(no exec)' = blanks
  gexSort: { key: 'Admissions', dir: -1 },      // global Execs overview sort
  execLevel: 'overview',                        // Execs module: 'overview' | 'students'
  selectedGlobalExec: null,
  dirRows: null,                                // current directory rows (for Export)
  preset: null,                                 // one-shot deep-link filter from the dashboard
};

const STATUS_CLASS = {
  'REPORTED': 's-reported', 'DROPPED': 's-dropped', 'YET TO ARRIVE': 's-coming',
  'SETTLED': 's-settled', 'NOT LIFTING': 's-notlift',
};
const pillClass = (s) => STATUS_CLASS[s] || 's-other';
const stPill = (s) => `<span class="pill-status ${pillClass(s)}">${esc(s || 'YET TO ARRIVE')}</span>`;

function fmtDate(s) {
  if (!s) return '';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s));
  return m ? `${m[3]}-${m[2]}-${m[1]}` : String(s);   // 2026-06-05 -> 05-06-2026
}
function fmtFee(v) {                                    // 45000 -> ₹45,000
  if (v == null || v === '') return '';
  const n = Number(v);
  return Number.isFinite(n) ? '₹' + n.toLocaleString('en-IN') : String(v);
}
function cmpv(a, b) {
  a = a ?? ''; b = b ?? '';
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}
function sortHead(cols, active, dir, attr) {
  return cols.map((c) => {
    const key = typeof c === 'string' ? c : c.key;
    const label = typeof c === 'string' ? c : c.label;
    const cls = key === active ? 'sorted' : '';
    const arr = key === active ? (dir === 1 ? '▲' : '▼') : '▲';
    return `<th data-${attr}="${esc(key)}" class="${cls}">${esc(label)}<span class="arr">${arr}</span></th>`;
  }).join('');
}
function fillSel(el, arr, allLabel) {
  el.innerHTML = `<option value="">${esc(allLabel)}</option>` +
    arr.map((v) => `<option>${esc(v)}</option>`).join('');
}

// ---- shared control markup (one clean search box + compact filter chips) ----
// The filter <select>s carry their meaning in the default "All …" option, so we
// drop the stacked uppercase captions that used to clutter the toolbar.
function searchBox(id, ph) {
  return `<div class="searchbox">${icon('search', 16)}` +
    `<input id="${id}" type="text" placeholder="${esc(ph)}" autocomplete="off"></div>`;
}
function filterSel(id, label) {
  return `<select id="${id}" aria-label="${esc(label)}"></select>`;
}
function clearBtn(id) {
  return `<button class="filter-clear" id="${id}" hidden>${icon('x', 13)}<span>Clear</span></button>`;
}
// Toggle a Clear button's visibility from whether any filter/search is set.
function toggleClear(btnId, selIds, searchId) {
  const btn = $('#' + btnId); if (!btn) return;
  const any = selIds.some((id) => $('#' + id).value) || (searchId && $('#' + searchId).value);
  btn.hidden = !any;
}
function wireClear(btnId, selIds, searchId, fill) {
  const btn = $('#' + btnId); if (!btn) return;
  btn.onclick = () => {
    selIds.forEach((id) => { $('#' + id).value = ''; });
    if (searchId) $('#' + searchId).value = '';
    fill();
  };
}

async function reloadStudents() {
  ST.data = await api().students();
  if (state.module === 'agms') renderAgms();
  else if (state.module === 'execs') renderExecs();
  else renderDirectory();
}

function studentsToolbarActions() {
  const add = canEdit('students')
    ? `<button class="btn btn-primary" id="navAdd">${icon('plus', 15)}<span>Add admission</span></button>` : '';
  const exp = `<button class="btn btn-ghost" id="navExport">${icon('download', 15)}<span>Export Excel</span></button>`;
  return `<div class="screen-actions">${add}${exp}</div>`;
}
function wireStudentActions() {
  const add = $('#navAdd'); if (add) add.onclick = openAddStudent;
  const exp = $('#navExport'); if (exp) exp.onclick = exportAllExcel;
}

// ---- shared funnel summary (used by AGM overview + exec list) ------------
// 'Avg Fee' is a money column: shown only to users with a money tab (the server
// also withholds final_fee from the payload otherwise), so it drops out cleanly.
// 'Target' (admission goal from the PRO+STAFF sheet, via exec_expenditure) is the
// first data column so the goal leads, then Admissions reads achieved-vs-target
// across. It's a goal, not money, so it always shows (the server no longer
// cost-strips it); buckets carry it via `m.Target` (summarize's targetMap /
// execGlobalSummary).
const FUNNEL_COUNT_COLS_BASE = ['Target', 'Admissions', 'Reported', 'Dropped', 'Yet to Arrive',
  'Settled', 'Not Lifting', 'Conversion %'];
function funnelCountColLabels() {
  return canMoney() ? FUNNEL_COUNT_COLS_BASE.concat('Avg Fee') : FUNNEL_COUNT_COLS_BASE.slice();
}
function funnelCols(firstLabel) {
  return [{ key: 'name', label: firstLabel }].concat(funnelCountColLabels());
}
function blankBucket(name) {
  return { name, Admissions: 0, Reported: 0, Dropped: 0, 'Yet to Arrive': 0,
    Settled: 0, 'Not Lifting': 0, _feeSum: 0, _feeN: 0 };
}
// Tally one student into a bucket; accumulate final fees of REPORTED students
// so the bucket can report an average reported final fee.
function tally(m, s) {
  const sc = s.status_category;
  m.Admissions++;
  if (sc === 'REPORTED') {
    m.Reported++;
    const fee = Number(s.final_fee);
    if (s.final_fee != null && s.final_fee !== '' && Number.isFinite(fee)) { m._feeSum += fee; m._feeN++; }
  }
  else if (sc === 'DROPPED') m.Dropped++;
  else if (sc === 'SETTLED') m.Settled++;
  else if (sc === 'NOT LIFTING') m['Not Lifting']++;
  else m['Yet to Arrive']++;   // YET TO ARRIVE + any blank/legacy value
}
function finishBucket(m) {
  m['Conversion %'] = m.Admissions ? Math.round(m.Reported / m.Admissions * 100) : 0;
  m['Avg Fee'] = m._feeN ? Math.round(m._feeSum / m._feeN) : 0;   // avg of reported fees
}
function summarize(students, keyFn, sort, targetMap) {
  const map = {};
  for (const s of students) {
    const k = keyFn(s);
    tally((map[k] ||= blankBucket(k)), s);
  }
  const out = Object.values(map);
  out.forEach((m) => { finishBucket(m); if (targetMap) m.Target = targetMap[m.name] ?? null; });
  out.sort((a, b) => sort.dir * cmpv(a[sort.key], b[sort.key]));
  return out;
}
function funnelCountCells(m) {
  return `<td class="mono">${m.Target != null ? m.Target : '—'}</td>` +
    `<td class="mono">${m.Admissions}</td>` +
    `<td class="mono">${m.Reported}</td>` +
    `<td class="mono">${m.Dropped}</td><td class="mono">${m['Yet to Arrive']}</td>` +
    `<td class="mono">${m.Settled}</td><td class="mono">${m['Not Lifting']}</td>` +
    `<td class="mono conv-num">${m['Conversion %']}%</td>` +
    (canMoney() ? `<td class="mono">${m['Avg Fee'] ? fmtFee(m['Avg Fee']) : '—'}</td>` : '');
}
// Build per-exec + per-AGM admission targets from the org roster (exec_expenditure).
// A target is an admission GOAL; per-AGM target = sum of its execs' targets.
function exTargets(exp) {
  const byExec = {}, byAgm = {}, agmCity = {}, execCity = {};
  ((exp && exp.agms) || []).forEach((a) => {
    let sum = 0, has = false;
    (a.execs || []).forEach((e) => {
      execCity[e.name] = a.city;
      if (e.target != null) {
        byExec[e.name] = (byExec[e.name] || 0) + Number(e.target);
        sum += Number(e.target); has = true;
      }
    });
    agmCity[a.name] = a.city;
    if (has) byAgm[a.name] = (byAgm[a.name] || 0) + sum;
  });
  return { byExec, byAgm, agmCity, execCity };
}
// Total target respecting the active per-city dashboard filter. `cityOf` maps a
// roster name (AGM or exec) → its city, so a city with no execs sums to 0 (not the
// org-wide total).
function totalTarget(byName, cityOf) {
  return Object.keys(byName).reduce((a, n) =>
    (!state.cityFilter || cityOf[n] === state.cityFilter ? a + byName[n] : a), 0);
}
function funnelRowCells(m) {
  return `<td class="nm-cell">${esc(m.name)}</td>` + funnelCountCells(m);
}

// =========================================================================
// STUDENTS MODULE — the flat directory
// =========================================================================
async function buildStudents() {
  $('#main').innerHTML = skelPage();
  ST.data = await api().students();
  renderDirectory();
}

const STUD_COLS = [
  { key: 'appn_no', label: 'Appn No' }, { key: 'student_name', label: 'Student' },
  { key: 'campus', label: 'Campus' }, { key: 'agm', label: 'AGM' },
  { key: 'marketing_exec', label: 'Marketing Exec' }, { key: 'application_course', label: 'Course' },
  { key: 'grp', label: 'Group' },
  { key: 'mobile1', label: 'Mobile' }, { key: 'status_category', label: 'Status' },
];
function renderDirectory() {
  const all = ST.data.students, meta = ST.data.meta;
  const cnt = (s) => all.filter((x) => x.status_category === s).length;
  $('#main').innerHTML =
    pageHead('Students', 'The full applicant directory.', 'Directory') +
    `<div class="controlbar">
       ${searchBox('studSearch', 'Search student, father or mobile…')}
       ${studentsToolbarActions()}
     </div>
     <div class="filterbar">
       <div class="filters">
         ${filterSel('sCity', 'City')}${filterSel('sCampus', 'Campus')}${filterSel('sAgm', 'AGM')}${filterSel('sCourse', 'Course')}${filterSel('sGroup', 'Group')}${filterSel('sStatus', 'Status')}
         ${clearBtn('studClear')}
       </div>
       <span class="count" id="studCount"></span>
     </div>
     <div class="table-wrap"><table class="ledger" id="studTable">
       <thead><tr id="studHead"></tr></thead><tbody id="studBody"></tbody></table>
       <p class="empty" id="studEmpty" hidden>No students match your search.</p></div>`;
  $('#phStats').innerHTML = statChip(all.length, 'Students') + statChip(cnt('REPORTED'), 'Reported')
    + statChip(cnt('DROPPED'), 'Dropped') + statChip(meta.agms.length, 'AGMs', true);

  fillSel($('#sCity'), meta.cities || [], 'All cities');
  fillSel($('#sCampus'), meta.campuses, 'All campuses');
  fillSel($('#sAgm'), meta.agms, 'All AGMs');
  fillSel($('#sCourse'), meta.courses, 'All courses');
  fillSel($('#sGroup'), meta.groups, 'All groups');
  fillSel($('#sStatus'), meta.statuses, 'All statuses');
  // Selecting a city narrows the Campus dropdown to that city's campuses.
  const campusesForCity = (city) => (meta.campuses || [])
    .filter((c) => !city || (meta.campus_city || {})[c] === city);
  const syncCampusOptions = () => {
    const keep = $('#sCampus').value;
    fillSel($('#sCampus'), campusesForCity($('#sCity').value), 'All campuses');
    $('#sCampus').value = campusesForCity($('#sCity').value).includes(keep) ? keep : '';
  };

  // One-shot deep-link from the dashboard (e.g. an action item or AGM row):
  // apply the preset filter once, then clear it so a manual revisit is clean.
  if (ST.preset) {
    const sel = { campus: 'sCampus', agm: 'sAgm', course: 'sCourse', group: 'sGroup', status: 'sStatus' }[ST.preset.field];
    if (sel && $('#' + sel)) $('#' + sel).value = ST.preset.value;
    ST.preset = null;
  }

  const rowsFor = () => {
    let rows = all.slice();
    const city = $('#sCity').value, cp = $('#sCampus').value, a = $('#sAgm').value,
      c = $('#sCourse').value, g = $('#sGroup').value, st = $('#sStatus').value;
    const q = ($('#studSearch').value || '').toLowerCase().trim();
    if (city) rows = rows.filter((r) => (meta.campus_city || {})[r.campus] === city);
    if (cp) rows = rows.filter((r) => r.campus === cp);
    if (a) rows = rows.filter((r) => r.agm === a);
    if (c) rows = rows.filter((r) => r.application_course === c);
    if (g) rows = rows.filter((r) => r.grp === g);
    if (st) rows = rows.filter((r) => r.status_category === st);
    if (q) rows = rows.filter((r) =>
      (r.student_name || '').toLowerCase().includes(q) ||
      (r.father_name || '').toLowerCase().includes(q) ||
      (r.appn_no || '').includes(q) ||
      (r.mobile1 || '').includes(q) || (r.mobile2 || '').includes(q));
    rows.sort((x, y) => ST.studSort.dir * cmpv(x[ST.studSort.key], y[ST.studSort.key]));
    return rows;
  };
  const fill = () => {
    $('#studHead').innerHTML = sortHead(STUD_COLS, ST.studSort.key, ST.studSort.dir, 'skey');
    const rows = rowsFor();
    ST.dirRows = rows;                 // what Export CSV uses
    $('#studCount').textContent = `${rows.length} of ${all.length}`;
    toggleClear('studClear', ['sCity', 'sCampus', 'sAgm', 'sCourse', 'sGroup', 'sStatus'], 'studSearch');
    $('#studEmpty').hidden = rows.length > 0;
    $('#studBody').innerHTML = rows.map((r) => `
      <tr data-id="${r.id}">
        <td class="mono">${esc(r.appn_no || '—')}</td>
        <td class="nm-cell">${esc(r.student_name)}<div class="sub">${esc(r.father_name || '—')}</div></td>
        <td>${esc(r.campus || '—')}</td><td>${esc(r.agm || '—')}</td>
        <td>${esc(r.marketing_exec || '—')}</td><td>${esc(r.application_course || '—')}</td>
        <td>${esc(r.grp || '—')}</td>
        <td class="mono">${esc(r.mobile1 || '—')}</td><td>${stPill(r.status_category)}</td>
      </tr>`).join('');
    $('#studBody').querySelectorAll('tr[data-id]').forEach((tr) =>
      tr.onclick = () => openStudent(tr.dataset.id));
  };
  ['sCampus', 'sAgm', 'sCourse', 'sGroup', 'sStatus'].forEach((id) => $('#' + id).onchange = fill);
  $('#sCity').onchange = () => { syncCampusOptions(); fill(); };
  $('#studSearch').oninput = fill;
  wireClear('studClear', ['sCity', 'sCampus', 'sAgm', 'sCourse', 'sGroup', 'sStatus'], 'studSearch',
    () => { syncCampusOptions(); fill(); });
  $('#studHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    const k = th.dataset.skey; ST.studSort = { key: k, dir: ST.studSort.key === k ? -ST.studSort.dir : 1 }; fill();
  };
  wireStudentActions();
  fill();
}

// =========================================================================
// AGMS MODULE — overview → execs → students
// =========================================================================
// ---- per-city filter helpers for the AGMs / Execs screens ---------------
// Both read the city map from the loaded students payload. AGMs are city-bound,
// so the overview's student set + the exec roster both narrow by city cleanly.
function stCampusCity() { return (ST.data && ST.data.meta && ST.data.meta.campus_city) || {}; }
function stCities() { return (ST.data && ST.data.meta && ST.data.meta.cities) || []; }
function stCityStudents() { return studentsInCity(ST.data.students, stCampusCity()); }
function stRoster() {
  const r = ST.execRoster || [];
  return state.cityFilter ? r.filter((e) => e.city === state.cityFilter) : r;
}

async function buildAgms() {
  $('#main').innerHTML = skelPage();
  // exec_expenditure carries the per-exec admission target (summed per AGM) for the
  // Target column; same student-data access as this tab.
  const [data, exp] = await Promise.all([api().students(), api().exec_expenditure()]);
  ST.data = data;
  ST.targets = exTargets(exp);
  ST.agmLevel = 'overview';
  ST.selectedAgm = null;
  ST.selectedExec = null;
  renderAgms();
}
function renderAgms() {
  if (ST.agmLevel === 'execs') renderAgmExecs();
  else if (ST.agmLevel === 'students') renderAgmStudents();
  else renderAgmOverview();
}

// ---- Level 1: AGM overview ----------------------------------------------
function renderAgmOverview() {
  const all = stCityStudents();
  const cnt = (st) => all.filter((x) => x.status_category === st).length;
  const total = all.length, rep = cnt('REPORTED');
  const cols = funnelCols('AGM');
  $('#main').innerHTML =
    pageHead('AGMs', 'Admissions by recruiter — click an AGM to see their execs.', 'Overview') +
    `<div class="controlbar">
       ${searchBox('agmSearch', 'Search AGM…')}
       ${cityFilterHtml(stCities())}
     </div>
     <div class="table-wrap wide"><table class="ledger funnel" id="agmTable">
       <thead><tr id="agmHead"></tr></thead><tbody id="agmBody"></tbody></table></div>`;
  const totTarget = totalTarget(ST.targets.byAgm, ST.targets.agmCity);
  const agmCount = state.cityFilter
    ? new Set(all.filter((s) => s.agm).map((s) => s.agm)).size
    : ST.data.meta.agms.length;
  $('#phStats').innerHTML = statChip(total, 'Total') + statChip(totTarget || '—', 'Target')
    + statChip(agmCount, 'AGMs')
    + statChip(rep, 'Reported') + statChip((total ? Math.round(rep / total * 100) : 0) + '%', 'Conversion', true);

  const fill = () => {
    $('#agmHead').innerHTML = sortHead(cols, ST.agmSort.key, ST.agmSort.dir, 'agmkey');
    let summ = summarize(all.filter((s) => s.agm), (s) => s.agm, ST.agmSort, ST.targets.byAgm);
    const q = ($('#agmSearch').value || '').toLowerCase().trim();
    if (q) summ = summ.filter((m) => (m.name || '').toLowerCase().includes(q));
    $('#agmBody').innerHTML = summ.map((m) =>
      `<tr data-open="${esc(m.name)}">${funnelRowCells(m)}</tr>`).join('');
    $('#agmBody').querySelectorAll('tr[data-open]').forEach((tr) =>
      tr.onclick = () => openAgm(tr.dataset.open));
  };
  $('#agmHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    const k = th.dataset.agmkey;
    ST.agmSort = { key: k, dir: ST.agmSort.key === k ? -ST.agmSort.dir : (k === 'name' ? 1 : -1) }; fill();
  };
  $('#agmSearch').oninput = fill;
  wireCityFilter(renderAgmOverview);
  fill();
}

// Decide whether a clicked AGM has real sub-execs (→ exec list) or not (→ students).
function openAgm(agm) {
  ST.selectedAgm = agm;
  ST.selectedExec = null;
  const mine = ST.data.students.filter((s) => s.agm === agm);
  const realExecs = new Set();
  mine.forEach((s) => { if (s.marketing_exec && s.marketing_exec !== agm) realExecs.add(s.marketing_exec); });
  if (realExecs.size > 0) { ST.agmLevel = 'execs'; ST.execSort = { key: 'Admissions', dir: -1 }; }
  else { ST.agmLevel = 'students'; }
  ST.detSort = { key: 'student_name', dir: 1 };
  renderAgms();
}

// ---- Level 2: an AGM's marketing execs ----------------------------------
function renderAgmExecs() {
  const mine = ST.data.students.filter((s) => s.agm === ST.selectedAgm);
  const cnt = (st) => mine.filter((s) => s.status_category === st).length;
  const total = mine.length, rep = cnt('REPORTED'), drop = cnt('DROPPED');
  const cols = funnelCols('Marketing Exec');
  $('#main').innerHTML =
    `<div class="detail-top">
       <button class="back-link" id="backToAgms">${icon('back', 16)}<span>AGMs</span></button>
     </div>` +
    pageHead(ST.selectedAgm, 'Marketing execs — click an exec to see their students.', 'AGM') +
    `<div class="controlbar">
       ${searchBox('execSearch', 'Search marketing exec…')}
       <span class="count" id="execCount"></span>
     </div>
     <div class="table-wrap wide"><table class="ledger funnel" id="execTable">
       <thead><tr id="execHead"></tr></thead><tbody id="execBody"></tbody></table></div>`;
  $('#phStats').innerHTML = statChip(total, 'Admissions')
    + statChip(ST.targets.byAgm[ST.selectedAgm] || '—', 'Target')
    + statChip(rep, 'Reported')
    + statChip(drop, 'Dropped') + statChip((total ? Math.round(rep / total * 100) : 0) + '%', 'Conversion', true);

  const fill = () => {
    $('#execHead').innerHTML = sortHead(cols, ST.execSort.key, ST.execSort.dir, 'ekey');
    let summ = summarize(mine, (s) => s.marketing_exec || '(no exec)', ST.execSort, ST.targets.byExec);
    const q = ($('#execSearch').value || '').toLowerCase().trim();
    if (q) summ = summ.filter((m) => (m.name || '').toLowerCase().includes(q));
    $('#execCount').textContent = `${summ.length} marketing exec(s)`;
    $('#execBody').innerHTML = summ.map((m) =>
      `<tr data-exec="${esc(m.name)}">${funnelRowCells(m)}</tr>`).join('');
    $('#execBody').querySelectorAll('tr[data-exec]').forEach((tr) =>
      tr.onclick = () => { ST.selectedExec = tr.dataset.exec; ST.agmLevel = 'students';
        ST.detSort = { key: 'student_name', dir: 1 }; renderAgms(); });
  };
  $('#execHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    const k = th.dataset.ekey;
    ST.execSort = { key: k, dir: ST.execSort.key === k ? -ST.execSort.dir : (k === 'name' ? 1 : -1) }; fill();
  };
  $('#execSearch').oninput = fill;
  $('#backToAgms').onclick = () => { ST.agmLevel = 'overview'; ST.selectedAgm = null; renderAgms(); };
  fill();
}

// ---- Level 3: students under an AGM (optionally scoped to one exec) ------
const DET_COLS = [
  { key: 'appn_no', label: 'Appn No' }, { key: 'student_name', label: 'Student' },
  { key: 'marketing_exec', label: 'Marketing Exec' }, { key: 'campus', label: 'Campus' },
  { key: 'application_course', label: 'Course' }, { key: 'grp', label: 'Group' },
  { key: 'mobile1', label: 'Mobile' },
  { key: 'status_category', label: 'Status' }, { key: 'reported_date', label: 'Reported' },
];
function renderAgmStudents() {
  const meta = ST.data.meta;
  const scoped = ST.selectedExec != null;     // came via an exec row
  const mine = ST.data.students.filter((s) => {
    if (s.agm !== ST.selectedAgm) return false;
    if (!scoped) return true;
    return ST.selectedExec === '(no exec)' ? !s.marketing_exec : s.marketing_exec === ST.selectedExec;
  });
  const cnt = (st) => mine.filter((s) => s.status_category === st).length;
  const total = mine.length, rep = cnt('REPORTED'), drop = cnt('DROPPED');
  const title = scoped ? ST.selectedExec : ST.selectedAgm;
  const sub = scoped ? `Exec under ${ST.selectedAgm}` : 'AGM portfolio';
  const backLabel = scoped ? ST.selectedAgm : 'AGMs';
  $('#main').innerHTML =
    `<div class="detail-top">
       <button class="back-link" id="backUp">${icon('back', 16)}<span>${esc(backLabel)}</span></button>
       <button class="btn btn-ghost" id="detailPrint">${icon('printer', 15)}<span>Print / Export</span></button>
     </div>` +
    pageHead(title, sub, 'Admissions') +
    `<div class="controlbar">
       ${searchBox('rowSearch', 'Search student or father…')}
     </div>
     <div class="filterbar">
       <div class="filters">
         ${filterSel('fCampus', 'Campus')}${filterSel('fCourse', 'Course')}${filterSel('fGroup', 'Group')}${filterSel('fStatus', 'Status')}
         ${clearBtn('rowClear')}
       </div>
       <span class="count" id="rowCount"></span>
     </div>
     <div class="table-wrap"><table class="ledger" id="detTable">
       <thead><tr id="detHead"></tr></thead><tbody id="detBody"></tbody></table>
       <p class="empty" id="detEmpty" hidden>No applications match these filters.</p></div>`;
  $('#phStats').innerHTML = statChip(total, 'Applications') + statChip(rep, 'Reported')
    + statChip(drop, 'Dropped') + statChip((total ? Math.round(rep / total * 100) : 0) + '%', 'Conversion', true);

  fillSel($('#fCampus'), meta.campuses, 'All campuses');
  fillSel($('#fCourse'), meta.courses, 'All courses');
  fillSel($('#fGroup'), meta.groups, 'All groups');
  fillSel($('#fStatus'), meta.statuses, 'All statuses');

  const rowsFor = () => {
    let rows = mine.slice();
    const cp = $('#fCampus').value, c = $('#fCourse').value, g = $('#fGroup').value, st = $('#fStatus').value;
    const q = ($('#rowSearch').value || '').toLowerCase().trim();
    if (cp) rows = rows.filter((r) => r.campus === cp);
    if (c) rows = rows.filter((r) => r.application_course === c);
    if (g) rows = rows.filter((r) => r.grp === g);
    if (st) rows = rows.filter((r) => r.status_category === st);
    if (q) rows = rows.filter((r) =>
      (r.student_name || '').toLowerCase().includes(q) || (r.father_name || '').toLowerCase().includes(q));
    rows.sort((a, b) => ST.detSort.dir * cmpv(a[ST.detSort.key], b[ST.detSort.key]));
    ST.dirRows = rows;                 // Print/Export uses the filtered set
    return rows;
  };
  const fill = () => {
    $('#detHead').innerHTML = sortHead(DET_COLS, ST.detSort.key, ST.detSort.dir, 'dkey');
    const rows = rowsFor();
    toggleClear('rowClear', ['fCampus', 'fCourse', 'fGroup', 'fStatus'], 'rowSearch');
    $('#rowCount').textContent = `${rows.length} of ${mine.length}`;
    $('#detEmpty').hidden = rows.length > 0;
    $('#detBody').innerHTML = rows.map((r) => `
      <tr data-id="${r.id}">
        <td class="mono">${esc(r.appn_no || '—')}</td>
        <td class="nm-cell">${esc(r.student_name)}<div class="sub">${esc(r.father_name || '—')}</div></td>
        <td>${esc(r.marketing_exec || '—')}</td><td>${esc(r.campus || '—')}</td>
        <td>${esc(r.application_course || '—')}</td><td>${esc(r.grp || '—')}</td>
        <td class="mono">${esc(r.mobile1 || '—')}</td>
        <td>${stPill(r.status_category)}</td><td class="mono">${esc(fmtDate(r.reported_date) || '—')}</td>
      </tr>`).join('');
    $('#detBody').querySelectorAll('tr[data-id]').forEach((tr) =>
      tr.onclick = () => openStudent(tr.dataset.id));
  };
  ['fCampus', 'fCourse', 'fGroup', 'fStatus'].forEach((id) => $('#' + id).onchange = fill);
  $('#rowSearch').oninput = fill;
  wireClear('rowClear', ['fCampus', 'fCourse', 'fGroup', 'fStatus'], 'rowSearch', fill);
  $('#detHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    const k = th.dataset.dkey; ST.detSort = { key: k, dir: ST.detSort.key === k ? -ST.detSort.dir : 1 }; fill();
  };
  $('#backUp').onclick = () => {
    ST.agmLevel = scoped ? 'execs' : 'overview';
    ST.selectedExec = null;
    if (!scoped) ST.selectedAgm = null;
    renderAgms();
  };
  $('#detailPrint').onclick = () => openPrint(title, mine);
  fill();
}

// =========================================================================
// EXECS MODULE — a flat global list of every marketing exec
// =========================================================================
async function buildExecs() {
  $('#main').innerHTML = skelPage();
  // Pull the full org roster alongside the students, so an exec with zero
  // admissions still lists (empty funnel) instead of vanishing.
  const [data, exp] = await Promise.all([api().students(), api().exec_expenditure()]);
  ST.data = data;
  ST.targets = exTargets(exp);
  ST.execRoster = [];
  ((exp && exp.agms) || []).forEach((a) => (a.execs || []).forEach((e) =>
    ST.execRoster.push({ name: e.name, agm: a.name, city: a.city })));
  // A dashboard deep-link (ST.preset {field:'exec'}) jumps straight to that
  // exec's students; otherwise start at the overview.
  if (ST.preset && ST.preset.field === 'exec') {
    ST.selectedGlobalExec = ST.preset.value;
    ST.execLevel = 'students';
    ST.detSort = { key: 'student_name', dir: 1 };
    ST.preset = null;
  } else {
    ST.execLevel = 'overview';
    ST.selectedGlobalExec = null;
  }
  renderExecs();
}
function renderExecs() {
  if (ST.execLevel === 'students') renderGlobalExecStudents();
  else renderExecsOverview();
}

// Every distinct marketing_exec across all AGMs, with its full funnel + AGM(s).
function execGlobalSummary(sort) {
  const map = {};
  for (const s of stCityStudents()) {
    if (!s.marketing_exec) continue;
    const m = (map[s.marketing_exec] ||= blankBucket(s.marketing_exec));
    (m._agms ||= new Set()).add(s.agm || '—');
    tally(m, s);
  }
  // Seed every roster exec not seen on a student, so the full org roster lists
  // (zero-admission execs show empty funnels — the "added but no admissions" set).
  stRoster().forEach((e) => {
    if (map[e.name]) return;
    const m = (map[e.name] = blankBucket(e.name));
    (m._agms ||= new Set()).add(e.agm || '—');
  });
  const out = Object.values(map);
  const tmap = (ST.targets && ST.targets.byExec) || {};
  out.forEach((m) => {
    finishBucket(m);
    m.Target = tmap[m.name] ?? null;
    m.agm = m._agms.size === 1 ? [...m._agms][0] : `${m._agms.size} AGMs`;
  });
  out.sort((a, b) => sort.dir * cmpv(a[sort.key], b[sort.key]));
  return out;
}

function execCols() {
  return [{ key: 'name', label: 'Marketing Exec' }].concat(funnelCountColLabels());
}
function renderExecsOverview() {
  const all = stCityStudents();
  const cnt = (st) => all.filter((x) => x.status_category === st).length;
  const total = all.length, rep = cnt('REPORTED');
  const execNames = new Set(all.filter((s) => s.marketing_exec).map((s) => s.marketing_exec));
  stRoster().forEach((e) => execNames.add(e.name));
  const execCount = execNames.size;
  $('#main').innerHTML =
    pageHead('Marketing Execs', 'Every marketing exec — click one to see their students.', 'Overview') +
    `<div class="controlbar">
       ${searchBox('gexSearch', 'Search marketing exec…')}
       ${cityFilterHtml(stCities())}
       <span class="count" id="gexCount"></span>
     </div>
     <div class="table-wrap wide"><table class="ledger funnel" id="gexTable">
       <thead><tr id="gexHead"></tr></thead><tbody id="gexBody"></tbody></table></div>`;
  const totTarget = totalTarget(ST.targets.byExec, ST.targets.execCity);
  $('#phStats').innerHTML = statChip(execCount, 'Marketing Execs') + statChip(totTarget || '—', 'Target')
    + statChip(rep, 'Reported')
    + statChip(cnt('DROPPED'), 'Dropped') + statChip((total ? Math.round(rep / total * 100) : 0) + '%', 'Conversion', true);

  const fill = () => {
    $('#gexHead').innerHTML = sortHead(execCols(), ST.gexSort.key, ST.gexSort.dir, 'gkey');
    let summ = execGlobalSummary(ST.gexSort);
    const q = ($('#gexSearch').value || '').toLowerCase().trim();
    if (q) summ = summ.filter((m) => (m.name || '').toLowerCase().includes(q));
    $('#gexCount').textContent = `${summ.length} marketing exec(s)`;
    $('#gexBody').innerHTML = summ.map((m) =>
      `<tr data-exec="${esc(m.name)}"><td class="nm-cell">${esc(m.name)}</td>${funnelCountCells(m)}</tr>`).join('');
    $('#gexBody').querySelectorAll('tr[data-exec]').forEach((tr) =>
      tr.onclick = () => { ST.selectedGlobalExec = tr.dataset.exec; ST.execLevel = 'students';
        ST.detSort = { key: 'student_name', dir: 1 }; renderExecs(); });
  };
  $('#gexHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    const k = th.dataset.gkey;
    ST.gexSort = { key: k, dir: ST.gexSort.key === k ? -ST.gexSort.dir : (k === 'name' ? 1 : -1) }; fill();
  };
  $('#gexSearch').oninput = fill;
  wireCityFilter(renderExecsOverview);
  fill();
}

// One exec's students (across every AGM they worked under).
const GEX_DET_COLS = [
  { key: 'appn_no', label: 'Appn No' }, { key: 'student_name', label: 'Student' },
  { key: 'agm', label: 'AGM' }, { key: 'campus', label: 'Campus' },
  { key: 'application_course', label: 'Course' }, { key: 'grp', label: 'Group' },
  { key: 'mobile1', label: 'Mobile' },
  { key: 'status_category', label: 'Status' }, { key: 'reported_date', label: 'Reported' },
];
function renderGlobalExecStudents() {
  const meta = ST.data.meta;
  const exec = ST.selectedGlobalExec;
  const mine = ST.data.students.filter((s) => s.marketing_exec === exec);
  const cnt = (st) => mine.filter((s) => s.status_category === st).length;
  const total = mine.length, rep = cnt('REPORTED'), drop = cnt('DROPPED');
  $('#main').innerHTML =
    `<div class="detail-top">
       <button class="back-link" id="backToExecs">${icon('back', 16)}<span>Marketing Execs</span></button>
       <button class="btn btn-ghost" id="detailPrint">${icon('printer', 15)}<span>Print / Export</span></button>
     </div>` +
    pageHead(exec, 'Marketing exec portfolio', 'Admissions') +
    `<div class="controlbar">
       ${searchBox('rowSearch', 'Search student or father…')}
     </div>
     <div class="filterbar">
       <div class="filters">
         ${filterSel('fAgm', 'AGM')}${filterSel('fCampus', 'Campus')}${filterSel('fCourse', 'Course')}${filterSel('fGroup', 'Group')}${filterSel('fStatus', 'Status')}
         ${clearBtn('rowClear')}
       </div>
       <span class="count" id="rowCount"></span>
     </div>
     <div class="table-wrap"><table class="ledger" id="detTable">
       <thead><tr id="detHead"></tr></thead><tbody id="detBody"></tbody></table>
       <p class="empty" id="detEmpty" hidden>No applications match these filters.</p></div>`;
  $('#phStats').innerHTML = statChip(total, 'Applications') + statChip(rep, 'Reported')
    + statChip(drop, 'Dropped') + statChip((total ? Math.round(rep / total * 100) : 0) + '%', 'Conversion', true);

  fillSel($('#fAgm'), [...new Set(mine.map((s) => s.agm).filter(Boolean))].sort(), 'All AGMs');
  fillSel($('#fCampus'), meta.campuses, 'All campuses');
  fillSel($('#fCourse'), meta.courses, 'All courses');
  fillSel($('#fGroup'), meta.groups, 'All groups');
  fillSel($('#fStatus'), meta.statuses, 'All statuses');

  const rowsFor = () => {
    let rows = mine.slice();
    const a = $('#fAgm').value, cp = $('#fCampus').value, c = $('#fCourse').value,
      g = $('#fGroup').value, st = $('#fStatus').value;
    const q = ($('#rowSearch').value || '').toLowerCase().trim();
    if (a) rows = rows.filter((r) => r.agm === a);
    if (cp) rows = rows.filter((r) => r.campus === cp);
    if (c) rows = rows.filter((r) => r.application_course === c);
    if (g) rows = rows.filter((r) => r.grp === g);
    if (st) rows = rows.filter((r) => r.status_category === st);
    if (q) rows = rows.filter((r) =>
      (r.student_name || '').toLowerCase().includes(q) || (r.father_name || '').toLowerCase().includes(q));
    rows.sort((x, y) => ST.detSort.dir * cmpv(x[ST.detSort.key], y[ST.detSort.key]));
    return rows;
  };
  const fill = () => {
    $('#detHead').innerHTML = sortHead(GEX_DET_COLS, ST.detSort.key, ST.detSort.dir, 'dkey');
    const rows = rowsFor();
    toggleClear('rowClear', ['fAgm', 'fCampus', 'fCourse', 'fGroup', 'fStatus'], 'rowSearch');
    $('#rowCount').textContent = `${rows.length} of ${mine.length}`;
    $('#detEmpty').hidden = rows.length > 0;
    $('#detBody').innerHTML = rows.map((r) => `
      <tr data-id="${r.id}">
        <td class="mono">${esc(r.appn_no || '—')}</td>
        <td class="nm-cell">${esc(r.student_name)}<div class="sub">${esc(r.father_name || '—')}</div></td>
        <td>${esc(r.agm || '—')}</td><td>${esc(r.campus || '—')}</td>
        <td>${esc(r.application_course || '—')}</td><td>${esc(r.grp || '—')}</td>
        <td class="mono">${esc(r.mobile1 || '—')}</td>
        <td>${stPill(r.status_category)}</td><td class="mono">${esc(fmtDate(r.reported_date) || '—')}</td>
      </tr>`).join('');
    $('#detBody').querySelectorAll('tr[data-id]').forEach((tr) =>
      tr.onclick = () => openStudent(tr.dataset.id));
  };
  ['fAgm', 'fCampus', 'fCourse', 'fGroup', 'fStatus'].forEach((id) => $('#' + id).onchange = fill);
  $('#rowSearch').oninput = fill;
  wireClear('rowClear', ['fAgm', 'fCampus', 'fCourse', 'fGroup', 'fStatus'], 'rowSearch', fill);
  $('#detHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    const k = th.dataset.dkey; ST.detSort = { key: k, dir: ST.detSort.key === k ? -ST.detSort.dir : 1 }; fill();
  };
  $('#backToExecs').onclick = () => { ST.execLevel = 'overview'; ST.selectedGlobalExec = null; renderExecs(); };
  $('#detailPrint').onclick = () => openPrint(exec, mine);
  fill();
}
