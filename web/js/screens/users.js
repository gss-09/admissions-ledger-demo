// =========================================================================
// USER MANAGEMENT (admin)
// =========================================================================
// City list for the binding pickers (admin bypasses the org view gate).
let UORG = { cities: [] };

async function buildUsers() {
  const [users, org] = await Promise.all([api().users_list(), api().org_data()]);
  UORG = { cities: org.cities || [] };
  const roleOpts = state.roles.map((r) => `<option value="${r.key}">${esc(r.label)}</option>`).join('');

  $('#main').innerHTML =
    pageHead('Users', 'Manage accounts — there is no public sign-up.', 'Access') +
    `<div class="two-col">
      <div class="panel">
        <div class="panel-head">
          <span class="eyebrow">Accounts</span>
          ${state.user.role === 'admin' ? `<button class="btn btn-ghost sm" id="pwLogBtn">${icon('history', 14)}<span>Password log</span></button>` : ''}
        </div>
        <div id="acctList"></div>
      </div>
      <div class="panel">
        <h4 class="panel-title">Create account</h4>
        <label class="field">Full name</label>
        <input id="fn" class="input" placeholder="e.g. Jane Doe" autocomplete="off" />
        <label class="field">Username</label>
        <input id="un" class="input" placeholder="e.g. jdoe" autocomplete="off" />
        <label class="field">Role</label>
        <select id="rl" class="select">${roleOpts}</select>
        <label class="field">Password</label>
        ${pwInput('pw', 'min. 8 characters')}
        <label class="field" style="margin-top:12px">Cities</label>
        ${cityPickerHtml('cmp', [])}
        <div id="umsg" class="error-msg"></div>
        <button id="createBtn" class="btn btn-primary btn-block">
          ${icon('plus', 16)}<span>Create account</span></button>
      </div>
    </div>`;

  renderAccts(users);
  wireCityPicker($('#main'), 'cmp');
  if ($('#pwLogBtn')) $('#pwLogBtn').onclick = openPwLog;
  $('#createBtn').onclick = async () => {
    const r = await api().users_create($('#fn').value, $('#un').value, $('#rl').value,
      $('#pw').value, readCityPicker($('#main'), 'cmp'));
    if (r.ok) {
      toast('Account created');
      $('#fn').value = $('#un').value = $('#pw').value = '';
      $('#umsg').textContent = '';
      renderAccts(await api().users_list());
    } else { $('#umsg').textContent = r.message; }
  };
}

// ---- city binding picker (reused by create + edit) ----------------------
// "All cities" = org-wide (the empty-set = all rule). When it's ticked the per-
// city list is disabled and we send []; otherwise we send the checked city ids.
function cityPickerHtml(prefix, selectedIds) {
  const sel = new Set(selectedIds || []);
  const allOn = sel.size === 0;
  const checks = UORG.cities.length
    ? UORG.cities.map((c) => `
        <label class="org-check"><input type="checkbox" value="${c.id}" ${sel.has(c.id) ? 'checked' : ''}>
          <span>${esc(c.name)}</span></label>`).join('')
    : '<p class="muted">No cities yet — add one in Manage Org.</p>';
  return `
    <label class="org-check" style="font-weight:600">
      <input type="checkbox" id="${prefix}All" ${allOn ? 'checked' : ''}>
      <span>All cities (org-wide)</span></label>
    <div class="org-checks" id="${prefix}List">${checks}</div>`;
}
function wireCityPicker(scope, prefix) {
  const all = scope.querySelector('#' + prefix + 'All');
  const list = scope.querySelector('#' + prefix + 'List');
  if (!all || !list) return;
  const sync = () => {
    list.style.opacity = all.checked ? '0.45' : '1';
    list.querySelectorAll('input').forEach((i) => { i.disabled = all.checked; });
  };
  all.onchange = sync;
  // Ticking any specific city implies "not all".
  list.querySelectorAll('input').forEach((i) => i.addEventListener('change', () => {
    if (i.checked) { all.checked = false; sync(); }
  }));
  sync();
}
function readCityPicker(scope, prefix) {
  const all = scope.querySelector('#' + prefix + 'All');
  if (!all || all.checked) return [];
  return [...scope.querySelectorAll('#' + prefix + 'List input:checked')].map((i) => Number(i.value));
}

const ROLE_ORDER = { admin: 0, editor: 1, viewer: 2 };

function renderAccts(users) {
  const me = state.user.id;
  const iAmAdmin = state.user.role === 'admin';
  const byId = {};
  users.forEach((u) => { byId[u.id] = u; });

  // Group by role label, then sort each group by name.
  const groups = {};
  users.forEach((u) => { (groups[u.role_label] = groups[u.role_label] || []).push(u); });
  const ordered = Object.keys(groups).sort((a, b) => {
    const ra = groups[a][0].role, rb = groups[b][0].role;
    return ((ROLE_ORDER[ra] ?? 99) - (ROLE_ORDER[rb] ?? 99)) || a.localeCompare(b);
  });

  const row = (u) => {
    const isAdmin = u.role === 'admin';
    const isSelf = u.id === me;
    // A delegate (non-admin) can't manage admin accounts — the backend blocks it,
    // so hide the controls rather than show buttons that just error.
    const locked = isAdmin && !iAmAdmin;
    const changeable = !isSelf && !locked;
    const rolePill = changeable
      ? `<button class="rolepill" data-role="${u.id}" title="Click to change role">${esc(u.role_label)}${icon('chevron', 12)}</button>`
      : `<span class="rolepill static" title="${isSelf ? "You can't change your own role" : 'Only an administrator can manage administrator accounts'}">${esc(u.role_label)}</span>`;
    // City binding: admin / no-rows ⇒ org-wide ("All cities"); else chips.
    const orgWide = isAdmin || !(u.city_ids && u.city_ids.length);
    const campusTag = orgWide
      ? '<span class="pill pill-accent">All cities</span>'
      : (u.city_names || []).map((n) => `<span class="pill">${esc(n)}</span>`).join(' ');
    return `
    <div class="acct">
      <div class="avatar">${esc(initials(u.full_name))}</div>
      <div class="acct-id"><div class="nm">${esc(u.full_name)}${isSelf ? ' <span class="pill pill-accent">You</span>' : ''}</div>
        <div class="sub">@${esc(u.username)}</div>
        <div class="sub campus-tags">${campusTag}</div></div>
      <div class="spacer"></div>
      ${rolePill}
      ${locked ? '' : `<button class="iconbtn sm" data-edit="${u.id}" title="Edit">${icon('edit', 15)}</button>`}
      ${(isSelf || locked) ? '' : `<button class="iconbtn sm" data-del="${u.id}" data-nm="${esc(u.username)}" title="Delete">${icon('trash', 15)}</button>`}
    </div>`;
  };

  $('#acctList').innerHTML = ordered.map((k) => {
    const arr = groups[k].sort((a, b) => a.full_name.localeCompare(b.full_name));
    return `<div class="grp-head">${icon('shield', 14)}<span>${esc(k)}</span>
      <span class="grp-count">${arr.length}</span></div>` + arr.map(row).join('');
  }).join('');

  $('#acctList').querySelectorAll('[data-role]').forEach((b) =>
    b.onclick = () => changeUserRole(byId[b.dataset.role]));
  $('#acctList').querySelectorAll('[data-edit]').forEach((b) =>
    b.onclick = () => openEditUser(byId[b.dataset.edit]));
  $('#acctList').querySelectorAll('[data-del]').forEach((b) =>
    b.onclick = async () => {
      const ok = await modalConfirm({ title: 'Delete account',
        message: `Delete account “${b.dataset.nm}”? This cannot be undone.` });
      if (!ok) return;
      const r = await api().users_delete(parseInt(b.dataset.del));
      if (r.ok) { toast('Account deleted'); renderAccts(await api().users_list()); }
      else toast(r.message, false);
    });
}

async function changeUserRole(u) {
  // Includes admin as a target option, but only if the actor is admin (they are,
  // since this screen is admin-only). Exclude promoting via this quick picker;
  // use the assignable list plus 'admin'.
  const roles = state.roles.slice();
  const picked = await modalRolePick(u, roles);
  if (!picked || picked === u.role) return;
  const label = (roles.find((r) => r.key === picked) || { label: picked }).label;
  const sure = await modalConfirm({ title: 'Change role',
    message: `Change ${u.full_name}’s role to “${label}”?`, confirmText: 'Change role', danger: false });
  if (!sure) return;
  const res = await api().users_update(u.id, u.full_name, u.username, picked);
  if (res.ok) { toast('Role updated'); renderAccts(await api().users_list()); }
  else toast(res.message, false);
}

function modalRolePick(u, roles) {
  return new Promise((res) => {
    const opts = roles.map((r) => `
      <button class="roleopt ${r.key === u.role ? 'current' : ''}" data-k="${r.key}">
        ${icon('shield', 15)}<span>${esc(r.label)}</span>
        ${r.key === u.role
          ? '<span class="pill pill-accent" style="margin-left:auto">Current</span>'
          : `<span style="margin-left:auto;color:var(--text-faint)">${icon('chevron', 14)}</span>`}
      </button>`).join('');
    const ov = overlay(`<div class="modal">
      <h3>Change role</h3>
      <p class="modal-msg">Pick a new role for <b>${esc(u.full_name)}</b>.</p>
      <div class="roleopts">${opts}</div>
      <div class="modal-actions"><button class="btn btn-ghost" data-close>Cancel</button></div></div>`);
    ov.querySelectorAll('[data-k]').forEach((b) => b.onclick = () => { const v = b.dataset.k; ov.remove(); res(v); });
    ov.querySelector('[data-close]').onclick = () => { ov.remove(); res(null); };
  });
}

async function openEditUser(u) {
  const r = await modalUser(u);
  if (!r) return;
  const res = await api().users_update(u.id, r.full_name, r.username, r.role,
    r.password, r.city_ids);
  if (!res.ok) { toast(res.message, false); return; }
  toast('Account updated');
  if (u.id === state.user.id) {
    state.user.full_name = r.full_name; state.user.username = r.username;
    renderShell(); openModule('users');
  } else {
    renderAccts(await api().users_list());
  }
}

function modalUser(u) {
  return new Promise((res) => {
    const isSelf = u.id === state.user.id;
    const roleOpts = state.roles.map((r) =>
      `<option value="${r.key}" ${r.key === u.role ? 'selected' : ''}>${esc(r.label)}</option>`).join('');
    // Only an admin actor may set/keep the admin role; delegates never see the option
    // (and can't open the editor on an admin account in the first place).
    const adminOpt = state.user.role === 'admin'
      ? `<option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Administrator</option>` : '';
    const roleLocked = isSelf;
    const ov = overlay(`<div class="modal">
      <h3>Edit account</h3>
      <label class="field">Full name</label>
      <input class="input" id="eFn" value="${esc(u.full_name)}" />
      <label class="field" style="margin-top:12px">Username</label>
      <input class="input" id="eUn" value="${esc(u.username)}" />
      <label class="field" style="margin-top:12px">Role</label>
      <select class="select" id="eRl" ${roleLocked ? 'disabled' : ''}>${adminOpt}${roleOpts}</select>
      ${isSelf ? '<div class="muted-note">You can’t change your own role.</div>' : ''}
      <label class="field" style="margin-top:12px">New password</label>
      ${pwInput('ePw', 'Leave blank to keep current')}
      <label class="field" style="margin-top:12px">Cities</label>
      ${cityPickerHtml('eCmp', u.city_ids || [])}
      <div id="eMsg" class="error-msg"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" data-close>Cancel</button>
        <button class="btn btn-primary" id="mOk">Save changes</button>
      </div></div>`);
    ov.querySelector('#eFn').focus();
    wireCityPicker(ov, 'eCmp');
    ov.querySelector('[data-close]').onclick = () => { ov.remove(); res(null); };
    ov.querySelector('#mOk').onclick = async () => {
      const fn = ov.querySelector('#eFn').value.trim();
      const un = ov.querySelector('#eUn').value.trim();
      const rl = isSelf ? u.role : ov.querySelector('#eRl').value;
      const pw = ov.querySelector('#ePw').value;
      const msg = ov.querySelector('#eMsg');
      if (!fn || !un) { msg.textContent = 'Name and username are required.'; return; }
      if (pw && pw.length < 8) { msg.textContent = 'Password must be at least 8 characters.'; return; }
      const sure = await modalConfirm({ title: 'Save changes',
        message: `Save changes to ${fn}’s account?`, confirmText: 'Save changes', danger: false });
      if (!sure) return;
      const city_ids = readCityPicker(ov, 'eCmp');
      ov.remove();
      res({ full_name: fn, username: un, role: rl, password: pw, city_ids });
    };
  });
}

// Admin-only audit trail: every password change across all accounts.
async function openPwLog() {
  const ov = overlay(`<div class="modal" style="width:min(560px,94vw)">
    <h3>${icon('history', 18)}<span style="margin-left:8px">Password change log</span></h3>
    <p class="modal-msg">Every password change across all accounts, newest first.</p>
    <div id="pwLogBody" class="pwlog">${skelRows(4)}</div>
    <div class="modal-actions"><button class="btn btn-ghost" data-close>Close</button></div></div>`);
  const res = await api().password_logs();
  const body = ov.querySelector('#pwLogBody');
  if (!res || !res.ok) { body.innerHTML = `<div class="empty">${esc((res && res.message) || 'Unable to load the log.')}</div>`; return; }
  if (!res.logs.length) { body.innerHTML = `<div class="empty">No password changes recorded yet.</div>`; return; }
  const KIND = { self: ['Self', 'pill'], reset: ['Reset', 'pill-accent'], account_edit: ['Account edit', 'pill'] };
  body.innerHTML = res.logs.map((l) => {
    const [klabel, kcls] = KIND[l.kind] || [l.kind, 'pill'];
    const same = l.target_user_id && l.actor_user_id && l.target_user_id === l.actor_user_id;
    const byline = same ? 'changed their own password'
      : `by <b>${esc(l.actor_name)}</b> <span class="muted">@${esc(l.actor_username)}</span>`;
    return `<div class="pwlog-row">
      <div class="avatar">${esc(initials(l.target_name))}</div>
      <div class="acct-id"><div class="nm">${esc(l.target_name)} <span class="muted">@${esc(l.target_username)}</span>
        <span class="pill ${kcls}">${esc(klabel)}</span></div>
        <div class="sub muted">${byline} · ${esc(l.created_at)}</div></div></div>`;
  }).join('');
}
