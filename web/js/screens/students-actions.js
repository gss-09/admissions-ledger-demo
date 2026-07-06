// =========================================================================
// ADMISSIONS — modals & exports (student detail/edit, add, Excel/print)
// =========================================================================

function overlay(html) {
  const ov = document.createElement('div');
  ov.className = 'modal-overlay';
  ov.innerHTML = html;
  document.body.appendChild(ov);
  ov.addEventListener('mousedown', (e) => { if (e.target === ov) ov.remove(); });
  ov.querySelectorAll('[data-close]').forEach((b) => b.onclick = () => ov.remove());
  return ov;
}

// Hostel is a fixed two-value field (AC / NON-AC) plus a blank "unset".
function hostelOpts(cur) {
  cur = cur || '';
  return `<option value=""${cur ? '' : ' selected'}>—</option>` +
    ['AC', 'NON-AC'].map((v) => `<option ${v === cur ? 'selected' : ''}>${v}</option>`).join('');
}

// ---- shared Campus → AGM → exec + Course fields (used by add + edit) -----
// CAMPUS drives the cascade: it filters the AGMs (only those serving the campus)
// and the Courses (only those offered at the campus); the exec dropdown then
// depends on the chosen AGM (an AGM with no execs acts as its own exec). The CITY
// is intentionally not shown — it's derived from the campus in the background.
function orgFieldsHtml(meta, cur = {}) {
  const campusSel = `<option value="">— select campus —</option>` +
    (meta.campuses || []).map((c) =>
      `<option ${c === (cur.campus || '') ? 'selected' : ''}>${esc(c)}</option>`).join('');
  return `
    <div class="field span2"><label>Campus</label>
      <select class="select" name="campus" data-org-campus required>${campusSel}</select></div>
    <div class="field span2"><label>AGM</label>
      <select class="select" name="agm" data-org-agm required></select></div>
    <div class="field span2"><label>Marketing Exec</label>
      <select class="select" name="marketing_exec" data-org-exec></select></div>
    <div class="field span2"><label>Application Course</label>
      <select class="select" name="application_course" data-org-course></select></div>`;
}

function wireOrgFields(scope, meta, cur = {}) {
  const campusSel = scope.querySelector('[data-org-campus]');
  const agmSel = scope.querySelector('[data-org-agm]');
  const execSel = scope.querySelector('[data-org-exec]');
  const courseSel = scope.querySelector('[data-org-course]');

  // Fill a <select> with a placeholder + values; keep `selected` even if it's no
  // longer in the list, so editing a legacy row never silently drops its value.
  const fill = (sel, values, selected, placeholder) => {
    selected = selected || '';
    const list = (selected && !values.includes(selected) ? [selected] : []).concat(values);
    sel.innerHTML = `<option value=""${selected ? '' : ' selected'}>${esc(placeholder)}</option>` +
      list.map((v) => `<option ${v === selected ? 'selected' : ''}>${esc(v)}</option>`).join('');
  };
  const fillExec = (selected) => {
    const execs = (meta.execs && meta.execs[agmSel.value]) || [];
    if (!execs.length) {
      execSel.innerHTML = `<option value="">AGM acts as exec</option>`;
      execSel.disabled = true; execSel.required = false;
    } else {
      execSel.disabled = false; execSel.required = true;
      execSel.innerHTML = `<option value="">— select exec —</option>` +
        execs.map((e) => `<option ${e === selected ? 'selected' : ''}>${esc(e)}</option>`).join('');
    }
  };
  const fillForCampus = (agm, me, course) => {
    const campus = campusSel.value;
    fill(agmSel, (meta.campus_agms && meta.campus_agms[campus]) || [], agm, '— select AGM —');
    fill(courseSel, (meta.campus_courses && meta.campus_courses[campus]) || [], course, '— select course —');
    fillExec(me);
  };

  campusSel.onchange = () => fillForCampus(null, null, null);
  agmSel.onchange = () => fillExec(null);
  // Initial render preserves the current values when editing an existing student.
  fillForCampus(cur.agm || null, cur.marketing_exec || null, cur.application_course || null);
}

// ---- student detail (read-only) → Edit unlocks all fields ---------------
function openStudent(id) {
  const r = (ST.data.students || []).find((s) => String(s.id) === String(id));
  if (!r) return;
  const mayEdit = canEdit('students');
  const isAdmin = state.user.role === 'admin';
  const meta = ST.data.meta;

  const ov = overlay('<div class="modal" id="smModal"></div>');
  const modal = ov.querySelector('#smModal');

  // VIEW mode — every field shown read-only; nothing is editable until Edit.
  function viewMode() {
    const info = (k, v) => `<div class="info-row"><span class="ik">${esc(k)}</span><span class="iv">${esc(v || '—')}</span></div>`;
    // Contact PII (appn/father/phones) and the fee ride on the same tabs the server
    // uses to populate them — they're absent from the payload for users without the
    // relevant tab, so we skip the rows rather than render a meaningless "—".
    const showContact = canContact(), showMoney = canMoney();
    modal.innerHTML = `
      <div class="modal-head"><h3>${esc(r.student_name)}</h3>
        <button class="x" data-close>${icon('x', 20)}</button></div>
      <div class="info-grid">
        ${showContact ? info('Appn No', r.appn_no) + info('Father', r.father_name) : ''}
        ${info('Campus', r.campus)}${info('AGM', r.agm)}
        ${info('Marketing Exec', r.marketing_exec || (r.agm ? '(AGM acts as exec)' : ''))}
        ${info('Course', r.application_course)}
        ${info('Group', r.grp)}${info('Hostel', r.hostel)}
        ${showContact ? info('Mobile No', r.mobile1) + info('WhatsApp No', r.mobile2) : ''}
        ${showMoney ? info('Final Fee', fmtFee(r.final_fee)) : ''}
        ${info('Status', r.status_category)}
        ${info('Reported Date', r.status_category === 'REPORTED' ? fmtDate(r.reported_date) : '—')}
      </div>
      <div class="modal-actions">
        ${isAdmin ? `<button class="btn btn-danger" id="smDelete" style="margin-right:auto">${icon('trash', 15)}<span>Delete</span></button>` : ''}
        <button class="btn btn-ghost" data-close>Close</button>
        ${mayEdit ? `<button class="btn btn-primary" id="smEdit">${icon('edit', 15)}<span>Edit</span></button>` : ''}
      </div>`;
    wireClose();
    const editBtn = modal.querySelector('#smEdit');
    if (editBtn) editBtn.onclick = editMode;
    const delBtn = modal.querySelector('#smDelete');
    if (delBtn) delBtn.onclick = async () => {
      const sure = await modalConfirm({ title: 'Delete admission',
        message: `Delete ${r.student_name}? This cannot be undone.` });
      if (!sure) return;
      const res = await api().student_delete(Number(id));
      if (res.ok) { ov.remove(); toast('Deleted'); await reloadStudents(); }
      else toast(res.message || 'Could not delete', false);
    };
  }

  // EDIT mode — all fields become inputs; Save persists + logs to the activity log.
  function editMode() {
    // A <select> listing every known value, with the current one pre-selected
    // (kept even if it is no longer among the distinct values), plus a blank.
    const selOpts = (cur, arr) => {
      cur = cur || '';
      const list = (cur && !arr.includes(cur) ? [cur] : []).concat(arr);
      return `<option value=""${cur ? '' : ' selected'}>—</option>` +
        list.map((v) => `<option ${v === cur ? 'selected' : ''}>${esc(v)}</option>`).join('');
    };
    const statusOpts = meta.statuses.map((s) =>
      `<option ${s === r.status_category ? 'selected' : ''}>${esc(s)}</option>`).join('');
    modal.innerHTML = `
      <div class="modal-head"><h3>Edit admission</h3>
        <button class="x" data-close>${icon('x', 20)}</button></div>
      <form id="smForm" class="form-grid">
        <div class="field span2"><label>Student Name</label>
          <input class="input" name="student_name" value="${esc(r.student_name || '')}" required></div>
        <div class="field"><label>Appn No</label>
          <input class="input" name="appn_no" inputmode="numeric" value="${esc(r.appn_no || '')}"></div>
        <div class="field"><label>Father Name</label>
          <input class="input" name="father_name" value="${esc(r.father_name || '')}"></div>
        ${orgFieldsHtml(meta, r)}
        <div class="field"><label>Group</label>
          <select class="select" name="grp">${selOpts(r.grp, meta.groups)}</select></div>
        <div class="field"><label>Hostel</label>
          <select class="select" name="hostel">${hostelOpts(r.hostel)}</select></div>
        <div class="field"><label>Mobile No</label>
          <input class="input" name="mobile1" inputmode="numeric" value="${esc(r.mobile1 || '')}"></div>
        <div class="field"><label>WhatsApp No</label>
          <input class="input" name="mobile2" inputmode="numeric" value="${esc(r.mobile2 || '')}"></div>
        <div class="field span2"><label>Final Fee (₹)</label>
          <input class="input" name="final_fee" inputmode="numeric" value="${esc(r.final_fee != null ? r.final_fee : '')}"></div>
        <div class="field span2"><label>Status</label>
          <select class="select" name="status_category" id="smStatus">${statusOpts}</select></div>
        <div class="field span2" id="smDateWrap" ${r.status_category === 'REPORTED' ? '' : 'hidden'}>
          <label>Reported Date</label>
          <input class="input" type="date" name="reported_date" value="${esc(r.reported_date || '')}"></div>
        <div class="error-msg span2" id="smMsg"></div>
        <div class="modal-actions span2">
          <button type="button" class="btn btn-ghost" id="smCancel">Cancel</button>
          <button type="submit" class="btn btn-primary">Save changes</button>
        </div>
      </form>`;
    wireClose();
    wireOrgFields(modal, meta, r);
    const stSel = modal.querySelector('#smStatus');
    const dateWrap = modal.querySelector('#smDateWrap');
    stSel.onchange = () => { dateWrap.hidden = stSel.value !== 'REPORTED'; };
    modal.querySelector('#smCancel').onclick = viewMode;
    modal.querySelector('#smForm').onsubmit = async (e) => {
      e.preventDefault();
      const fd = Object.fromEntries(new FormData(e.target).entries());
      const res = await api().student_update(Number(id), fd);
      if (res.ok) { ov.remove(); toast('Saved'); await reloadStudents(); }
      else modal.querySelector('#smMsg').textContent = res.message || 'Could not save';
    };
  }

  function wireClose() {
    modal.querySelectorAll('[data-close]').forEach((b) => b.onclick = () => ov.remove());
  }

  viewMode();
}

// ---- add admission ------------------------------------------------------
function openAddStudent() {
  const meta = ST.data.meta;
  const dataList = (id, arr) => `<datalist id="${id}">${arr.map((v) => `<option value="${esc(v)}">`).join('')}</datalist>`;
  const statusOpts = meta.statuses.map((s) =>
    `<option ${s === 'YET TO ARRIVE' ? 'selected' : ''}>${esc(s)}</option>`).join('');

  const ov = overlay(`<div class="modal">
    <div class="modal-head"><h3>Add admission</h3>
      <button class="x" data-close>${icon('x', 20)}</button></div>
    <form id="addForm" class="form-grid">
      ${orgFieldsHtml(meta)}
      <div class="field"><label>Appn No</label><input class="input" name="appn_no" inputmode="numeric"></div>
      <div class="field"><label>Student Name</label><input class="input" name="student_name" required></div>
      <div class="field"><label>Father Name</label><input class="input" name="father_name"></div>
      <div class="field"><label>Group</label>
        <input class="input" name="grp" list="dlGroup">${dataList('dlGroup', meta.groups)}</div>
      <div class="field"><label>Hostel</label>
        <select class="select" name="hostel">${hostelOpts()}</select></div>
      <div class="field"><label>Mobile No</label><input class="input" name="mobile1" inputmode="numeric"></div>
      <div class="field"><label>WhatsApp No</label><input class="input" name="mobile2" inputmode="numeric"></div>
      <div class="field span2"><label>Final Fee (₹)</label><input class="input" name="final_fee" inputmode="numeric"></div>
      <div class="field span2"><label>Status</label>
        <select class="select" name="status_category">${statusOpts}</select></div>
      <div class="error-msg span2" id="addMsg"></div>
      <div class="modal-actions span2">
        <button type="button" class="btn btn-ghost" data-close>Cancel</button>
        <button type="submit" class="btn btn-primary">Save admission</button>
      </div>
    </form></div>`);

  wireOrgFields(ov, meta);
  ov.querySelector('#addForm').onsubmit = async (e) => {
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target).entries());
    const res = await api().student_add(fd);
    if (res.ok) { ov.remove(); toast('Admission added'); await reloadStudents(); }
    else ov.querySelector('#addMsg').textContent = res.message || 'Could not add';
  };
}


// ---- exports ------------------------------------------------------------
const EXPORT_COLS = [
  ['appn_no', 'Appn No'], ['student_name', 'Student'], ['father_name', 'Father'],
  ['campus', 'Campus'], ['agm', 'AGM'], ['marketing_exec', 'Marketing Exec'],
  ['application_course', 'Course'], ['grp', 'Group'],
  ['mobile1', 'Mobile'], ['mobile2', 'WhatsApp'], ['final_fee', 'Final Fee'],
  ['hostel', 'Hostel'],
  ['status_category', 'Status'], ['reported_date', 'Reported'],
];
function safeName(s) { return String(s).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, ''); }
function rowCell(r, k) { return k === 'reported_date' ? fmtDate(r[k]) : r[k]; }

// EXPORT_COLS as typed columns for the .xlsx writer: fee is numeric, the
// reported date is a real date cell (so Excel sorts both correctly), the rest
// are text. The .xlsx ships with filter/sort dropdowns over the header.
const XLSX_COLS = EXPORT_COLS.map(([key, header]) => ({
  key, header,
  type: key === 'final_fee' ? 'number' : key === 'reported_date' ? 'date' : 'text',
}));

// "16 Jun 2026, 3:34 am" — the generated-at stamp shown atop an export.
function exportStamp() {
  const d = new Date();
  const mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getMonth()];
  let h = d.getHours(); const ap = h < 12 ? 'am' : 'pm'; h = h % 12 || 12;
  return `${d.getDate()} ${mon} ${d.getFullYear()}, ${h}:${String(d.getMinutes()).padStart(2, '0')} ${ap}`;
}
// The active Students-directory filters, each as a "Label: value" line.
function dirFilterLines() {
  const val = (id) => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const out = [];
  [['sCampus', 'Campus'], ['sAgm', 'AGM'], ['sCourse', 'Course'], ['sGroup', 'Group'],
    ['sStatus', 'Status']].forEach(([id, label]) => { const v = val(id); if (v) out.push(`${label}: ${v}`); });
  const q = val('studSearch'); if (q) out.push(`Search: “${q}”`);
  return out;
}
// The title/context block written above an export table.
function exportTitle(caption, contextLines, n, filtered) {
  return [caption, ...contextLines,
    `Generated ${exportStamp()}`,
    `By ${state.user.full_name}`,
    `${n} student${n === 1 ? '' : 's'}${filtered ? ' (current filters)' : ''}`];
}

function exportAllExcel() {
  // The Export button lives on the Students directory; ST.dirRows is exactly
  // the filtered/visible rows. Fall back to the whole ledger if unset.
  const rows = Array.isArray(ST.dirRows) ? ST.dirRows.slice()
    : (ST.data.students || []).slice()
      .sort((a, b) => cmpv(a.agm, b.agm) || cmpv(a.student_name, b.student_name));
  const filters = dirFilterLines();
  const title = exportTitle('Students', filters, rows.length, filters.length > 0);
  downloadXLSX(rows, XLSX_COLS, 'students.xlsx', 'Students', title);
  toast(`Exported ${rows.length} student(s)`);
}

// Print / export chooser for a given set of students (a whole AGM, or one exec).
function openPrint(title, baseRows) {
  baseRows = baseRows || [];
  const ov = overlay(`<div class="modal compact">
    <div class="modal-head"><h3>Print / Export</h3>
      <button class="x" data-close>${icon('x', 20)}</button></div>
    <p class="edit-name">${esc(title)}</p>
    <div class="field"><label>Which students</label>
      <select class="select" id="prSubset">
        <option value="all">All students</option>
        <option value="REPORTED">Reported</option>
        <option value="DROPPED">Dropped</option>
        <option value="YET TO ARRIVE">Yet to arrive</option>
        <option value="SETTLED">Settled</option>
        <option value="NOT LIFTING">Not lifting</option>
      </select></div>
    <p class="modal-msg" id="prHint"></p>
    <div class="modal-actions">
      <button class="btn btn-ghost" id="prXlsx">${icon('download', 15)}<span>Excel</span></button>
      <button class="btn btn-primary" id="prPdf">${icon('printer', 15)}<span>Print / PDF</span></button>
    </div></div>`);

  const subset = ov.querySelector('#prSubset');
  const label = () => ({ all: 'All students', REPORTED: 'Reported', DROPPED: 'Dropped',
    'YET TO ARRIVE': 'Yet to arrive', SETTLED: 'Settled',
    'NOT LIFTING': 'Not lifting' })[subset.value];
  const rowsFor = () => {
    let rows = baseRows.slice();
    const v = subset.value;
    if (v !== 'all') rows = rows.filter((r) => r.status_category === v);
    return rows.sort((a, b) => cmpv(a.student_name, b.student_name));
  };
  const hint = () => { ov.querySelector('#prHint').textContent = `${label()} · ${rowsFor().length} student(s)`; };
  subset.onchange = hint; hint();

  ov.querySelector('#prXlsx').onclick = () => {
    const rows = rowsFor();
    const titleBlock = exportTitle(title, [`Filter: ${label()}`], rows.length, subset.value !== 'all');
    downloadXLSX(rows, XLSX_COLS, `${safeName(title)}_${safeName(label())}.xlsx`, label(), titleBlock);
    ov.remove(); toast(`Exported ${rows.length} student(s)`);
  };
  ov.querySelector('#prPdf').onclick = () => { printPDF(title, label(), rowsFor()); ov.remove(); };
}

function printPDF(agm, label, rows) {
  const td = (v) => `<td>${esc(v == null || v === '' ? '—' : v)}</td>`;
  const body = rows.map((r, i) =>
    `<tr><td>${i + 1}</td>${EXPORT_COLS.map((c) => td(rowCell(r, c[0]))).join('')}</tr>`).join('');
  const today = new Date().toLocaleDateString();
  const w = window.open('', '_blank');
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(agm)} — ${esc(label)}</title>
  <style>
    *{font-family:Arial,Helvetica,sans-serif;-webkit-print-color-adjust:exact}
    body{margin:28px;color:#000}
    .hd{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #000;padding-bottom:10px;margin-bottom:14px}
    h1{font-size:20px;margin:0}.sub{font-size:12px;color:#444;margin-top:4px}
    .meta{font-size:12px;text-align:right;color:#444}
    table{width:100%;border-collapse:collapse;font-size:11px}
    th{background:#000;color:#fff;text-align:left;padding:6px 7px;font-size:10px;text-transform:uppercase;letter-spacing:.04em}
    td{padding:5px 7px;border-bottom:1px solid #ddd}
    tr:nth-child(even) td{background:#f6f6f6}
    @media print{@page{margin:14mm}}
  </style></head><body>
    <div class="hd"><div><h1>${esc(agm)}</h1><div class="sub">Admissions Ledger · ${esc(label)}</div></div>
    <div class="meta">${esc(today)}<br>${rows.length} student(s)</div></div>
    <table><thead><tr><th>#</th>${EXPORT_COLS.map((c) => `<th>${esc(c[1])}</th>`).join('')}</tr></thead>
    <tbody>${body}</tbody></table>
  </body></html>`);
  w.document.close(); w.focus();
  setTimeout(() => w.print(), 350);
}
