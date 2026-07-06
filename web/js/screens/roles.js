// =========================================================================
// ROLES & PERMISSIONS (admin): create roles and set per-page View/Edit access
// =========================================================================
async function buildRoles() {
  const [roles, allModules] = await Promise.all([api().roles_manage_list(), api().role_modules()]);
  state.allModules = allModules;
  const mayEdit = canEdit('roles');

  const createPanel = mayEdit ? `
      <div class="panel">
        <h4 class="panel-title">Create role</h4>
        <label class="field">Role name</label>
        <input id="rName" class="input" placeholder="e.g. Front desk" autocomplete="off" />
        <label class="field">Page permissions</label>
        <div id="rPerms">${permRows([], [])}</div>
        <div id="rMsg" class="error-msg"></div>
        <button id="rCreate" class="btn btn-primary btn-block" style="margin-top:12px">
          ${icon('plus', 16)}<span>Create role</span></button>
      </div>` : '';

  $('#main').innerHTML =
    pageHead('Roles & Permissions', mayEdit
      ? 'Create roles and choose, per page, whether a role has no access, view-only, or full edit. Every role always includes Home.'
      : 'Roles and their per-page access.', 'Access') +
    `<div class="two-col">
      <div class="panel">
        <div class="panel-head"><span class="eyebrow">Roles</span></div>
        <div id="roleList"></div>
      </div>
      ${createPanel}
    </div>`;

  renderRoleList(roles, mayEdit);
  if (mayEdit) {
    wirePermRows($('#rPerms'));
    $('#rCreate').onclick = async () => {
      const name = $('#rName').value.trim();
      if (!name) { $('#rMsg').textContent = 'Role name is required.'; return; }
      const { menu, editable } = readPermRows($('#rPerms'));
      const r = await api().role_create(name, menu, editable);
      if (r.ok) { toast('Role created'); state.roles = await api().roles(); buildRoles(); }
      else { $('#rMsg').textContent = r.message; }
    };
  }
}

// One "Off / View / Edit" row per module. `disabled` locks them (admin role).
function permRows(menu, editable, disabled = false) {
  return (state.allModules || []).map((m) => {
    const lvl = editable.includes(m.key) ? 'edit' : (menu.includes(m.key) ? 'view' : 'off');
    const seg = (v, label) =>
      `<button type="button" class="seg-b ${lvl === v ? 'active' : ''}" data-lvl="${v}" ${disabled ? 'disabled' : ''}>${label}</button>`;
    return `<div class="permrow" data-mod="${m.key}">
      <div class="permname">${icon(m.icon, 15)}<span>${esc(m.label)}</span></div>
      <div class="seg">
        ${seg('off', 'Off')}${seg('view', 'View')}${m.editable ? seg('edit', 'Edit')
          : '<span class="seg-b seg-ph" aria-hidden="true">Edit</span>'}
      </div></div>`;
  }).join('');
}

function wirePermRows(container) {
  container.querySelectorAll('.permrow .seg-b').forEach((b) =>
    b.onclick = () => {
      if (b.classList.contains('seg-ph')) return;
      b.parentElement.querySelectorAll('.seg-b').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
    });
}

function readPermRows(container) {
  const menu = [], editable = [];
  container.querySelectorAll('.permrow').forEach((row) => {
    const active = row.querySelector('.seg-b.active');
    const lvl = active ? active.dataset.lvl : 'off';
    if (lvl === 'view' || lvl === 'edit') menu.push(row.dataset.mod);
    if (lvl === 'edit') editable.push(row.dataset.mod);
  });
  return { menu, editable };
}

function renderRoleList(roles, mayEdit = canEdit('roles')) {
  const modLabel = {};
  (state.allModules || []).forEach((m) => { modLabel[m.key] = m.label; });
  const tabs = (r) => {
    const view = r.menu.filter((k) => k !== 'home');
    if (!view.length) return '<span class="muted">Home only</span>';
    return view.map((k) => {
      const isEdit = r.editable.includes(k);
      return `<span class="perm-tag ${isEdit ? 'is-edit' : ''}"><i class="perm-dot"></i>${esc(modLabel[k] || k)}
        <span class="perm-lvl">${isEdit ? 'edit' : 'view'}</span></span>`;
    }).join('');
  };
  const row = (r) => `
    <div class="acct">
      <div class="chip chip-accent">${icon('shield', 18)}</div>
      <div class="acct-id"><div class="nm">${esc(r.label)}${r.builtin ? ' <span class="tag-builtin">Built-in</span>' : ''}</div>
        <div class="sub pills-wrap">${tabs(r)}</div></div>
      <div class="spacer"></div>
      ${mayEdit ? `<button class="iconbtn sm" data-redit="${r.key}" title="Edit permissions">${icon('edit', 15)}</button>` : ''}
      ${mayEdit && r.key !== 'admin' ? `<button class="iconbtn sm" data-rdel="${r.key}" data-nm="${esc(r.label)}" title="Delete">${icon('trash', 15)}</button>` : ''}
    </div>`;

  $('#roleList').innerHTML = roles.map(row).join('');
  $('#roleList').querySelectorAll('[data-redit]').forEach((b) =>
    b.onclick = () => openEditRole(roles.find((r) => r.key === b.dataset.redit)));
  $('#roleList').querySelectorAll('[data-rdel]').forEach((b) =>
    b.onclick = async () => {
      const ok = await modalConfirm({ title: 'Delete role',
        message: `Delete role “${b.dataset.nm}”? Accounts using it must be reassigned first.` });
      if (!ok) return;
      const r = await api().role_delete(b.dataset.rdel);
      if (r.ok) { toast('Role deleted'); state.roles = await api().roles(); buildRoles(); }
      else toast(r.message, false);
    });
}

async function openEditRole(role) {
  const r = await modalRole(role);
  if (!r) return;
  const res = await api().role_update(role.key, r.label, r.menu, r.editable);
  if (!res.ok) { toast(res.message, false); return; }
  toast('Permissions updated');
  state.roles = await api().roles();
  state.perms = await api().my_perms();
  if (role.key === state.user.role) {
    state.menu = await api().menu();
    renderShell(); openModule('roles');
  } else {
    buildRoles();
  }
}

function modalRole(role) {
  return new Promise((res) => {
    const isAdmin = role.key === 'admin';
    const ov = overlay(`<div class="modal">
      <h3>Edit role</h3>
      <label class="field">Role name</label>
      <input class="input" id="erName" value="${esc(role.label)}" ${isAdmin ? 'disabled' : ''}/>
      <label class="field" style="margin-top:12px">Page permissions</label>
      <div id="erPerms">${permRows(role.menu, role.editable, isAdmin)}</div>
      ${isAdmin ? '<div class="muted-note">The Administrator always has full access to every page.</div>' : ''}
      <div id="erMsg" class="error-msg"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" data-close>Cancel</button>
        <button class="btn btn-primary" id="mOk">Save changes</button>
      </div></div>`);
    wirePermRows(ov.querySelector('#erPerms'));
    ov.querySelector('[data-close]').onclick = () => { ov.remove(); res(null); };
    ov.querySelector('#mOk').onclick = async () => {
      const label = ov.querySelector('#erName').value.trim();
      if (!label) { ov.querySelector('#erMsg').textContent = 'Role name is required.'; return; }
      const { menu, editable } = readPermRows(ov.querySelector('#erPerms'));
      const sure = await modalConfirm({ title: 'Save changes',
        message: `Save permission changes to “${label}”?`, confirmText: 'Save changes', danger: false });
      if (!sure) return;
      ov.remove();
      res({ label, menu, editable });
    };
  });
}
