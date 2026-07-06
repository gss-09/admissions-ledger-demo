// =========================================================================
// APP SHELL
// =========================================================================
async function enterApp(boot) {
  // boot (from bootstrap()) may already carry menu/roles/perms, saving a round
  // trip on reopen. Otherwise — e.g. right after an interactive login — fetch
  // them in parallel (still one round trip, not three).
  let menu, roles, perms;
  if (boot && boot.menu) {
    ({ menu, roles, perms } = boot);
  } else {
    [menu, roles, perms] = await Promise.all([
      api().menu(), api().roles(), api().my_perms(),
    ]);
  }
  state.menu = menu;
  state.roles = roles;
  state.perms = perms;
  renderShell();
  openModule((state.menu[0] || { key: 'home' }).key);
}

function renderShell() {
  const u = state.user;
  const navItem = (key, ic, label) =>
    `<div class="nav-item" data-key="${key}" role="button" tabindex="0">${icon(ic)}<span>${esc(label)}</span></div>`;
  // Each module the role can see is its own sidebar item now — Students, the
  // analytics screens (AGMs / Execs / Averages / Income / Expenditure) and the
  // admin screens are all real, independently-permissioned modules.
  const navHtml = state.menu.map((m) => navItem(m.key, m.icon, m.label)).join('');

  root().innerHTML = `
    <div class="app">
      <header class="topbar">
        <button class="hamburger" id="navToggle" aria-label="Menu">${icon('menu', 22)}</button>
        <img src="logo.png" class="tb-logo" alt="" />
        <div class="tb-title">Admissions Ledger</div>
      </header>
      <div class="scrim" id="navScrim"></div>
      <aside class="sidebar" id="sidebar">
        <div class="side-brand">
          <div class="brand-mark"><img src="logo.png" alt="logo" /></div>
          <div class="brand-text">
            <span class="brand-name">Admissions Ledger</span>
            <span class="brand-sub">JR Inter · 2026&ndash;27</span>
          </div>
        </div>
        <div class="side-section">Menu</div>
        <nav id="nav">${navHtml}</nav>
        <div class="side-foot">
          <button class="user-card" id="profileBtn" title="Your account & password">
            <div class="avatar">${esc(initials(u.full_name))}</div>
            <div class="uc-text"><div class="nm">${esc(u.full_name)}</div>
                 <div class="rl">${esc(u.role_label)}</div></div>
            <span class="uc-go">${icon('chevron', 14)}</span>
          </button>
          <button id="logout" class="btn btn-ghost btn-block">
            ${icon('logout', 16)}<span>Log out</span></button>
        </div>
      </aside>
      <main class="main" id="main"></main>
    </div>`;

  const closeNav = () => {
    $('#sidebar').classList.remove('open');
    $('#navScrim').classList.remove('show');
  };
  $('#navToggle').onclick = () => {
    $('#sidebar').classList.toggle('open');
    $('#navScrim').classList.toggle('show');
  };
  $('#navScrim').onclick = closeNav;

  $('#nav').addEventListener('click', (e) => {
    const item = e.target.closest('.nav-item');
    if (item) { openModule(item.dataset.key); closeNav(); }
  });
  $('#nav').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const item = e.target.closest('.nav-item');
    if (item) { e.preventDefault(); openModule(item.dataset.key); closeNav(); }
  });
  $('#profileBtn').onclick = openProfile;
  $('#logout').onclick = async () => {
    const sure = await modalConfirm({ title: 'Log out',
      message: 'Are you sure you want to log out?', confirmText: 'Log out', danger: false });
    if (!sure) return;
    await api().logout(); state.user = null; renderLogin();
  };
}

// Profile modal: account details on top; the password form is behind a button.
function openProfile() {
  const kv = (k, v) => `<div class="kv"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`;
  const ov = document.createElement('div');
  ov.className = 'modal-overlay';
  document.body.appendChild(ov);
  const done = () => ov.remove();
  const isAdmin = state.user.role === 'admin';

  function render() {
    const u = state.user;
    ov.innerHTML = `<div class="modal">
    <h3>Your account</h3>
    <div class="profile-row">
      <div class="avatar lg">${esc(initials(u.full_name))}</div>
      <div><div class="nm">${esc(u.full_name)}</div><div class="rl">@${esc(u.username)}</div></div>
    </div>
    <div class="kvlist">
      ${kv('Full name', u.full_name || '—')}
      ${kv('Username', u.username || '—')}
      ${kv('Role', u.role_label)}
    </div>
    <div id="editSection" style="display:none;margin-top:14px">
      <label class="field">Full name</label>
      <input class="input" id="pfName" value="${esc(u.full_name || '')}" autocomplete="off">
      <label class="field" style="margin-top:12px">Username</label>
      <input class="input" id="pfUser" value="${esc(u.username || '')}" autocomplete="off">
      <div id="pfMsg" class="error-msg"></div>
      <button class="btn btn-primary btn-block" id="pfSave">Save changes</button>
    </div>
    <div class="divider"></div>
    ${isAdmin ? `<button class="btn btn-ghost btn-block" id="editProfile">${icon('edit', 16)}<span>Edit name</span></button>` : ''}
    <button class="btn btn-ghost btn-block" id="showPw" style="margin-top:10px">${icon('lock', 16)}<span>Change password</span></button>
    <div id="pwSection" style="display:none;margin-top:14px">
      <label class="field">Current password</label>
      ${pwInput('pCur', 'Your current password')}
      <label class="field" style="margin-top:12px">New password</label>
      ${pwInput('pNew', 'min. 8 characters')}
      <label class="field" style="margin-top:12px">Confirm new password</label>
      ${pwInput('pCon', 'Re-type new password')}
      <div id="pMsg" class="error-msg"></div>
      <button class="btn btn-primary btn-block" id="pwSave">Update password</button>
    </div>
    <div class="modal-actions" style="margin-top:14px">
      <button class="btn btn-ghost" id="mClose">Close</button>
    </div></div>`;
    wire();
  }

  function wire() {
    ov.querySelector('#mClose').onclick = done;
    const editBtn = ov.querySelector('#editProfile');
    if (editBtn) editBtn.onclick = () => {
      ov.querySelector('#editSection').style.display = 'block';
      editBtn.style.display = 'none';
      ov.querySelector('#pfName').focus();
    };
    const pfSave = ov.querySelector('#pfSave');
    if (pfSave) pfSave.onclick = async () => {
      const name = ov.querySelector('#pfName').value.trim();
      const user = ov.querySelector('#pfUser').value.trim();
      const msg = ov.querySelector('#pfMsg');
      if (!name || !user) { msg.textContent = 'Name and username are required.'; return; }
      const r = await api().update_my_profile(name, user);
      if (r.ok) {
        state.user = r.user;
        const card = $('.user-card .nm'); if (card) card.textContent = r.user.full_name;
        const av = $('.user-card .avatar'); if (av) av.textContent = initials(r.user.full_name);
        toast('Profile updated'); render();
      } else { msg.textContent = r.message; }
    };
    ov.querySelector('#showPw').onclick = () => {
      ov.querySelector('#pwSection').style.display = 'block';
      ov.querySelector('#showPw').style.display = 'none';
      ov.querySelector('#pCur').focus();
    };
    ov.querySelector('#pwSave').onclick = async () => {
      const cur = ov.querySelector('#pCur').value;
      const nw = ov.querySelector('#pNew').value;
      const cf = ov.querySelector('#pCon').value;
      const msg = ov.querySelector('#pMsg');
      if (!cur || !nw) { msg.textContent = 'Fill in all fields.'; return; }
      if (nw.length < 8) { msg.textContent = 'New password must be at least 8 characters.'; return; }
      if (nw !== cf) { msg.textContent = 'New passwords do not match.'; return; }
      const r = await api().change_my_password(cur, nw);
      if (r.ok) { done(); toast('Password updated'); }
      else { msg.textContent = r.message; }
    };
  }

  ov.addEventListener('mousedown', (e) => { if (e.target === ov) done(); });
  render();
}

function setActiveNav(key) {
  document.querySelectorAll('.nav-item').forEach((n) => {
    const active = n.dataset.key === key;
    n.classList.toggle('active', active);
    if (active) n.setAttribute('aria-current', 'page');
    else n.removeAttribute('aria-current');
  });
}

function openModule(key) {
  state.module = key;
  setActiveNav(key);
  if (key !== 'home') $('#main').innerHTML = skelPage();
  if (key === 'home') renderHome();
  else if (key === 'students') buildStudents();
  else if (key === 'agms') buildAgms();
  else if (key === 'execs') buildExecs();
  else if (key === 'averages') buildAverages();
  else if (key === 'income') buildIncome();
  else if (key === 'expenditure') buildExpenditure();
  else if (key === 'org') buildOrg();
  else if (key === 'users') buildUsers();
  else if (key === 'roles') buildRoles();
  else if (key === 'log') buildAuditLog();
}
