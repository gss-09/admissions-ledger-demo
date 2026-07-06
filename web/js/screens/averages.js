// =========================================================================
// MARKETING AVERAGES — fee analysis that compares like-for-like.
//
// The point: every exec has leeway on the fee, so for the SAME course + hostel
// type one exec books higher and another lower. A flat per-exec average hides
// that because the fee also varies by course and by AC / NON-AC. So we segment
// by **course × hostel type** and average the actual booked `final_fee` within
// each segment — then you can read down a column and see who books high vs low
// for that exact course+type.
//
// Rides on the same student payload the directory loads (api().students()),
// computed entirely client-side — no extra endpoint. Only REPORTED admissions
// count (a "settled" student paid part of the tuition and left). Rows are
// marketing execs grouped under their AGM; an AGM with no sub-exec recruits as
// their own exec and shows as a single self-named row marked "own".
// =========================================================================
const AV = {
  students: null,
  tab: 'execs', level: 'overview', selectedExec: null,
};

async function buildAverages() {
  $('#main').innerHTML = skelPage();
  const data = await api().students();
  AV.allStudents = (data && data.students) || [];
  AV.meta = (data && data.meta) || {};
  AV.level = 'overview';
  AV.selectedExec = null;
  renderAverages();
}

// ---- helpers ------------------------------------------------------------
function avFee(s) {
  if (s.final_fee == null || s.final_fee === '') return null;
  const n = Number(s.final_fee);
  return Number.isFinite(n) ? n : null;
}
// Spell the hostel type out as "Hostel-A/C" / "Hostel-Non A/C" (clearer than a
// bare AC / NON-AC, especially next to a course name that also reads "… A/C").
function avHostLabel(h) {
  if (h === 'AC') return 'Hostel-A/C';
  if (h === 'NON-AC') return 'Hostel-Non A/C';
  return '—';
}
function avHostBadge(h) {
  if (!h) return `<span class="host-badge host-none">—</span>`;
  return `<span class="host-badge ${h === 'AC' ? 'host-ac' : 'host-non'}">${esc(avHostLabel(h))}</span>`;
}
// Reported admissions that count toward the analysis (real course).
function avReported() {
  return AV.students.filter((s) =>
    s.status_category === 'REPORTED'
    && (s.application_course || '').trim());
}
// A solo AGM (no sub-exec) recruits as their own exec → key on the AGM name.
function avExecKey(s) {
  return (s.marketing_exec || '').trim() || (s.agm || '').trim();
}
function avComboKey(course, hostel) { return course + '||' + (hostel || ''); }
function avComboCmp(a, b) {
  return cmpv(a.course, b.course) || cmpv(a.hostel || '~', b.hostel || '~');
}
// A running fee accumulator: count of admissions + sum/n of booked fees + min/max.
function avAcc() { return { count: 0, sum: 0, n: 0, min: Infinity, max: -Infinity }; }
function avAdd(acc, fee) {
  acc.count++;
  if (fee != null) { acc.sum += fee; acc.n++; if (fee < acc.min) acc.min = fee; if (fee > acc.max) acc.max = fee; }
}
function avAvg(acc) { return acc.n ? Math.round(acc.sum / acc.n) : null; }

// Build the course×type combos (columns) and the per-exec rows, each carrying a
// fee accumulator, plus a per-combo benchmark and the overall average.
function avAggregate() {
  const reported = avReported();
  const comboMap = new Map();
  const execMap = new Map();
  const overall = avAcc();
  reported.forEach((s) => {
    const course = (s.application_course || '').trim();
    const hostel = (s.hostel || '').trim();
    const ck = avComboKey(course, hostel);
    const fee = avFee(s);
    overall.count++; if (fee != null) { overall.sum += fee; overall.n++; }

    let c = comboMap.get(ck);
    if (!c) { c = { key: ck, course, hostel, acc: avAcc() }; comboMap.set(ck, c); }
    avAdd(c.acc, fee);

    const ek = avExecKey(s);
    if (!ek) return;
    let e = execMap.get(ek);
    if (!e) {
      e = { name: ek, agm: (s.agm || '').trim() || '—',
        solo: !(s.marketing_exec || '').trim(), cells: {}, acc: avAcc() };
      execMap.set(ek, e);
    }
    avAdd(e.acc, fee);
    (e.cells[ck] ||= avAcc());
    avAdd(e.cells[ck], fee);
  });
  // Seed the full exec roster: every recruiter who appears on ANY admission
  // (not just reported ones). So an exec whose students haven't reported yet
  // still gets a row (empty cells, 0 reported) — it fills in automatically once
  // their students flip to REPORTED on the next load.
  AV.students.forEach((s) => {
    const ek = avExecKey(s);
    if (!ek || execMap.has(ek)) return;
    execMap.set(ek, { name: ek, agm: (s.agm || '').trim() || '—',
      solo: !(s.marketing_exec || '').trim(), cells: {}, acc: avAcc() });
  });
  const combos = [...comboMap.values()].map((c) => ({ ...c, avg: avAvg(c.acc) }));
  const benchmark = {};
  combos.forEach((c) => { benchmark[c.key] = c.avg; });
  const execs = [...execMap.values()].map((e) => ({ ...e, avg: avAvg(e.acc) }));
  return { reported, combos, execs, benchmark,
    overallAvg: avAvg(overall), reportedCount: overall.count };
}

// ---- top-level render ---------------------------------------------------
function renderAverages() {
  // Narrow the working set to the active city (org-wide admins slicing the
  // dashboard); '' = all. Everything downstream reads AV.students.
  AV.students = studentsInCity(AV.allStudents, (AV.meta || {}).campus_city);
  if (AV.level === 'exec') { renderExecDrill(); return; }
  const head = pageHead('Marketing Averages',
    'Booked fee by course & hostel type, on reported admissions only — compare execs like-for-like.',
    'Analytics');
  if (!AV.students.length) {
    $('#main').innerHTML = head + emptyHtml('chart', 'Nothing to analyse yet',
      'Reported admissions will appear here as they come in.');
    return;
  }
  const agg = avAggregate();
  AV.agg = agg;   // stashed so the course-leaderboard modal can read the breakdown
  const tabs = `<div class="seg-tabs" id="avTabs">
      <button class="seg-tab ${AV.tab === 'execs' ? 'active' : ''}" data-tab="execs">Marketing Execs</button>
      <button class="seg-tab ${AV.tab === 'course' ? 'active' : ''}" data-tab="course">Course-wise</button>
    </div>`;
  $('#main').innerHTML = head +
    `<div class="controlbar">${tabs}${cityFilterHtml((AV.meta || {}).cities)}</div><div id="avBody"></div>`;
  // Headline exec count = the full marketing-exec roster (every distinct
  // marketing_exec across all statuses), matching the Execs overview screen —
  // NOT just the reported-active execs that populate the fee pivot below.
  const execTotal = new Set(AV.students.filter((s) => s.marketing_exec).map((s) => s.marketing_exec)).size;
  $('#phStats').innerHTML =
    statChip(agg.reportedCount, 'Reported')
    + statChip(agg.combos.length, 'Course×Type')
    + statChip(execTotal, 'Marketing Execs')
    + statChip(agg.overallAvg != null ? fmtFee(agg.overallAvg) : '—', 'Avg Fee', true);

  $('#avBody').innerHTML = AV.tab === 'course' ? avCourseView(agg) : avExecView(agg);
  wireAverages();
  wireCityFilter(renderAverages);
}

// ---- Course-wise tab (the org-wide benchmark per course×type) -----------
function avCourseView(agg) {
  const combos = agg.combos.slice().sort((a, b) => (b.avg || 0) - (a.avg || 0) || b.acc.count - a.acc.count);
  const maxAvg = Math.max(1, ...combos.map((c) => c.avg || 0));
  // The org-wide mean is the baseline here — shade each course×type by how far it
  // books above (premium) or below (budget) the overall average fee.
  const base = agg.overallAvg;
  // One island: each bar carries the avg (with ▲/▼ vs the overall), the reported
  // count and the fee range — so the old separate breakdown table is gone and a
  // course is clickable in exactly one place.
  const bars = combos.map((c) => {
    const w = c.avg ? Math.round(c.avg / maxAvg * 100) : 0;
    return `<div class="av-bar-row av-click" data-combo="${esc(c.key)}" role="button" tabindex="0" title="See execs for this course & type">
      <div class="av-bar-label"><span class="av-bl-course">${esc(c.course)}</span>${avHostBadge(c.hostel)}</div>
      <div class="av-track"><span class="av-fill" style="width:${w}%"></span></div>
      <div class="av-bar-val">
        <b class="mono">${c.avg != null ? fmtFee(c.avg) : 'no fee'}${avDelta(c.avg, base)}</b>
        <small>${c.acc.count} reported${c.acc.n ? ` · ${esc(avRangeText(c.acc))}` : ''}</small>
      </div>
      <span class="av-go" aria-hidden="true">${icon('chevron', 15)}</span>
    </div>`;
  }).join('');
  return `<div class="panel">
      <div class="eyebrow">Average booked fee by course &amp; hostel type
        <span class="av-hint">
          <span class="av-leg up"><i>▲</i>above</span>
          <span class="av-leg dn"><i>▼</i>below the overall avg ${base != null ? fmtFee(base) : '—'}</span>
          <span class="av-leg-sep"></span>
          click a course for its exec leaderboard</span></div>
      <div class="av-bars">${bars || '<p class="muted-note">No reported admissions.</p>'}</div>
    </div>`;
}
function avRangeText(acc) {
  if (!acc.n) return '—';
  if (acc.min === acc.max) return fmtFee(acc.min);
  return `${fmtFee(acc.min)} – ${fmtFee(acc.max)}`;
}

// ---- Marketing Execs tab (the pivot) ------------------------------------
// Each cell shows the exec's average booked fee for that course×type and a ▲/▼
// against the course benchmark, so leeway (who books higher vs lower) is visible.
function avExecView(agg) {
  // Columns ordered by enrolments — the most-reported course×type first.
  const combos = agg.combos.slice().sort((a, b) => b.acc.count - a.acc.count || avComboCmp(a, b));
  // A flat list of every marketing exec, ranked by reported count (no AGM grouping).
  const execs = agg.execs.slice().sort((a, b) =>
    b.acc.count - a.acc.count || cmpv(a.name, b.name));
  if (!execs.length) return `<div class="panel"><p class="muted-note">No reported admissions to pivot.</p></div>`;
  const ncols = combos.length + 3;   // exec name + combos + avg fee + reported

  const head = `<tr>
      <th class="av-sticky">Marketing Exec</th>
      ${combos.map((c) => `<th class="av-col av-click" data-combo="${esc(c.key)}" title="${esc(c.course)} · ${esc(c.hostel || 'unset')} — see execs for this course & type">
        <span class="av-col-name">${esc(c.course)}</span>
        <span class="av-col-host is-${c.hostel === 'AC' ? 'ac' : 'non'}">${esc(avHostLabel(c.hostel))}</span>
        <span class="av-col-rate mono">${c.avg != null ? fmtFee(c.avg) : '—'}</span>
        <span class="av-col-cap">course avg</span></th>`).join('')}
      <th class="av-wavg-h">Avg Fee</th>
      <th>Reported</th>
    </tr>`;

  // Totals first: the "All execs" roll-up sits at the top, right under the
  // column headers, as the org-wide reference you read every exec against.
  const totCells = combos.map((c) => `<td class="av-c av-tot"><b class="mono">${c.acc.count}</b></td>`).join('');
  let body = `<tr class="av-grand">
      <td class="av-sticky">All execs</td>${totCells}
      <td class="av-wavg mono">${agg.overallAvg != null ? fmtFee(agg.overallAvg) : '—'}</td>
      <td class="mono">${agg.reportedCount}</td></tr>`;
  execs.forEach((e) => {
    const cells = combos.map((c) => {
      const cell = e.cells[c.key];
      if (!cell || !cell.count) return `<td class="av-c av-empty">·</td>`;
      const avg = avAvg(cell);
      const heat = avHeat(avg, agg.benchmark[c.key]);
      return `<td class="av-c"${heat ? ` style="${heat}"` : ''}><b class="mono">${avg != null ? fmtFee(avg) : '—'}${avDelta(avg, agg.benchmark[c.key])}</b><small>×${cell.count}</small></td>`;
    }).join('');
    body += `<tr class="av-exec${e.acc.count ? '' : ' av-exec-zero'}" data-exec="${esc(e.name)}">
        <td class="av-sticky av-exec-name">${esc(e.name)}${e.solo ? '<span class="av-solo">own</span>' : ''}${e.acc.count ? '' : '<span class="av-await">no reports yet</span>'}</td>
        ${cells}
        <td class="av-wavg mono">${e.avg != null ? fmtFee(e.avg) : '—'}</td>
        <td class="mono">${e.acc.count}</td>
      </tr>`;
  });

  return `<div class="eyebrow av-tablehead">Average booked fee · exec × course&amp;type
        <span class="av-hint">
          <span class="av-leg up"><i>▲</i>books above</span>
          <span class="av-leg dn"><i>▼</i>below the course avg</span>
          <span class="av-leg-sep"></span>
          click an exec to drill in</span></div>
      <div class="table-wrap wide"><table class="ledger av-pivot">
        <thead>${head}</thead><tbody>${body}</tbody></table></div>`;
}
// Cell heatmap: shade by how far the exec's booked fee sits from the column
// benchmark — ink wash above (premium), a cool wash below (discount) — so reading
// down a column the high vs low bookers pop out. Saturates at ±25%.
function avHeat(avg, bench) {
  if (avg == null || bench == null || !bench) return '';
  const d = (avg - bench) / bench;
  if (Math.abs(d) < 0.012) return '';
  const a = (Math.min(1, Math.abs(d) / 0.25) * 0.16).toFixed(3);
  return d > 0 ? `background:rgba(20,20,26,${a})` : `background:rgba(96,110,170,${a})`;
}
// A small up/down marker comparing a cell's average to its column benchmark.
function avDelta(avg, bench) {
  if (avg == null || bench == null || avg === bench) return '';
  return avg > bench
    ? '<span class="av-up" title="above the course average">▲</span>'
    : '<span class="av-dn" title="below the course average">▼</span>';
}

// ---- one exec's breakdown (drill-down) ----------------------------------
function renderExecDrill() {
  const name = AV.selectedExec;
  const reported = avReported().filter((s) => avExecKey(s) === name);
  const comboMap = new Map();
  const overall = avAcc();
  reported.forEach((s) => {
    const course = (s.application_course || '').trim();
    const hostel = (s.hostel || '').trim();
    const ck = avComboKey(course, hostel);
    const fee = avFee(s);
    avAdd(overall, fee);
    let c = comboMap.get(ck);
    if (!c) { c = { course, hostel, acc: avAcc() }; comboMap.set(ck, c); }
    avAdd(c.acc, fee);
  });
  // Org-wide benchmark per combo (for the "course average" comparison column).
  const bench = {};
  avAggregate().combos.forEach((c) => { bench[c.key] = c.avg; });

  const combos = [...comboMap.values()].map((c) => ({ ...c, avg: avAvg(c.acc),
    bench: bench[avComboKey(c.course, c.hostel)] }));
  const sorted = combos.slice().sort((a, b) => b.acc.count - a.acc.count || (b.avg || 0) - (a.avg || 0));
  const rows = sorted.map((c) => `<tr>
      <td class="nm-cell">${esc(c.course)}</td><td>${avHostBadge(c.hostel)}</td>
      <td class="mono">${c.avg != null ? fmtFee(c.avg) : '—'}${avDelta(c.avg, c.bench)}</td>
      <td class="mono av-bench">${c.bench != null ? fmtFee(c.bench) : '—'}</td>
      <td class="mono">${c.acc.count}</td>
      <td class="mono av-range">${avRangeText(c.acc)}</td>
    </tr>`).join('');
  $('#main').innerHTML =
    `<div class="detail-top">
       <button class="back-link" id="avBack">${icon('back', 16)}<span>Marketing Averages</span></button>
     </div>` +
    pageHead(name, 'Booked fee by course & type', 'Marketing Exec') +
    `<div class="eyebrow av-tablehead">Average booked fee by course &amp; type
       <span class="av-hint">▲ / ▼ vs the course average</span></div>` +
    (sorted.length
      ? `<div class="table-wrap"><table class="ledger">
       <thead><tr><th>Course</th><th>Type</th><th>Their Avg</th><th>Course Avg</th><th>Reported</th><th>Their range</th></tr></thead>
       <tbody>${rows}</tbody>
       <tfoot><tr class="av-foot"><td colspan="2">Overall</td>
         <td class="mono">${avAvg(overall) != null ? fmtFee(avAvg(overall)) : '—'}</td>
         <td class="mono">—</td>
         <td class="mono">${overall.count}</td>
         <td class="mono">${avRangeText(overall)}</td></tr></tfoot>
     </table></div>`
      : emptyHtml('chart', 'No reported admissions',
          'This exec has no reported admissions yet, so there is no booked-fee data to break down.'));
  $('#phStats').innerHTML = statChip(overall.count, 'Reported')
    + statChip(avAvg(overall) != null ? fmtFee(avAvg(overall)) : '—', 'Avg Fee')
    + statChip(avRangeText(overall), 'Fee Range')
    + statChip(combos.length, 'Course×Type', true);
  $('#avBack').onclick = () => { AV.level = 'overview'; AV.selectedExec = null; AV.tab = 'execs'; renderAverages(); };
}

// ---- interactions -------------------------------------------------------
function wireAverages() {
  const tabs = $('#avTabs');
  if (tabs) tabs.querySelectorAll('.seg-tab').forEach((b) =>
    b.onclick = () => { AV.tab = b.dataset.tab; renderAverages(); });
  $('#main').querySelectorAll('.av-exec').forEach((tr) =>
    tr.onclick = () => { AV.selectedExec = tr.dataset.exec; AV.level = 'exec'; renderAverages(); });
  // Click a course (a course-wise row/bar, or a pivot column header) → an
  // exec leaderboard scoped to that exact course × type.
  $('#main').querySelectorAll('[data-combo]').forEach((el) => {
    el.onclick = () => openCourseLeaderboard(el.dataset.combo);
    if (el.tagName !== 'TR' && el.tagName !== 'TH') el.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCourseLeaderboard(el.dataset.combo); }
    };
  });
}

// A leaderboard of execs for one course × type — ranked by enrolments, with each
// exec's average booked fee and a ▲/▼ vs the course average.
function openCourseLeaderboard(key) {
  const agg = AV.agg;
  if (!agg) return;
  const combo = agg.combos.find((c) => c.key === key);
  if (!combo) return;
  const board = agg.execs
    .map((e) => ({ name: e.name, solo: e.solo, cell: e.cells[key] }))
    .filter((x) => x.cell && x.cell.count)
    .map((x) => ({ name: x.name, solo: x.solo, count: x.cell.count, avg: avAvg(x.cell) }))
    .sort((a, b) => (b.avg || 0) - (a.avg || 0) || b.count - a.count || cmpv(a.name, b.name));
  const maxAvg = Math.max(1, ...board.map((b) => b.avg || 0));
  const bench = combo.avg;
  const rows = board.map((b, i) => {
    const heat = avHeat(b.avg, bench);
    return `
    <div class="lead-row av-lead"${heat ? ` style="${heat}"` : ''}>
      <span class="lead-rank mono">${i + 1}</span>
      <span class="lead-name">${esc(b.name)}${b.solo ? '<span class="av-solo">own</span>' : ''}</span>
      <span class="lead-bar"><span class="lead-fill" style="width:${Math.round((b.avg || 0) / maxAvg * 100)}%"></span></span>
      <span class="lead-fig"><b class="mono">${b.avg != null ? fmtFee(b.avg) : '—'}${avDelta(b.avg, bench)}</b><small>avg fee</small></span>
      <span class="lead-fig"><b class="mono">${b.count}</b><small>reported</small></span>
    </div>`;
  }).join('');
  overlay(`<div class="modal">
    <div class="modal-head">
      <h3 class="av-lead-title">${esc(combo.course)}${avHostBadge(combo.hostel)}</h3>
      <button class="x" data-close>${icon('x', 20)}</button></div>
    <p class="modal-msg">Course average ${bench != null ? fmtFee(bench) : '—'} · ${combo.acc.count} reported · range ${avRangeText(combo.acc)}</p>
    <div class="lead-list av-board">${rows || '<p class="muted-note">No reported admissions for this course &amp; type.</p>'}</div>
  </div>`);
}
