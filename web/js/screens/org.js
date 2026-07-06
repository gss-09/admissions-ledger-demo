// =========================================================================
// MANAGE ORG — the recruiting org, in two tabs (governed by one `org` perm):
//   • Recruiters       — city-bound AGMs (grouped by city) + their marketing execs
//   • Campuses & Cities — cities → campuses → per-campus course lists
//
// Hierarchy: City → Campus → Course; an AGM serves exactly ONE city (covering all
// its campuses), execs inherit their AGM's city. Renames cascade to student rows.
// =========================================================================
let ORG = { cities: [], campuses: [], agms: [], tab: 'recruiters' };

async function buildOrg() {
  $('#main').innerHTML = skelPage();
  ORG = Object.assign({ tab: 'recruiters' }, await api().org_data());
  renderOrg();
}

async function reloadOrg() {
  const tab = ORG.tab;
  ORG = Object.assign({ tab }, await api().org_data());
  // Keep the student forms' dropdowns fresh after org edits.
  if (typeof ST !== 'undefined' && ST && ST.data) {
    try { ST.data = await api().students(); } catch {}
  }
  renderOrg();
}

function renderOrg() {
  const mayEdit = canEdit('org');
  const execCount = ORG.agms.reduce((n, a) => n + a.execs.length, 0);
  const tabs = `<div class="seg-tabs" id="orgTabs">
      <button class="seg-tab ${ORG.tab === 'recruiters' ? 'active' : ''}" data-tab="recruiters">Recruiters</button>
      <button class="seg-tab ${ORG.tab === 'campuses' ? 'active' : ''}" data-tab="campuses">Campuses &amp; Cities</button>
    </div>`;
  $('#main').innerHTML =
    pageHead('Manage Org', mayEdit
      ? 'City-bound AGMs and their execs; cities, campuses and per-campus course lists.'
      : 'AGMs, execs, cities, campuses and courses.', 'Organisation')
    + `<div class="controlbar">${tabs}</div><div id="orgBody"></div>`;
  $('#phStats').innerHTML = statChip(ORG.agms.length, 'AGMs')
    + statChip(execCount, 'Marketing Execs') + statChip(ORG.campuses.length, 'Campuses')
    + statChip(ORG.cities.length, 'Cities', true);

  $('#orgTabs').querySelectorAll('.seg-tab').forEach((b) =>
    b.onclick = () => { ORG.tab = b.dataset.tab; renderOrg(); });

  if (ORG.tab === 'campuses') renderCampusesTab(mayEdit);
  else renderRecruitersTab(mayEdit);
}

// ---- Tab 1: Recruiters (campus-bound AGMs + execs) ----------------------
function renderRecruitersTab(mayEdit) {
  const addBtn = mayEdit
    ? `<div class="spacer"></div><button class="btn btn-primary" id="agmAdd">${icon('plus', 15)}<span>Add AGM</span></button>` : '';
  $('#orgBody').innerHTML = `<div class="panel">
      <div class="panel-head"><span class="eyebrow">AGMs &amp; marketing execs</span>${addBtn}</div>
      <div id="agmList"></div></div>`;
  if (mayEdit) $('#agmAdd').onclick = () => openAgmModal(null);
  renderAgmList(mayEdit);
}

function renderAgmList(mayEdit) {
  if (!ORG.agms.length) {
    $('#agmList').innerHTML = `<p class="muted" style="padding:8px 2px">No AGMs yet.</p>`;
    return;
  }
  const editBtns = (kind, id, nm) => mayEdit ? `
    <button class="iconbtn sm" data-${kind}-edit="${id}" data-nm="${esc(nm)}" title="Rename">${icon('edit', 14)}</button>
    <button class="iconbtn sm" data-${kind}-del="${id}" data-nm="${esc(nm)}" title="Delete">${icon('trash', 14)}</button>` : '';

  // One AGM card. AGMs are city-bound (one city each); the card sits under its
  // city's section header, so it shows only a warning when it has NO city yet.
  const agmCard = (a) => `
    <div class="org-agm">
      <div class="acct">
        <div class="chip chip-accent">${icon('user', 17)}</div>
        <div class="acct-id"><div class="nm">${esc(a.name)}</div>
          <div class="sub">${a.execs.length
            ? `${a.execs.length} marketing exec${a.execs.length > 1 ? 's' : ''}`
            : 'No marketing execs — acts as own exec'}</div></div>
        <div class="spacer"></div>
        ${mayEdit ? `<button class="btn btn-ghost sm" data-exec-add="${a.id}">${icon('plus', 14)}<span>Add exec</span></button>` : ''}
        ${mayEdit ? `<button class="iconbtn sm" data-agm-city="${a.id}" title="Edit city">${icon('building', 14)}</button>` : ''}
        ${editBtns('agm', a.id, a.name)}
      </div>
      ${a.city_id ? '' : `<div class="org-campuses"><span class="muted" style="font-size:12px">no city — won't appear on the student form</span></div>`}
      ${a.execs.length ? `<div class="org-chips">
        ${a.execs.map((e) => `
          <span class="org-chip${mayEdit ? '' : ' ro'}">
            <span class="org-chip-nm">${esc(e.name)}</span>
            ${mayEdit ? `<button class="org-chip-act" data-exec-edit="${e.id}" data-nm="${esc(e.name)}" title="Rename">${icon('edit', 12)}</button>
              <button class="org-chip-act" data-exec-del="${e.id}" data-nm="${esc(e.name)}" title="Delete">${icon('trash', 12)}</button>` : ''}
          </span>`).join('')}
      </div>` : ''}
    </div>`;

  // Group AGMs by city (a city → its AGMs), with any city-less AGMs last.
  const section = (title, agms) => `
    <div class="org-city">
      <div class="org-city-head"><span class="org-city-name">${esc(title)}</span>
        <span class="org-city-meta">${agms.length} AGM${agms.length === 1 ? '' : 's'}</span></div>
      <div class="org-city-body">${agms.map(agmCard).join('')}</div>
    </div>`;
  const groups = ORG.cities
    .map((ci) => ({ name: ci.name, agms: ORG.agms.filter((a) => a.city_id === ci.id) }))
    .filter((g) => g.agms.length);
  const orphans = ORG.agms.filter((a) => !a.city_id);
  $('#agmList').innerHTML = groups.map((g) => section(g.name, g.agms)).join('')
    + (orphans.length ? section('Unassigned (no city)', orphans) : '');

  if (!mayEdit) return;
  wireOrgEdit('agm', {
    rename: (id, nm) => api().agm_rename(Number(id), nm),
    del: (id) => api().agm_delete(Number(id)), label: 'AGM',
  });
  wireOrgEdit('exec', {
    rename: (id, nm) => api().exec_rename(Number(id), nm),
    del: (id) => api().exec_delete(Number(id)), label: 'marketing exec',
  });
  $('#agmList').querySelectorAll('[data-agm-city]').forEach((b) => b.onclick = () =>
    openAgmModal(ORG.agms.find((a) => a.id === Number(b.dataset.agmCity))));
  $('#agmList').querySelectorAll('[data-exec-add]').forEach((b) => b.onclick = async () => {
    const name = await modalPrompt({ title: 'Add marketing exec', label: 'Exec name', confirmText: 'Add' });
    if (!name) return;
    const r = await api().exec_create(Number(b.dataset.execAdd), name);
    if (r.ok) { toast('Marketing exec added'); await reloadOrg(); }
    else toast(r.message, false);
  });
}

// Add a new AGM (name + single city) or edit an existing AGM's city.
function openAgmModal(agm) {
  const editing = !!agm;
  const cityField = ORG.cities.length
    ? `<select class="input" id="agmModalCity">
         <option value="">— No city —</option>
         ${ORG.cities.map((c) => `<option value="${c.id}" ${editing && agm.city_id === c.id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}
       </select>`
    : '<p class="muted">No cities yet — add one in the Campuses & Cities tab.</p>';
  const ov = overlay(`<div class="modal">
    <div class="modal-head"><h3>${editing ? 'Edit AGM city' : 'Add AGM'}</h3>
      <button class="x" data-close>${icon('x', 20)}</button></div>
    <label class="field">AGM name</label>
    <input class="input" id="agmModalName" value="${editing ? esc(agm.name) : ''}" ${editing ? 'disabled' : ''} autocomplete="off" placeholder="New AGM name" />
    <label class="field" style="margin-top:12px">City served</label>
    ${cityField}
    <div class="error-msg" id="agmModalMsg"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" data-close>Cancel</button>
      <button class="btn btn-primary" id="agmModalOk">${editing ? 'Save city' : 'Add AGM'}</button>
    </div></div>`);
  ov.querySelector('#agmModalOk').onclick = async () => {
    const sel = ov.querySelector('#agmModalCity');
    const cityId = sel && sel.value ? Number(sel.value) : null;
    const msg = ov.querySelector('#agmModalMsg');
    let r;
    if (editing) {
      r = await api().agm_set_city(agm.id, cityId);
    } else {
      const name = ov.querySelector('#agmModalName').value.trim();
      if (!name) { msg.textContent = 'AGM name is required.'; return; }
      r = await api().agm_create(name, cityId);
    }
    if (r.ok) { ov.remove(); toast(editing ? 'AGM city updated' : 'AGM added'); await reloadOrg(); }
    else msg.textContent = r.message;
  };
}

// ---- Tab 2: Campuses & Cities (cities → campuses → courses) -------------
function renderCampusesTab(mayEdit) {
  const cityAdd = mayEdit
    ? `<button class="btn btn-ghost sm" id="cityAdd">${icon('plus', 14)}<span>Add city</span></button>` : '';
  const campusAdd = mayEdit
    ? `<button class="btn btn-primary" id="campusAdd">${icon('plus', 15)}<span>Add campus</span></button>` : '';
  // Group campuses by city; campuses with no city land in an "Unassigned" bucket.
  const groups = ORG.cities.map((ci) => ({ id: ci.id, name: ci.name,
    campuses: ORG.campuses.filter((c) => c.city_id === ci.id) }));
  const orphans = ORG.campuses.filter((c) => !c.city_id);

  const section = (title, campuses, cityId) => `
    <div class="org-city">
      <div class="org-city-head">
        <span class="org-city-name">${esc(title)}</span>
        <span class="org-city-meta">${campuses.length} campus${campuses.length === 1 ? '' : 'es'}</span>
        ${cityId && mayEdit ? `<button class="iconbtn sm" data-city-edit="${cityId}" data-nm="${esc(title)}" title="Rename city">${icon('edit', 12)}</button>
          <button class="iconbtn sm" data-city-del="${cityId}" data-nm="${esc(title)}" title="Delete city">${icon('trash', 12)}</button>` : ''}
      </div>
      <div class="org-city-body">
        ${campuses.length ? campuses.map((c) => campusCard(c, mayEdit)).join('')
          : '<p class="muted" style="padding:4px 2px;font-size:13px">No campuses in this city.</p>'}
      </div>
    </div>`;

  $('#orgBody').innerHTML = `<div class="panel">
      <div class="panel-head"><span class="eyebrow">Cities, campuses &amp; courses</span>
        <div class="spacer"></div>${cityAdd}${campusAdd}</div>
      ${groups.map((g) => section(g.name, g.campuses, g.id)).join('')}
      ${orphans.length ? section('Unassigned (no city)', orphans, null) : ''}
      ${!ORG.campuses.length ? '<p class="muted" style="padding:8px 2px">No campuses yet.</p>' : ''}
    </div>`;

  if (!mayEdit) return;
  $('#cityAdd').onclick = async () => {
    const name = await modalPrompt({ title: 'Add city', label: 'City name', confirmText: 'Add' });
    if (!name) return;
    const r = await api().city_create(name);
    if (r.ok) { toast('City added'); await reloadOrg(); } else toast(r.message, false);
  };
  $('#campusAdd').onclick = () => openCampusModal();
  wireOrgEdit('city', {
    rename: (id, nm) => api().city_rename(Number(id), nm),
    del: (id) => api().city_delete(Number(id)), label: 'city',
  });
  wireOrgEdit('campus', {
    rename: (id, nm) => api().campus_rename(Number(id), nm),
    del: (id) => api().campus_delete(Number(id)), label: 'campus',
  });
  wireOrgEdit('course', {
    rename: (id, nm) => api().course_rename(Number(id), nm),
    del: (id) => api().course_delete(Number(id)), label: 'course',
  });
  // Add a course under a campus.
  $('#orgBody').querySelectorAll('[data-course-add]').forEach((b) => b.onclick = async () => {
    const name = await modalPrompt({ title: 'Add course', label: 'Course name', confirmText: 'Add' });
    if (!name) return;
    const r = await api().course_create(Number(b.dataset.courseAdd), name);
    if (r.ok) { toast('Course added'); await reloadOrg(); } else toast(r.message, false);
  });
}

function campusCard(c, mayEdit) {
  // Courses are compact chips that wrap, not one full row each (a campus can hold
  // 15+ courses — vertical rows made the screen scroll forever).
  const courses = (c.courses || []).map((co) => `
    <span class="org-chip${mayEdit ? '' : ' ro'}">
      <span class="org-chip-nm">${esc(co.name)}</span>
      ${mayEdit ? `<button class="org-chip-act" data-course-edit="${co.id}" data-nm="${esc(co.name)}" title="Rename">${icon('edit', 12)}</button>
        <button class="org-chip-act" data-course-del="${co.id}" data-nm="${esc(co.name)}" title="Delete">${icon('trash', 12)}</button>` : ''}
    </span>`).join('');
  return `<div class="org-agm">
      <div class="acct">
        <div class="chip chip-accent">${icon('building', 17)}</div>
        <div class="acct-id"><div class="nm">${esc(c.name)}</div>
          <div class="sub">${(c.courses || []).length} course${(c.courses || []).length === 1 ? '' : 's'}</div></div>
        <div class="spacer"></div>
        ${mayEdit ? `<button class="btn btn-ghost sm" data-course-add="${c.id}">${icon('plus', 14)}<span>Add course</span></button>` : ''}
        ${mayEdit ? `<button class="iconbtn sm" data-campus-edit="${c.id}" data-nm="${esc(c.name)}" title="Rename">${icon('edit', 14)}</button>
          <button class="iconbtn sm" data-campus-del="${c.id}" data-nm="${esc(c.name)}" title="Delete">${icon('trash', 14)}</button>` : ''}
      </div>
      ${(c.courses || []).length ? `<div class="org-chips">${courses}</div>` : ''}
    </div>`;
}

// Add a campus (name + city).
function openCampusModal() {
  const ov = overlay(`<div class="modal compact">
    <div class="modal-head"><h3>Add campus</h3><button class="x" data-close>${icon('x', 20)}</button></div>
    <label class="field">Campus name</label>
    <input class="input" id="campusModalName" autocomplete="off" placeholder="New campus name" />
    <label class="field" style="margin-top:12px">City</label>
    <select class="select" id="campusModalCity">
      <option value="">— no city —</option>
      ${ORG.cities.map((ci) => `<option value="${ci.id}">${esc(ci.name)}</option>`).join('')}
    </select>
    <div class="error-msg" id="campusModalMsg"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" data-close>Cancel</button>
      <button class="btn btn-primary" id="campusModalOk">Add campus</button>
    </div></div>`);
  ov.querySelector('#campusModalOk').onclick = async () => {
    const name = ov.querySelector('#campusModalName').value.trim();
    const cityId = ov.querySelector('#campusModalCity').value;
    if (!name) { ov.querySelector('#campusModalMsg').textContent = 'Campus name is required.'; return; }
    const r = await api().campus_create(name, cityId ? Number(cityId) : null);
    if (r.ok) { ov.remove(); toast('Campus added'); await reloadOrg(); }
    else ov.querySelector('#campusModalMsg').textContent = r.message;
  };
}

// Wire the rename/delete buttons for one entity kind across the org screen.
function wireOrgEdit(kind, fns) {
  document.querySelectorAll(`[data-${kind}-edit]`).forEach((b) => b.onclick = async () => {
    const id = b.dataset[`${kind}Edit`];
    const name = await modalPrompt({ title: `Rename ${fns.label}`, value: b.dataset.nm, confirmText: 'Rename' });
    if (!name || name === b.dataset.nm) return;
    const r = await fns.rename(id, name);
    if (r.ok) { toast('Renamed'); await reloadOrg(); } else toast(r.message, false);
  });
  document.querySelectorAll(`[data-${kind}-del]`).forEach((b) => b.onclick = async () => {
    const id = b.dataset[`${kind}Del`];
    const ok = await modalConfirm({ title: `Delete ${fns.label}`,
      message: `Delete “${b.dataset.nm}”? This can't be undone.` });
    if (!ok) return;
    const r = await fns.del(id);
    if (r.ok) { toast('Deleted'); await reloadOrg(); } else toast(r.message, false);
  });
}
