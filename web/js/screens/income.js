// =========================================================================
// INCOME — reported students' booked fees, drilled by campus → course →
// hostel type.
//   • Overview     — every campus: total reported income + count + avg fee
//   • Campus drill — that campus's income by course (AC + Non-A/C combined)
//   • Course drill — AC and Non-A/C blocks for that course, with the students
//
// "Income" = Σ `final_fee` of REPORTED students only (matches the Home hero's
// "Reported income"); a blank fee counts toward the headcount but not the avg.
// No backend of its own — computed client-side from api().students(), the same
// payload the rest of the app uses. Mirrors the Expenditure screen's look.
// =========================================================================
const IN = {
  students: null,
  level: 'overview', campus: null, course: null,
  campusSort: { key: 'income', dir: -1 },
  courseSort: { key: 'income', dir: -1 },
};

async function buildIncome() {
  $('#main').innerHTML = skelPage();
  const data = await api().students();
  IN.allStudents = (data && data.students) || [];
  IN.meta = (data && data.meta) || {};
  IN.level = 'overview'; IN.campus = null; IN.course = null;
  renderIncome();
}

// ---- helpers ------------------------------------------------------------
function inNum(v) { const n = Number(v); return Number.isFinite(n) ? n : null; }
function inAcc() { return { income: 0, adm: 0, feeN: 0 }; }
function inAvg(a) { return a.feeN ? Math.round(a.income / a.feeN) : null; }
function inReported() { return IN.students.filter((s) => s.status_category === 'REPORTED'); }
function inCampusOf(s) { return (s.campus || '').trim() || '—'; }
function inCourseOf(s) { return (s.application_course || '').trim() || '—'; }

// Sum reported students into an income accumulator, grouped by keyFn.
function inGroupBy(students, keyFn) {
  const m = new Map();
  students.forEach((s) => {
    const k = keyFn(s);
    let a = m.get(k); if (!a) { a = inAcc(); m.set(k, a); }
    a.adm++; const f = inNum(s.final_fee); if (f != null) { a.income += f; a.feeN++; }
  });
  return m;
}
// Sort enriched rows; blank metrics sink to the bottom either direction, ties
// fall back to the name column.
function inSortRows(rows, sort, nameKey) {
  return rows.slice().sort((a, b) => {
    if (sort.key === nameKey) return sort.dir * cmpv(a[nameKey], b[nameKey]);
    const av = a[sort.key], bv = b[sort.key];
    if (av == null && bv == null) return cmpv(a[nameKey], b[nameKey]);
    if (av == null) return 1;
    if (bv == null) return -1;
    return sort.dir * (av - bv) || cmpv(a[nameKey], b[nameKey]);
  });
}
function inNextSort(cur, k, nameKey) {
  return { key: k, dir: cur.key === k ? -cur.dir : (k === nameKey ? 1 : -1) };
}

const IN_CAMPUS_COLS = [
  { key: 'campus', label: 'Campus' }, { key: 'income', label: 'Income' },
  { key: 'adm', label: 'Reported' }, { key: 'avg', label: 'Avg Fee' },
  { key: 'share', label: '% of Income' },
];
const IN_COURSE_COLS = [{ key: 'course', label: 'Course' }].concat(IN_CAMPUS_COLS.slice(1));

// ---- render dispatch ----------------------------------------------------
function renderIncome() {
  // Narrow the working set to the active city (org-wide admins slicing the
  // dashboard); '' = all. Everything downstream reads IN.students.
  IN.students = studentsInCity(IN.allStudents, (IN.meta || {}).campus_city);
  if (IN.level === 'campus') return renderIncomeCampus();
  if (IN.level === 'course') return renderIncomeCourse();
  return renderIncomeOverview();
}

// One summary table (campus or course rows) + a pinned grand-total row.
function inSummaryTable(recs, total, totAdm, totFeeN, cols, sort, attr, rowAttr, eyebrow, hint) {
  const sorted = inSortRows(recs, sort, cols[0].key);
  const gavg = totFeeN ? fmtFee(Math.round(total / totFeeN)) : '—';
  const grand = `<tr class="ex-total"><td class="nm-cell">${esc(eyebrow.all)}</td>
      <td class="mono">${fmtLk(total)}</td><td class="mono">${totAdm}</td>
      <td class="mono">${gavg}</td><td class="mono">100%</td></tr>`;
  const rows = sorted.map((r) => `<tr ${rowAttr}="${esc(r[cols[0].key])}" title="${esc(eyebrow.row)}">
      <td class="nm-cell">${esc(r[cols[0].key])}</td>
      <td class="mono">${fmtLk(r.income)}</td>
      <td class="mono">${r.adm}</td>
      <td class="mono">${r.avg != null ? fmtFee(r.avg) : '—'}</td>
      <td class="mono">${r.share}%</td></tr>`).join('');
  return `<div class="eyebrow av-tablehead">${esc(eyebrow.title)}
      <span class="av-hint">${esc(hint)}</span></div>
    <div class="table-wrap"><table class="ledger exp">
      <thead><tr id="inHead">${sortHead(cols, sort.key, sort.dir, attr)}</tr></thead>
      <tbody>${grand}${rows}</tbody></table></div>`;
}

// ---- level 1: all campuses ---------------------------------------------
function renderIncomeOverview() {
  const rep = inReported();
  const head = pageHead('Income',
    "Reported students' booked fees — total income, by campus. Click a campus to drill into its courses.",
    'Analytics');
  const bar = `<div class="controlbar">${cityFilterHtml((IN.meta || {}).cities)}</div>`;
  if (!rep.length) {
    $('#main').innerHTML = head + bar + emptyHtml('rupee', 'No income yet',
      'Income appears here once admissions are marked reported.');
    wireCityFilter(renderIncome);
    return;
  }
  const recs = [...inGroupBy(rep, inCampusOf).entries()]
    .map(([campus, a]) => ({ campus, ...a, avg: inAvg(a) }));
  const total = recs.reduce((t, r) => t + r.income, 0);
  const totFeeN = recs.reduce((t, r) => t + r.feeN, 0);
  recs.forEach((r) => { r.share = total ? Math.round(r.income / total * 100) : 0; });

  $('#main').innerHTML = head + bar + `<div id="inBody"></div>`;
  $('#phStats').innerHTML =
    statChip(fmtLk(total), 'Reported Income') + statChip(rep.length, 'Reported')
    + statChip(recs.length, 'Campuses')
    + statChip(totFeeN ? fmtFee(Math.round(total / totFeeN)) : '—', 'Avg Fee', true);

  $('#inBody').innerHTML = inSummaryTable(recs, total, rep.length, totFeeN,
    IN_CAMPUS_COLS, IN.campusSort, 'ckey', 'data-campus',
    { title: 'Reported income by campus', all: 'All campuses', row: "See this campus's courses" },
    'click a campus to drill into its courses');

  $('#inHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    IN.campusSort = inNextSort(IN.campusSort, th.dataset.ckey, 'campus'); renderIncomeOverview();
  };
  $('#inBody').querySelectorAll('tr[data-campus]').forEach((tr) =>
    tr.onclick = () => { IN.campus = tr.dataset.campus; IN.level = 'campus'; renderIncome(); });
  wireCityFilter(renderIncome);
}

// ---- level 2: one campus → courses -------------------------------------
function renderIncomeCampus() {
  const rep = inReported().filter((s) => inCampusOf(s) === IN.campus);
  if (!rep.length) { IN.level = 'overview'; IN.campus = null; return renderIncome(); }
  const recs = [...inGroupBy(rep, inCourseOf).entries()]
    .map(([course, a]) => ({ course, ...a, avg: inAvg(a) }));
  const total = recs.reduce((t, r) => t + r.income, 0);
  const totFeeN = recs.reduce((t, r) => t + r.feeN, 0);
  recs.forEach((r) => { r.share = total ? Math.round(r.income / total * 100) : 0; });

  $('#main').innerHTML =
    `<div class="detail-top"><button class="back-link" id="inBack">${icon('back', 16)}<span>Income</span></button></div>`
    + pageHead(IN.campus, 'Reported income by course — click a course for the AC / Non-A/C split', 'Campus')
    + `<div id="inBody"></div>`;
  $('#phStats').innerHTML =
    statChip(fmtLk(total), 'Reported Income') + statChip(rep.length, 'Reported')
    + statChip(recs.length, 'Courses')
    + statChip(totFeeN ? fmtFee(Math.round(total / totFeeN)) : '—', 'Avg Fee', true);

  $('#inBody').innerHTML = inSummaryTable(recs, total, rep.length, totFeeN,
    IN_COURSE_COLS, IN.courseSort, 'okey', 'data-course',
    { title: 'Reported income by course', all: 'All courses', row: 'See AC / Non-A/C detail' },
    'click a course for the AC / Non-A/C split');

  $('#inBack').onclick = () => { IN.level = 'overview'; IN.campus = null; renderIncome(); };
  $('#inHead').onclick = (e) => {
    const th = e.target.closest('th'); if (!th) return;
    IN.courseSort = inNextSort(IN.courseSort, th.dataset.okey, 'course'); renderIncomeCampus();
  };
  $('#inBody').querySelectorAll('tr[data-course]').forEach((tr) =>
    tr.onclick = () => { IN.course = tr.dataset.course; IN.level = 'course'; renderIncome(); });
}

// ---- level 3: one course → AC / Non-A/C blocks with the students --------
function renderIncomeCourse() {
  const rows = inReported().filter((s) =>
    inCampusOf(s) === IN.campus && inCourseOf(s) === IN.course);
  if (!rows.length) { IN.level = 'campus'; IN.course = null; return renderIncome(); }
  const total = rows.reduce((t, s) => t + (inNum(s.final_fee) || 0), 0);
  const feeN = rows.filter((s) => inNum(s.final_fee) != null).length;

  $('#main').innerHTML =
    `<div class="detail-top"><button class="back-link" id="inBack">${icon('back', 16)}<span>${esc(IN.campus)}</span></button></div>`
    + pageHead(IN.course, `${IN.campus} · reported income split by hostel type`, 'Course')
    + `<div id="inBody"></div>`;
  $('#phStats').innerHTML =
    statChip(fmtLk(total), 'Reported Income') + statChip(rows.length, 'Reported')
    + statChip(feeN ? fmtFee(Math.round(total / feeN)) : '—', 'Avg Fee', true);

  // One block per hostel type — AC, then Non-A/C, then any unset (only if used).
  $('#inBody').innerHTML = ['AC', 'NON-AC', ''].map((h) => {
    const set = rows.filter((s) => (s.hostel || '').trim() === h);
    return set.length ? inHostBlock(h, set) : '';
  }).join('');

  $('#inBack').onclick = () => { IN.level = 'campus'; IN.course = null; renderIncome(); };
  $('#inBody').querySelectorAll('tr[data-id]').forEach((tr) =>
    tr.onclick = () => openStudent(tr.dataset.id));
}

function inHostBlock(h, set) {
  const inc = set.reduce((t, s) => t + (inNum(s.final_fee) || 0), 0);
  const feeN = set.filter((s) => inNum(s.final_fee) != null).length;
  const avg = feeN ? fmtFee(Math.round(inc / feeN)) : '—';
  const body = set.slice().sort((a, b) => cmpv(a.student_name, b.student_name)).map((s) => `
    <tr data-id="${s.id}" title="Open student">
      <td class="mono">${esc(s.appn_no || '—')}</td>
      <td class="nm-cell">${esc(s.student_name)}<div class="sub">${esc(s.father_name || '—')}</div></td>
      <td>${esc(s.grp || '—')}</td>
      <td class="mono">${esc(s.mobile1 || '—')}</td>
      <td class="mono">${s.final_fee != null && s.final_fee !== '' ? fmtFee(s.final_fee) : '—'}</td>
      <td class="mono">${esc(fmtDate(s.reported_date) || '—')}</td>
    </tr>`).join('');
  return `<div class="eyebrow av-tablehead">${avHostBadge(h)}
      <span class="av-hint">${fmtLk(inc)} income · ${set.length} reported · avg ${avg}</span></div>
    <div class="table-wrap"><table class="ledger">
      <thead><tr><th>Appn No</th><th>Student</th><th>Group</th>
        <th>Mobile</th><th>Final Fee</th><th>Reported</th></tr></thead>
      <tbody>${body}</tbody></table></div>`;
}
